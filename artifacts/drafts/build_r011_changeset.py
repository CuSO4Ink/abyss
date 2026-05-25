from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

harness_path = ROOT / "abyss_cli" / "harness_review.py"
agent_runner_path = ROOT / "abyss_cli" / "agent_runner.py"
out_path = ROOT / "artifacts" / "drafts" / "r011_deterministic_import_validation_changeset.json"

old_harness = harness_path.read_text(encoding="utf-8")
old_agent_runner = agent_runner_path.read_text(encoding="utf-8")

new_harness = '''from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import new_id, now_iso, repo_root, runtime_root, write_record

HARNESS_REVIEWS_DIR = runtime_root() / "process" / "harness_reviews"
HARNESS_REVIEW_BLOCK_RE = re.compile(r"```abyss-harness-review\\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _parse_simple_yaml(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _normalize_verdict(value: str) -> str:
    verdict = value.strip().lower()
    return verdict if verdict in {"ok", "warning", "violation"} else "warning"


def _normalize_risk(value: str) -> str:
    risk = value.strip().upper()
    return risk if risk in {"L0", "L1", "L2", "L3", "L4", "L5"} else "L3"


def _operation_target_path(operation: dict[str, Any]) -> str:
    target = operation.get("target")
    if isinstance(target, dict):
        return str(target.get("path") or "")
    return str(operation.get("path") or "")


def _operation_new_python_content(operation: dict[str, Any]) -> str | None:
    kind = str(operation.get("kind") or "")
    if kind not in {"fs.create_file", "fs.replace_exact", "fs.append_file"}:
        return None
    rel_path = _operation_target_path(operation).replace("\\\\", "/")
    if not rel_path.endswith(".py"):
        return None
    data = operation.get("input") if isinstance(operation.get("input"), dict) else operation
    content = data.get("new_content") if kind == "fs.replace_exact" else data.get("content")
    return content if isinstance(content, str) and content.strip() else None


def _module_file_from_parts(parts: list[str]) -> Path | None:
    root = repo_root()
    module_file = root.joinpath(*parts).with_suffix(".py")
    if module_file.exists():
        return module_file
    package_init = root.joinpath(*parts, "__init__.py")
    if package_init.exists():
        return package_init
    return None


def _resolve_import_from_module(source_path: str, node: ast.ImportFrom) -> tuple[Path | None, str]:
    source_parts = Path(source_path.replace("\\\\", "/")).with_suffix("").parts
    current_package = list(source_parts[:-1])
    if node.level:
        keep = len(current_package) - (node.level - 1)
        if keep < 0:
            return None, "." * node.level + (node.module or "")
        module_parts = current_package[:keep]
        if node.module:
            module_parts.extend(part for part in node.module.split(".") if part)
    else:
        module_parts = [part for part in (node.module or "").split(".") if part]
    display = ".".join(module_parts) if module_parts else "." * node.level + (node.module or "")
    if not module_parts:
        return None, display
    return _module_file_from_parts(module_parts), display


def _python_exports(module_file: Path) -> set[str]:
    try:
        tree = ast.parse(module_file.read_text(encoding="utf-8", errors="replace"), filename=str(module_file))
    except SyntaxError:
        return set()
    exports: set[str] = set()
    explicit_all: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                exports.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                        explicit_all.update(
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        )
                    elif not target.id.startswith("_"):
                        exports.add(target.id)
    return explicit_all or exports


def _validate_python_imports(changeset: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for operation in changeset.get("operations", []):
        if not isinstance(operation, dict):
            continue
        source_path = _operation_target_path(operation)
        content = _operation_new_python_content(operation)
        if content is None:
            continue
        try:
            tree = ast.parse(content, filename=source_path or "<changeset>")
        except SyntaxError as exc:
            findings.append({
                "type": "python_syntax_error",
                "severity": "error",
                "message": f"Python syntax error in {source_path}: {exc}",
                "operation_id": operation.get("id"),
            })
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not node.level and not (node.module or "").startswith("abyss_cli"):
                continue
            module_file, module_display = _resolve_import_from_module(source_path, node)
            if module_file is None:
                findings.append({
                    "type": "python_import_missing_module",
                    "severity": "error",
                    "message": f"Import target module not found for 'from {'.' * node.level}{node.module or ''} import ...' in {source_path}",
                    "operation_id": operation.get("id"),
                    "module": module_display,
                })
                continue
            exports = _python_exports(module_file)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if node.module is None:
                    submodule_parts = list(Path(module_display.replace(".", "/")).parts) + [alias.name]
                    if _module_file_from_parts(submodule_parts) is None and alias.name not in exports:
                        findings.append({
                            "type": "python_import_missing_symbol",
                            "severity": "error",
                            "message": f"Imported name '{alias.name}' is neither a submodule nor exported by {module_display}",
                            "operation_id": operation.get("id"),
                            "module": module_display,
                            "symbol": alias.name,
                        })
                elif alias.name not in exports:
                    findings.append({
                        "type": "python_import_missing_symbol",
                        "severity": "error",
                        "message": f"Imported symbol '{alias.name}' is not exported by {module_display} ({module_file.relative_to(repo_root()).as_posix()})",
                        "operation_id": operation.get("id"),
                        "module": module_display,
                        "symbol": alias.name,
                    })
    return findings


def _base_harness_finding(raw: dict[str, str]) -> dict[str, Any]:
    return {
        "type": raw.get("finding_1_type", "none"),
        "severity": raw.get("finding_1_severity", "info"),
        "message": raw.get("finding_1_message", ""),
    }


def parse_harness_review(text: str, *, target_id: str | None, agent_run_id: str | None, result_path: Path, target_type: str = "action_proposal", deterministic_context: dict[str, Any] | None = None) -> dict[str, Any]:
    matches = HARNESS_REVIEW_BLOCK_RE.findall(text)
    import_findings: list[dict[str, Any]] = []
    if target_type == "changeset" and deterministic_context:
        target_changeset = deterministic_context.get("target_changeset")
        if isinstance(target_changeset, dict):
            import_findings = _validate_python_imports(target_changeset)

    if matches:
        raw = _parse_simple_yaml(matches[0])
        verdict = _normalize_verdict(raw.get("verdict", "warning"))
        risk_level = _normalize_risk(raw.get("risk_level", "L3"))
        no_action_executed = raw.get("no_action_executed", "").strip().lower() == "true"
        findings = [_base_harness_finding(raw)]
        if import_findings:
            findings.extend(import_findings)
            verdict = "violation"
            risk_level = "L3"
        review = {
            "schema": "abyss.harness_review.v1",
            "id": new_id("hrev"),
            "agent_id": "harness",
            "agent_run_id": agent_run_id,
            "target_id": target_id,
            "target_type": target_type,
            "result_path": result_path.as_posix(),
            "verdict": verdict,
            "risk_level": risk_level,
            "summary": raw.get("summary", ""),
            "findings": findings,
            "recommendation": "reject" if import_findings else raw.get("recommendation", "none"),
            "no_action_executed": no_action_executed,
            "created_at": now_iso(),
            "deterministic_import_validation": {"checked": target_type == "changeset", "findings": import_findings},
        }
    else:
        review = {
            "schema": "abyss.harness_review.v1",
            "id": new_id("hrev"),
            "agent_id": "harness",
            "agent_run_id": agent_run_id,
            "target_id": target_id,
            "target_type": target_type,
            "result_path": result_path.as_posix(),
            "verdict": "violation" if import_findings else "warning",
            "risk_level": "L3",
            "summary": "HarnessAgent output did not contain an abyss-harness-review block.",
            "findings": import_findings or [
                {
                    "type": "output_contract_violation",
                    "severity": "warning",
                    "message": "Missing required fenced abyss-harness-review block.",
                }
            ],
            "recommendation": "reject" if import_findings else "require_human_review",
            "no_action_executed": True,
            "created_at": now_iso(),
            "deterministic_import_validation": {"checked": target_type == "changeset", "findings": import_findings},
        }

    if deterministic_context is not None:
        review["deterministic_context"] = deterministic_context

    path = HARNESS_REVIEWS_DIR / f"{review['id']}.yaml"
    write_record(path, review)
    append_event(
        "harness.review.created",
        "HarnessAgent review created",
        {
            "harness_review_id": review["id"],
            "target_id": target_id,
            "target_type": target_type,
            "verdict": review["verdict"],
            "risk_level": review["risk_level"],
            "recommendation": review["recommendation"],
            "deterministic_import_validation_checked": review.get("deterministic_import_validation", {}).get("checked", False),
        },
    )
    return review
'''

