from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .audit import append_event
from .fenced_blocks import parse_named_json_block
from .utils import list_records, new_id, now_iso, read_record, relative_to_repo, repo_root, runtime_root, write_record

CHANGESETS_DIR = runtime_root() / "process" / "changesets"
EXECUTIONS_DIR = runtime_root() / "process" / "executions"

SUPPORTED_SCHEMA = "abyss.change_set.v1"
SUPPORTED_OPERATION_KINDS = {
    "fs.create_file",
    "fs.replace_exact",
    "fs.append_file",
    "check.command",
}

ALLOWED_FS_ROOTS = (
    "abyss_cli/",
    "artifacts/drafts/",
    "README.md",
    "SYSTEM_MAP.md",
)

ALLOWED_FS_PATHS = {
    "EXTERNAL_MODEL_ONBOARDING.md",
    "rules/context_manifest.yaml",
    "rules/rule_sources.v1.yaml",
    "rules/contracts/disclosure_plan.v1.yaml",
    "rules/contracts/rule_source_registry.v1.yaml",
    "rules/schemas/disclosure_plan.v1.schema.json",
    "rules/schemas/rule_source_registry.v1.schema.json",
}

BLOCKED_PATH_PREFIXES = (
    ".git/",
    ".local/",
    "audit/",
    "process/",
    "prompts/",
    "rules/",
    "storage/",
    "user_data/",
)

BLOCKED_PATHS = {
    "ABYSS_CONSTITUTION.md",
    "ROADMAP.md",
    "pyproject.toml",
}

ALLOWED_CHECK_COMMANDS = {
    "python -m abyss_cli check": ["python", "-m", "abyss_cli", "check"],
    "python -m compileall -q abyss_cli": ["python", "-m", "compileall", "-q", "abyss_cli"],
    "python -m abyss_cli rules validate --json": ["python", "-m", "abyss_cli", "rules", "validate", "--json"],
    "python -m abyss_cli request types --all --json": ["python", "-m", "abyss_cli", "request", "types", "--all", "--json"],
    "python -m abyss_cli summary --check": ["python", "-m", "abyss_cli", "summary", "--check"],
}

LOW_INFORMATION_DECORATIVE_SYMBOLS = {
    "✓", "✔", "✅", "✗", "✘", "❌", "⚠", "⚠️", "⭐", "★", "→", "➡", "⬆", "⬇",
}


def _decorative_symbol_messages(text: str, op_id: str) -> list[str]:
    messages: list[str] = []
    for symbol in sorted(LOW_INFORMATION_DECORATIVE_SYMBOLS):
        if symbol in text:
            messages.append(f"LOW_INFORMATION_DECORATIVE_SYMBOL {op_id} {symbol!r}")
    return messages


def _record_path(changeset_id: str) -> Path:
    return CHANGESETS_DIR / f"{changeset_id}.yaml"


def _execution_path(execution_id: str) -> Path:
    return EXECUTIONS_DIR / f"{execution_id}.yaml"


def _normalize_path(raw: str) -> str:
    return raw.replace("\\", "/").lstrip("/")


def _target_path(raw: str) -> Path:
    rel = _normalize_path(raw)
    if not rel:
        raise ValueError("missing target path")
    if ".." in Path(rel).parts:
        raise ValueError(f"parent path traversal is not allowed: {rel}")
    return repo_root() / rel


def _is_allowed_fs_path(rel: str) -> bool:
    rel = _normalize_path(rel)
    if rel in BLOCKED_PATHS:
        return False
    if rel in ALLOWED_FS_PATHS:
        return True
    if any(rel.startswith(prefix) for prefix in BLOCKED_PATH_PREFIXES):
        return False
    for root in ALLOWED_FS_ROOTS:
        if root.endswith("/") and rel.startswith(root):
            return True
        if rel == root:
            return True
    return False


def _operation_target_path(operation: dict[str, Any]) -> str:
    target = operation.get("target")
    if isinstance(target, dict):
        return str(target.get("path") or "")
    return str(operation.get("path") or "")


def _operation_input(operation: dict[str, Any]) -> dict[str, Any]:
    data = operation.get("input")
    return data if isinstance(data, dict) else operation


