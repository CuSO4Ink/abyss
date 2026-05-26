import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_between(text: str, start_marker: str, end_marker: str, new_block: str) -> tuple[str, str]:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    old = text[start:end]
    return old, new_block

patch_path = ROOT / "abyss_cli" / "patch_compiler.py"
agent_path = ROOT / "abyss_cli" / "agent_runner.py"

patch_text = patch_path.read_text(encoding="utf-8")
agent_text = agent_path.read_text(encoding="utf-8")

old_patch, new_patch = replace_between(
    patch_text,
    "def _invalid_changeset(plan: dict[str, Any] | None, messages: list[str], *, agent_run_id: str | None, result_path: Path) -> dict[str, Any]:",
    "\ndef _parse_edit_plan_json",
    '''def _invalid_changeset(plan: dict[str, Any] | None, messages: list[str], *, agent_run_id: str | None, result_path: Path) -> dict[str, Any]:
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

'''
)

old_agent, new_agent = replace_between(
    agent_text,
    "def _context_request_from_invalid_edit_plan(compiled_changeset: dict[str, Any]) -> dict[str, Any] | None:",
    "\ndef _has_relevant_recent_implementation_failures",
    '''def _context_request_from_invalid_edit_plan(compiled_changeset: dict[str, Any]) -> dict[str, Any] | None:
    validation = compiled_changeset.get("validation") if isinstance(compiled_changeset.get("validation"), dict) else {}
    messages = [str(message) for message in validation.get("messages") or []]
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
    context_recoverable = [message for message in messages if any(marker in message for marker in context_markers)]
    format_recoverable = [message for message in messages if any(marker in message for marker in format_markers)]
    placeholder_recoverable = [message for message in messages if any(marker in message for marker in placeholder_markers)]
    recoverable = context_recoverable[:]
    for message in format_recoverable + placeholder_recoverable:
        if message not in recoverable:
            recoverable.append(message)
    if not recoverable:
        return None

    missing: list[dict[str, str]] = []
    seen_files: set[str] = set()
    for message in context_recoverable:
        rel_path = _target_file_from_edit_plan_error(message)
        if not rel_path or rel_path in seen_files:
            continue
        seen_files.add(rel_path)
        if "replace_symbol target is too large" in message:
            need = "use replace_anchor or append_after_anchor with a small unique anchor instead of replace_symbol for this large function"
        elif "symbol not found" in message:
            need = "verify the exact symbol name exists in this file; use a unique anchor from the target region instead"
        elif "anchor match count is" in message:
            need = "the specified anchor text does not uniquely match in this file; provide a different exact unique anchor from the target region"
        else:
            need = "a smaller unique anchor or nearby exact source context for a local edit"
        missing.append({
            "file": rel_path,
            "need": need,
            "reason": message,
            "request_kind": "local_edit_context",
            "retry_guidance": "Use replace_anchor or append_after_anchor with a small exact unique snippet visible in the provided context. If no safe anchor is visible, request local_edit_context instead of guessing.",
        })
    for message in format_recoverable:
        missing.append({
            "file": "unknown",
            "need": "a syntactically valid abyss-edit-plan JSON block with a non-empty edits array",
            "reason": message,
            "request_kind": "format_feedback",
            "retry_guidance": "Retry with a strictly valid abyss-edit-plan fenced JSON block. Include schema abyss.edit_plan.v1 and at least one edit; escape newlines and quotes inside JSON string values.",
        })
    for message in placeholder_recoverable:
        missing.append({
            "file": "unknown",
            "need": "complete concrete code with no placeholder markers in content or new_content",
            "reason": message,
            "request_kind": "format_feedback",
            "retry_guidance": "Replace placeholder markers such as existing code, placeholder, omitted, ellipsis, or TODO with complete concrete code. Do not use abbreviated code or prose placeholders inside new_content/content.",
        })
    if not missing:
        missing.append({
            "file": "unknown",
            "need": "a smaller unique anchor or exact local source context for the failed edit-plan operation",
            "reason": recoverable[0],
            "request_kind": "local_edit_context",
            "retry_guidance": "Use replace_anchor or append_after_anchor with a small unique snippet instead of replace_symbol.",
        })

    has_format_feedback = any(item.get("request_kind") == "format_feedback" for item in missing)
    request_kind = "format_feedback" if has_format_feedback and not context_recoverable else "local_edit_context"
    recovery_classification = "format_feedback" if has_format_feedback and not context_recoverable else "context_insufficient"
    if recovery_classification == "format_feedback":
        reason = "Implementation edit plan could not be compiled because the edit-plan output was malformed, empty, or contained placeholder content."
        suggestion = "Regenerate the implementation as a valid abyss-edit-plan JSON block with complete concrete code and no placeholders."
    else:
        reason = "Implementation edit plan could not be safely compiled into a ChangeSet due to symbol/anchor resolution failure; more precise local context or a smaller unique anchor is required."
        suggestion = "Regenerate the implementation using replace_anchor/append_after_anchor with a small exact unique anchor visible in the provided Repository Files, or request the exact local source region needed for the edit."

    req_id = new_id("ctx_req")
    record = {
        "schema": "abyss.context_request.v1",
        "id": req_id,
        "output_type": "context_request",
        "agent_id": "implementation",
        "roadmap_id": compiled_changeset.get("roadmap_id"),
        "proposal_id": "unknown",
        "agent_run_id": compiled_changeset.get("agent_run_id"),
        "result_path": compiled_changeset.get("result_path"),
        "source_changeset_id": compiled_changeset.get("id"),
        "missing": missing,
        "request_kind": request_kind,
        "recovery_classification": recovery_classification,
        "reason": reason,
        "suggestion": suggestion,
        "retry_guidance": compiled_changeset.get("retry_guidance") or missing[0].get("retry_guidance"),
        "created_at": now_iso(),
    }
    ctx_req_dir = runtime_root() / "process" / "context_requests"
    ctx_req_dir.mkdir(parents=True, exist_ok=True)
    write_record(ctx_req_dir / f"{req_id}.yaml", record)
    append_event("agent.output.context_request_from_invalid_edit_plan", "Invalid edit plan converted to recoverable context request", {
        "context_request_id": req_id,
        "source_changeset_id": compiled_changeset.get("id"),
        "recovery_classification": recovery_classification,
        "request_kind": request_kind,
        "messages": recoverable,
    })
    return record

'''
)

record = {
    "schema": "abyss.change_set.v1",
    "id": "chg_r056_corrected_anchor_placeholder_feedback",
    "roadmap_id": "R056",
    "summary": "Convert anchor and placeholder invalid edit-plan failures into actionable recoverable feedback",
    "risk_level": "L2",
    "status": "proposed",
    "operations": [
        {
            "id": "op_001",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/patch_compiler.py"},
            "input": {"old_content": old_patch, "new_content": new_patch},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "op_002",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/agent_runner.py"},
            "input": {"old_content": old_agent, "new_content": new_agent},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "check_001",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": "python -m compileall -q abyss_cli"},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        },
        {
            "id": "check_002",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": "python -m abyss_cli check"},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        },
    ],
    "generated_by": "corrected_changeset",
    "agent_run_id": "manual_r056_corrected",
    "no_action_executed": True,
}

out = ROOT / "artifacts" / "drafts" / "chg_r056_corrected_anchor_placeholder_feedback.json"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
