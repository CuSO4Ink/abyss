from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from .audit import append_event
from .changeset import ALLOWED_CHECK_COMMANDS, SUPPORTED_SCHEMA, validate_changeset
from .fenced_blocks import extract_named_json_blocks, parse_json_object
from .utils import new_id, now_iso, read_record, relative_to_repo, repo_root, runtime_root, write_record

CHANGESETS_DIR = runtime_root() / "process" / "changesets"
PLACEHOLDER_MARKERS = (
    "# ...",
    "... 其他",
    "...其他",
    "其他命令定义",
    "existing code",
    "rest of",
    "omitted",
    "placeholder",
)


def _normalize_path(raw: str) -> str:
    return raw.replace("\\", "/").lstrip("/")


def _repo_file(rel_path: str) -> Path:
    rel = _normalize_path(rel_path)
    if not rel:
        raise ValueError("missing target path")
    if ".." in Path(rel).parts:
        raise ValueError(f"parent path traversal is not allowed: {rel}")
    return repo_root() / rel


def _operation_target_path(edit: dict[str, Any]) -> str:
    target = edit.get("target")
    if isinstance(target, dict):
        return _normalize_path(str(target.get("path") or ""))
    return _normalize_path(str(edit.get("path") or ""))


def _read_lines(rel_path: str) -> tuple[Path, str, list[str]]:
    path = _repo_file(rel_path)
    if not path.exists():
        raise ValueError(f"target file does not exist: {rel_path}")
    text = path.read_text(encoding="utf-8")
    return path, text, text.splitlines(keepends=True)


def _node_span_for_symbol(rel_path: str, symbol: str, symbol_type: str = "") -> str:
    path, text, lines = _read_lines(rel_path)
    tree = ast.parse(text, filename=str(path))
    expected = symbol_type.lower().strip()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name != symbol:
            continue
        actual = "class" if isinstance(node, ast.ClassDef) else "function"
        if expected and expected not in {actual, "symbol"}:
            continue
        if not getattr(node, "lineno", None) or not getattr(node, "end_lineno", None):
            raise ValueError(f"symbol has no source span: {rel_path}:{symbol}")
        return "".join(lines[node.lineno - 1:node.end_lineno])
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == symbol for target in targets):
            continue
        if expected and expected not in {"assign", "constant", "variable", "assignment", "symbol"}:
            continue
        if not getattr(node, "lineno", None) or not getattr(node, "end_lineno", None):
            raise ValueError(f"symbol has no source span: {rel_path}:{symbol}")
        return "".join(lines[node.lineno - 1:node.end_lineno])
    raise ValueError(f"symbol not found: {rel_path}:{symbol}")


def _exact_anchor(rel_path: str, anchor: str) -> str:
    _path, text, _lines = _read_lines(rel_path)
    if not anchor:
        raise ValueError("missing anchor")
    count = text.count(anchor)
    if count != 1:
        raise ValueError(f"anchor match count is {count}, expected 1: {rel_path}")
    return anchor


def _reject_placeholder_content(edit_id: str, content: str) -> None:
    lowered = content.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"{edit_id}: placeholder content is not allowed: {marker}")
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and node.value.value is Ellipsis:
            raise ValueError(f"{edit_id}: ellipsis placeholder expression is not allowed")


def preflight_reject_placeholder_edits(edits: list[dict[str, Any]]) -> list[str]:
    """Return deterministic placeholder rejection messages for raw edit-plan edits.

    This preflight runs before anchor/symbol resolution and ChangeSet operation
    compilation, so placeholder-like edit content is classified as format feedback
    instead of being mixed with later context-resolution errors.
    """
    messages: list[str] = []
    for index, edit in enumerate(edits, start=1):
        if not isinstance(edit, dict):
            continue
        edit_id = str(edit.get("id") or f"op_{index:03d}")
        for field_name in ("new_content", "content"):
            if field_name not in edit:
                continue
            try:
                _reject_placeholder_content(edit_id, str(edit.get(field_name) or ""))
            except ValueError as exc:
                messages.append(str(exc))
    return messages