def _validate_operation(operation: dict[str, Any], *, for_apply: bool = False) -> list[str]:
    messages: list[str] = []
    kind = str(operation.get("kind") or "")
    op_id = str(operation.get("id") or kind or "operation")

    if kind not in SUPPORTED_OPERATION_KINDS:
        return [f"UNSUPPORTED_OPERATION {op_id} {kind}"]

    if kind.startswith("fs."):
        rel = _normalize_path(_operation_target_path(operation))
        if not _is_allowed_fs_path(rel):
            messages.append(f"PATH_NOT_ALLOWED {op_id} {rel}")
            return messages

        path = _target_path(rel)
        data = _operation_input(operation)
        if kind == "fs.create_file":
            content = str(data.get("content") if "content" in data else data.get("new_content") or "")
            if "content" not in data and "new_content" not in data:
                messages.append(f"MISSING_CONTENT {op_id}")
            messages.extend(_decorative_symbol_messages(content, op_id))
            if path.exists() and for_apply:
                messages.append(f"TARGET_EXISTS {op_id} {rel}")
        elif kind == "fs.replace_exact":
            old_content = str(data.get("old_content") or "")
            new_content = str(data.get("new_content") or "")
            if not old_content:
                messages.append(f"MISSING_OLD_CONTENT {op_id}")
            if old_content == new_content:
                messages.append(f"NOOP_REPLACE {op_id}")
            if old_content and "\ufffd" in old_content:
                messages.append(f"OLD_CONTENT_CONTAINS_REPLACEMENT_CHARS {op_id} (likely encoding corruption)")
            messages.extend(_decorative_symbol_messages(new_content, op_id))
            if not path.exists():
                messages.append(f"TARGET_MISSING {op_id} {rel}")
            elif for_apply:
                text = path.read_text(encoding="utf-8")
                count = text.count(old_content)
                if count != 1:
                    messages.append(f"OLD_CONTENT_MATCH_COUNT {op_id} {rel} count={count}")
        elif kind == "fs.append_file":
            content = str(data.get("content") or "")
            if "content" not in data:
                messages.append(f"MISSING_CONTENT {op_id}")
            messages.extend(_decorative_symbol_messages(content, op_id))
            if not path.exists() and for_apply:
                messages.append(f"TARGET_MISSING {op_id} {rel}")

    if kind == "check.command":
        data = _operation_input(operation)
        command = str(data.get("command") or "")
        if command not in ALLOWED_CHECK_COMMANDS:
            messages.append(f"COMMAND_NOT_ALLOWED {op_id} {command}")

    return messages


def validate_changeset(record: dict[str, Any], *, for_apply: bool = False) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if record.get("schema") != SUPPORTED_SCHEMA:
        messages.append(f"INVALID_SCHEMA {record.get('schema')}")
    if not record.get("id"):
        messages.append("MISSING_ID")
    if not record.get("roadmap_id"):
        messages.append("MISSING_ROADMAP_ID")
    operations = record.get("operations")
    if not isinstance(operations, list) or not operations:
        messages.append("MISSING_OPERATIONS")
    else:
        for operation in operations:
            if not isinstance(operation, dict):
                messages.append("INVALID_OPERATION_TYPE")
            else:
                messages.extend(_validate_operation(operation, for_apply=for_apply))
    return (not messages, messages or ["OK"])


def _store_imported_changeset(record: dict[str, Any], *, source: str) -> dict[str, Any]:
    if not record.get("id"):
        record["id"] = new_id("chg")
    record.setdefault("schema", SUPPORTED_SCHEMA)
    record.setdefault("status", "proposed")
    record.setdefault("created_at", now_iso())
    record["updated_at"] = now_iso()
    record["no_action_executed"] = True
    record["source"] = source

    ok, messages = validate_changeset(record, for_apply=False)
    record["validation"] = {"ok": ok, "messages": messages, "validated_at": now_iso()}
    write_record(_record_path(str(record["id"])), record)
    append_event("changeset.imported", str(record.get("summary") or record["id"]), {"changeset_id": record["id"], "ok": ok, "source": source})
    return record


def import_changeset(source_path: Path) -> dict[str, Any]:
    record = read_record(source_path)
    return _store_imported_changeset(record, source=relative_to_repo(source_path))


def _parse_changeset_block(text: str) -> tuple[dict[str, Any] | None, str | None, bool]:
    return parse_named_json_block(text, ("abyss-changeset", "abyss-change-set"), object_error="ChangeSet block was not a JSON object")


def import_changeset_from_agent_output(text: str, *, agent_run_id: str | None, result_path: Path) -> dict[str, Any] | None:
    record, parse_error, saw_block = _parse_changeset_block(text)
    if not saw_block:
        append_event("changeset.agent_output_missing", "ImplementationAgent output did not contain an abyss-changeset block", {"agent_run_id": agent_run_id, "result_path": result_path.as_posix()})
        return None
    if record is None and parse_error != "ChangeSet block was not a JSON object":
        fallback = {
            "schema": SUPPORTED_SCHEMA,
            "id": new_id("chg_invalid"),
            "roadmap_id": "unknown",
            "summary": "Invalid ImplementationAgent ChangeSet JSON output",
            "status": "invalid",
            "operations": [],
            "parse_error": parse_error or "unknown parse error",
            "raw_result_path": result_path.as_posix(),
        }
        return _store_imported_changeset(fallback, source="implementation_agent_parse_error")
    if not isinstance(record, dict):
        return _store_imported_changeset({
            "schema": SUPPORTED_SCHEMA,
            "id": new_id("chg_invalid"),
            "roadmap_id": "unknown",
            "summary": "ImplementationAgent ChangeSet block was not a JSON object",
            "status": "invalid",
            "operations": [],
            "raw_result_path": result_path.as_posix(),
        }, source="implementation_agent_invalid_type")
    record["agent_run_id"] = agent_run_id
    record["result_path"] = result_path.as_posix()
    record.setdefault("generated_by", "implementation")
    return _store_imported_changeset(record, source="implementation_agent")