old_agent_snippet = '''    deterministic_context = {
        "validation_ok": validation_ok,
        "validation_messages": validation_messages,
        "dry_run": dry_run_report,
    }'''
new_agent_snippet = '''    deterministic_context = {
        "validation_ok": validation_ok,
        "validation_messages": validation_messages,
        "dry_run": dry_run_report,
        "target_changeset": target_record,
    }'''
if old_agent_snippet not in old_agent_runner:
    raise SystemExit("agent_runner old snippet not found")
new_agent_runner = old_agent_runner.replace(old_agent_snippet, new_agent_snippet, 1)

record = {
    "schema": "abyss.change_set.v1",
    "id": "chg_r011_deterministic_import_validation",
    "roadmap_id": "R011",
    "summary": "Add deterministic Python import and symbol validation to Harness ChangeSet review",
    "risk_level": "L2",
    "status": "proposed",
    "operations": [
        {
            "id": "op_001",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/harness_review.py"},
            "input": {"old_content": old_harness, "new_content": new_harness},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "op_002",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/agent_runner.py"},
            "input": {"old_content": old_agent_snippet, "new_content": new_agent_snippet},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "op_003",
            "kind": "check.command",
            "capability": "check.command",
            "target": {"path": "system"},
            "input": {"command": "python -m compileall -q abyss_cli"},
            "preconditions": [],
            "rollback": {"strategy": "none"},
        },
        {
            "id": "op_004",
            "kind": "check.command",
            "capability": "check.command",
            "target": {"path": "system"},
            "input": {"command": "python -m abyss_cli check"},
            "preconditions": [],
            "rollback": {"strategy": "none"},
        },
    ],
    "no_action_executed": True,
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(out_path.as_posix())