def _operation_from_edit(edit: dict[str, Any]) -> dict[str, Any]:
    edit_id = str(edit.get("id") or new_id("edit"))
    kind = str(edit.get("kind") or "").strip()
    rel_path = _operation_target_path(edit)
    if not rel_path:
        raise ValueError(f"{edit_id}: missing target.path")

    if kind == "create_file":
        content = str(edit.get("content") if "content" in edit else edit.get("new_content") or "")
        _reject_placeholder_content(edit_id, content)
        return {
            "id": edit_id,
            "kind": "fs.create_file",
            "capability": "fs.write",
            "target": {"path": rel_path},
            "input": {"content": content},
            "preconditions": ["target_absent"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        }

    if kind == "replace_symbol":
        symbol = str(edit.get("symbol") or "")
        symbol_type = str(edit.get("symbol_type") or edit.get("type") or "symbol")
        old_content = _node_span_for_symbol(rel_path, symbol, symbol_type)
        if old_content.count("\n") > 120 and not edit.get("allow_large_replace"):
            raise ValueError(f"{edit_id}: replace_symbol target is too large for {rel_path}:{symbol}; use replace_anchor or append_after_anchor with a unique small anchor, or output abyss-context-request if no safe anchor is visible")
        new_content = str(edit.get("new_content") or "")

    elif kind == "replace_anchor":
        old_content = _exact_anchor(rel_path, str(edit.get("anchor") or ""))
        new_content = str(edit.get("new_content") or "")
    elif kind == "append_after_anchor":
        anchor = _exact_anchor(rel_path, str(edit.get("anchor") or ""))
        addition = str(edit.get("content") if "content" in edit else edit.get("new_content") or "")
        old_content = anchor
        new_content = anchor + addition
    else:
        raise ValueError(f"{edit_id}: unsupported edit kind: {kind}")

    if not new_content:
        raise ValueError(f"{edit_id}: missing new_content")
    _reject_placeholder_content(edit_id, new_content)

    return {
        "id": edit_id,
        "kind": "fs.replace_exact",
        "capability": "fs.write",
        "target": {"path": rel_path},
        "input": {"old_content": old_content, "new_content": new_content},
        "preconditions": ["old_content_matches_once"],
        "rollback": {"strategy": "manual_revert_from_git_diff"},
    }


def _check_operations(checks: Any) -> list[dict[str, Any]]:
    if not isinstance(checks, list):
        return []
    operations: list[dict[str, Any]] = []
    for command in checks:
        command_text = str(command)
        if command_text not in ALLOWED_CHECK_COMMANDS:
            continue
        operations.append({
            "id": f"check_{len(operations) + 1:03d}",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": command_text},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        })
    return operations


def _invalid_changeset(plan: dict[str, Any] | None, messages: list[str], *, agent_run_id: str | None, result_path: Path) -> dict[str, Any]:
    roadmap_id = "unknown"
    if isinstance(plan, dict):
        roadmap_id = str(plan.get("roadmap_id") or "unknown")
    context_markers = (
        "replace_symbol target is too large",
        "anchor match count is",
        "symbol not found:",
    )
    format_markers = (
        "EDIT_PLAN_PARSE_ERROR",
        "MISSING_EDITS_DUE_TO_PARSE_FAILURE",
        "MISSING_EDITS_NO_EDITS_BLOCK",
    )
    placeholder_markers = (
        "placeholder content is not allowed",
        "ellipsis placeholder expression is not allowed",
    )
    has_context_issue = any(any(marker in msg for marker in context_markers) for msg in messages)
    has_format_issue = any(any(marker in msg for marker in format_markers) for msg in messages)
    has_placeholder_issue = any(any(marker in msg for marker in placeholder_markers) for msg in messages)
    is_recoverable = has_context_issue or has_format_issue or has_placeholder_issue
    if has_format_issue:
        recovery_classification = "format_feedback"
        retry_guidance = "Retry with a strictly valid abyss-edit-plan JSON block and a non-empty edits array. Escape newlines and quotes inside JSON string values."
    elif has_placeholder_issue:
        recovery_classification = "format_feedback"
        retry_guidance = "Replace placeholder markers such as existing code, placeholder, omitted, ellipsis, or TODO with complete concrete code. Do not use abbreviated code or prose placeholders inside new_content/content."
    elif has_context_issue:
        recovery_classification = "context_insufficient"
        has_anchor_match_zero = any("anchor match count is 0" in msg or "anchor match count is" in msg for msg in messages)
        has_symbol_too_large = any("replace_symbol target is too large" in msg for msg in messages)
        if has_anchor_match_zero and has_symbol_too_large:
            retry_guidance = "Anchor match count is 0: the specified anchor text does not exist in the target file; provide a different exact unique anchor that appears exactly once in the file. Replace_symbol target is too large: use replace_anchor or append_after_anchor with a small unique anchor instead of replacing the entire large symbol."
        elif has_anchor_match_zero:
            retry_guidance = "Anchor match count is 0: the specified anchor text does not exist or is not unique in the target file. You must provide an exact unique anchor that appears exactly once in the target file. Copy a small distinctive snippet directly from the Repository Files section as your anchor."
        elif has_symbol_too_large:
            retry_guidance = "Replace_symbol target is too large: the target function/class exceeds the size limit for replace_symbol. Use replace_anchor or append_after_anchor with a small exact unique snippet from the target region instead, or output abyss-context-request if no safe unique anchor is visible in the provided context."
        else:
            retry_guidance = "Use replace_anchor or append_after_anchor with a small exact unique snippet visible in the provided Repository Files. If no safe anchor is visible, output abyss-context-request for local_edit_context instead of guessing."
    else:
        recovery_classification = "true_failure"
        retry_guidance = ""
    record = {
        "schema": SUPPORTED_SCHEMA,
        "id": new_id("chg_invalid"),
        "roadmap_id": roadmap_id,
        "summary": "Invalid ImplementationAgent edit plan output",
        "risk_level": "L2",
        "status": "invalid",
        "operations": [],
        "generated_by": "implementation_edit_plan",
        "agent_run_id": agent_run_id,
        "result_path": result_path.as_posix(),
        "validation": {"ok": False, "messages": messages, "validated_at": now_iso()},
        "validation_errors": messages,
        "recoverable": is_recoverable,
        "recovery_classification": recovery_classification,
        "retry_guidance": retry_guidance,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "no_action_executed": True,
        "output_type": "changeset",
    }
    CHANGESETS_DIR.mkdir(parents=True, exist_ok=True)
    write_record(CHANGESETS_DIR / f"{record['id']}.yaml", record)
    append_event("changeset.edit_plan_invalid", record["summary"], {"changeset_id": record["id"], "messages": messages, "recoverable": is_recoverable, "recovery_classification": recovery_classification, "retry_guidance": retry_guidance})
    return record


def _parse_edit_plan_json(raw_json: str) -> tuple[dict[str, Any] | None, str | None]:
    return parse_json_object(raw_json, object_error="edit plan block was not a JSON object")



def _extract_edit_plan_blocks(text: str) -> list[str]:
    return extract_named_json_blocks(text, ("abyss-edit-plan", "abyss_edit_plan"))


def parse_edit_plan(text: str) -> dict[str, Any] | None:
    matches = _extract_edit_plan_blocks(text)
    if matches:
        raw_json = matches[0].strip()
        plan, error = _parse_edit_plan_json(raw_json)
        if plan is not None:
            return plan
        return {"schema": "abyss.edit_plan.v1", "_parse_error": error, "_raw_length": len(raw_json), "edits": []}

    return None


def compile_edit_plan_from_agent_output(text: str, *, agent_run_id: str | None, result_path: Path) -> dict[str, Any] | None:
    plan = parse_edit_plan(text)
    if plan is None:
        return None

    errors: list[str] = []
    if plan.get("schema") != "abyss.edit_plan.v1":
        errors.append(f"INVALID_EDIT_PLAN_SCHEMA {plan.get('schema')}")
    if plan.get("_parse_error"):
        errors.append(f"EDIT_PLAN_PARSE_ERROR {plan.get('_parse_error')}")

    edits = plan.get("edits")
    if not isinstance(edits, list) or not edits:
        if plan.get("_parse_error"):
            errors.append("MISSING_EDITS_DUE_TO_PARSE_FAILURE")
        else:
            errors.append("MISSING_EDITS_NO_EDITS_BLOCK")

    operations: list[dict[str, Any]] = []

    if isinstance(edits, list):
        placeholder_errors = preflight_reject_placeholder_edits(edits)
        if placeholder_errors:
            errors.extend(placeholder_errors)
        else:
            for edit in edits:
                if not isinstance(edit, dict):
                    errors.append("INVALID_EDIT_TYPE")
                    continue
                try:
                    operations.append(_operation_from_edit(edit))
                except Exception as exc:
                    errors.append(str(exc))

    operations.extend(_check_operations(plan.get("checks")))

    if errors:
        record = _invalid_changeset(plan, errors, agent_run_id=agent_run_id, result_path=result_path)
        record["parse_diagnostics"] = {
            "raw_length": plan.get("_raw_length"),
            "had_parse_error": bool(plan.get("_parse_error")),
            "edit_count": len(edits) if isinstance(edits, list) else 0,
            "operation_count": len(operations),
            "error_count": len(errors),
            "recovery_classification": record.get("recovery_classification"),
            "retry_guidance": record.get("retry_guidance"),
        }
        write_record(CHANGESETS_DIR / f"{record['id']}.yaml", record)
        return record

    record = {

        "schema": SUPPORTED_SCHEMA,
        "id": str(plan.get("changeset_id") or plan.get("id") or new_id("chg")),
        "roadmap_id": str(plan.get("roadmap_id") or "unknown"),
        "summary": str(plan.get("summary") or "Compiled ImplementationAgent edit plan"),
        "risk_level": str(plan.get("risk_level") or "L2"),
        "status": "proposed",
        "operations": operations,
        "generated_by": "implementation_edit_plan",
        "agent_run_id": agent_run_id,
        "result_path": result_path.as_posix(),
        "source_edit_plan": plan,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "no_action_executed": True,
    }
    ok, messages = validate_changeset(record, for_apply=True)
    record["validation"] = {"ok": ok, "messages": messages, "validated_at": now_iso()}
    record["output_type"] = "changeset"
    if not ok:
        record["status"] = "invalid"

    CHANGESETS_DIR.mkdir(parents=True, exist_ok=True)
    write_record(CHANGESETS_DIR / f"{record['id']}.yaml", record)
    append_event("changeset.edit_plan_compiled", str(record.get("summary") or record["id"]), {"changeset_id": record["id"], "ok": ok, "messages": messages})
    return record