def list_changesets() -> list[dict[str, Any]]:
    return [read_record(path) for path in list_records(CHANGESETS_DIR, "chg")]


def resolve_changeset(value: str) -> Path:
    from .utils import resolve_record_arg

    return resolve_record_arg(CHANGESETS_DIR, value, "chg")


def load_changeset(value: str) -> dict[str, Any]:
    return read_record(resolve_changeset(value))


def set_changeset_status(value: str, status: str, reason: str = "") -> dict[str, Any]:
    if status not in {"approved", "rejected"}:
        raise SystemExit(f"Unsupported changeset status: {status}")
    path = resolve_changeset(value)
    record = read_record(path)
    if record.get("status") == "applied":
        raise SystemExit(f"Cannot change applied changeset: {record.get('id')}")
    ok, messages = validate_changeset(record, for_apply=False)
    if status == "approved" and not ok:
        raise SystemExit("Cannot approve invalid changeset: " + "; ".join(messages))
    record["status"] = status
    record["updated_at"] = now_iso()
    if status == "approved":
        record["approved_at"] = now_iso()
        record["approved_by"] = "user"
    else:
        record["rejected_at"] = now_iso()
        record["rejection_reason"] = reason
    record["validation"] = {"ok": ok, "messages": messages, "validated_at": now_iso()}
    write_record(path, record)
    append_event(f"changeset.{status}", str(record.get("summary") or record.get("id")), {"changeset_id": record.get("id"), "reason": reason})
    return record


def dry_run_changeset(value: str) -> dict[str, Any]:
    record = load_changeset(value)
    ok, messages = validate_changeset(record, for_apply=True)
    report = {
        "schema": "abyss.changeset_dry_run.v1",
        "changeset_id": record.get("id"),
        "ok": ok,
        "messages": messages,
        "checked_at": now_iso(),
        "no_action_executed": True,
    }
    append_event("changeset.dry_run", str(record.get("summary") or record.get("id")), {"changeset_id": record.get("id"), "ok": ok})
    return report


def _apply_operation(operation: dict[str, Any]) -> dict[str, Any]:
    kind = str(operation.get("kind"))
    op_id = str(operation.get("id") or kind)
    data = _operation_input(operation)

    if kind.startswith("fs."):
        rel = _normalize_path(_operation_target_path(operation))
        path = _target_path(rel)
        if kind == "fs.create_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(data.get("content") if "content" in data else data.get("new_content") or ""), encoding="utf-8")
            return {"id": op_id, "kind": kind, "path": rel, "status": "applied"}
        if kind == "fs.replace_exact":
            text = path.read_text(encoding="utf-8")
            old_content = str(data.get("old_content") or "")
            new_content = str(data.get("new_content") or "")
            path.write_text(text.replace(old_content, new_content, 1), encoding="utf-8")
            return {"id": op_id, "kind": kind, "path": rel, "status": "applied"}
        if kind == "fs.append_file":
            with path.open("a", encoding="utf-8") as f:
                f.write(str(data.get("content") or ""))
            return {"id": op_id, "kind": kind, "path": rel, "status": "applied"}

    if kind == "check.command":
        command = str(data.get("command") or "")
        proc = subprocess.run(
            ALLOWED_CHECK_COMMANDS[command],
            cwd=repo_root(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "id": op_id,
            "kind": kind,
            "command": command,
            "status": "passed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }

    raise SystemExit(f"Unsupported operation kind: {kind}")


def apply_changeset(value: str) -> dict[str, Any]:
    path = resolve_changeset(value)
    record = read_record(path)
    if record.get("status") != "approved":
        raise SystemExit(f"Changeset must be approved before apply: {record.get('status')}")

    ok, messages = validate_changeset(record, for_apply=True)
    if not ok:
        raise SystemExit("Dry-run failed: " + "; ".join(messages))

    execution_id = new_id("exec")
    applied: list[dict[str, Any]] = []
    status = "succeeded"
    for operation in record.get("operations", []):
        result = _apply_operation(operation)
        applied.append(result)
        if result.get("status") == "failed":
            status = "failed"
            break

    execution = {
        "schema": "abyss.execution.v1",
        "id": execution_id,
        "changeset_id": record.get("id"),
        "roadmap_id": record.get("roadmap_id"),
        "status": status,
        "operations": applied,
        "created_at": now_iso(),
    }
    write_record(_execution_path(execution_id), execution)

    record["status"] = "applied" if status == "succeeded" else "failed"
    record["execution_id"] = execution_id
    record["updated_at"] = now_iso()
    write_record(path, record)

    append_event("changeset.applied", str(record.get("summary") or record.get("id")), {"changeset_id": record.get("id"), "execution_id": execution_id, "status": status})
    return execution


def render_record(record: dict[str, Any]) -> str:
    import json

    return json.dumps(record, ensure_ascii=False, indent=2)
