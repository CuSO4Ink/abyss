from __future__ import annotations

import json
from pathlib import Path

from abyss_cli.utils import now_iso, repo_root

ROOT = repo_root()


def replace_op(op_id: str, path: str, old: str, new: str) -> dict:
    text = (ROOT / path).read_text(encoding="utf-8")
    assert old in text, f"old content not found for {op_id}"
    assert text.count(old) == 1, f"old content not unique for {op_id}: {text.count(old)}"
    return {
        "id": op_id,
        "kind": "fs.replace_exact",
        "target": {"path": path},
        "input": {"old_content": old, "new_content": new},
    }

workflow_old = '''def _context_pack_included_files(agent_run: dict[str, Any]) -> set[str]:
    """Return files included in the Context Pack used by an agent run."""
    context = agent_run.get("context") if isinstance(agent_run.get("context"), dict) else {}
    files = context.get("files_included") if isinstance(context.get("files_included"), list) else []
    included = {str(path) for path in files if path}
    pack_id = context.get("context_pack_id")
    if pack_id:
        pack_path = CONTEXT_PACKS_DIR / f"{pack_id}.yaml"
        if pack_path.exists():
            try:
                pack_record = read_record(pack_path)
                for path in pack_record.get("files_included", []):
                    if path:
                        included.add(str(path))
            except Exception:
                pass
    return included


def _create_owner_changeset_item(workflow: dict[str, Any], changeset: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
'''
workflow_new = '''def _context_pack_included_files(agent_run: dict[str, Any]) -> set[str]:
    """Return files included in the Context Pack used by an agent run."""
    context = agent_run.get("context") if isinstance(agent_run.get("context"), dict) else {}
    files = context.get("files_included") if isinstance(context.get("files_included"), list) else []
    included = {str(path) for path in files if path}
    pack_id = context.get("context_pack_id")
    if pack_id:
        pack_path = CONTEXT_PACKS_DIR / f"{pack_id}.yaml"
        if pack_path.exists():
            try:
                pack_record = read_record(pack_path)
                for path in pack_record.get("files_included", []):
                    if path:
                        included.add(str(path))
            except Exception:
                pass
    return included


def _is_placeholder_format_feedback_request(record: dict[str, Any]) -> bool:
    """Return true when a context_request is placeholder-related format feedback."""
    if record.get("request_kind") != "format_feedback":
        return False
    markers = (
        "placeholder content is not allowed",
        "ellipsis placeholder expression is not allowed",
        "existing code",
        "placeholder",
        "omitted",
        "TODO",
    )
    texts = [str(record.get("retry_guidance") or ""), str(record.get("reason") or ""), str(record.get("suggestion") or "")]
    missing = record.get("missing") if isinstance(record.get("missing"), list) else []
    for item in missing:
        if not isinstance(item, dict):
            continue
        texts.extend(str(item.get(key) or "") for key in ("need", "reason", "retry_guidance"))
    combined = "\\n".join(texts).lower()
    return any(marker.lower() in combined for marker in markers)


def _prior_placeholder_format_feedback_ids(workflow: dict[str, Any], *, exclude_id: str = "") -> list[str]:
    """Return prior placeholder format_feedback context request ids for this workflow."""
    context_requests_dir = runtime_root() / "process" / "context_requests"
    if not context_requests_dir.exists():
        return []
    candidate_ids: list[str] = []
    current_id = str(workflow.get("context_request_id") or "")
    if current_id and current_id != exclude_id:
        candidate_ids.append(current_id)
    history = workflow.get("history") if isinstance(workflow.get("history"), list) else []
    for event in reversed(history):
        details = event.get("details") if isinstance(event, dict) else {}
        if not isinstance(details, dict) or not details.get("context_request_id"):
            continue
        ctx_id = str(details.get("context_request_id"))
        if ctx_id and ctx_id != exclude_id and ctx_id not in candidate_ids:
            candidate_ids.append(ctx_id)
    matches: list[str] = []
    for ctx_id in candidate_ids:
        ctx_path = context_requests_dir / f"{ctx_id}.yaml"
        if not ctx_path.exists():
            continue
        try:
            ctx_req = read_record(ctx_path)
        except Exception:
            continue
        if _is_placeholder_format_feedback_request(ctx_req):
            matches.append(ctx_id)
    return matches


def _create_owner_changeset_item(workflow: dict[str, Any], changeset: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
'''

workflow_branch_old = '''                workflow["last_error"] = f"context_request: {reason}"
                workflow["context_request_id"] = result.get("id")
                workflow["context_request_missing_files"] = missing_files
                return _record_transition(workflow, "blocked", "implementation_context_insufficient", {
                    "agent_run_id": agent_run.get("id"),
                    "context_request_id": result.get("id"),
                    "missing_files": missing_files,
                    "request_kind": request_kind or ("local_edit_context" if has_local_edit_request else ""),
                    "reason": reason,
                })

            # Handle blocked_result output
'''
workflow_branch_new = '''                ctx_id = str(result.get("id") or "")
                if _is_placeholder_format_feedback_request(result):
                    prior_placeholder_ctx_ids = _prior_placeholder_format_feedback_ids(workflow, exclude_id=ctx_id)
                    if prior_placeholder_ctx_ids:
                        workflow["last_error"] = "repeated_placeholder_format_feedback: Implementation Agent repeated placeholder edit-plan output after mandatory corrective feedback"
                        workflow["context_request_id"] = result.get("id")
                        workflow["context_request_missing_files"] = missing_files
                        return _record_transition(workflow, "blocked", "implementation_repeated_placeholder_blocked", {
                            "agent_run_id": agent_run.get("id"),
                            "context_request_id": result.get("id"),
                            "prior_context_request_ids": prior_placeholder_ctx_ids[:5],
                            "missing_files": missing_files,
                            "request_kind": "format_feedback",
                            "reason": "Implementation Agent repeated placeholder output after placeholder format_feedback was already recorded for this workflow; stop automatic retry and require corrected implementation path.",
                        })
                workflow["last_error"] = f"context_request: {reason}"
                workflow["context_request_id"] = result.get("id")
                workflow["context_request_missing_files"] = missing_files
                return _record_transition(workflow, "blocked", "implementation_context_insufficient", {
                    "agent_run_id": agent_run.get("id"),
                    "context_request_id": result.get("id"),
                    "missing_files": missing_files,
                    "request_kind": request_kind or ("local_edit_context" if has_local_edit_request else ""),
                    "reason": reason,
                })

            # Handle blocked_result output
'''

summary_categories_old = '''WORKFLOW_FAILURE_CATEGORIES = (
    ("context_request", "context_insufficient"),
    ("context insufficient", "context_insufficient"),
    ("implementation_context_insufficient", "context_insufficient"),
    ("implementation_agent_redundant_context_request", "context_insufficient"),
    ("task_type", "task_type_misclassification"),
'''
summary_categories_new = '''WORKFLOW_FAILURE_CATEGORIES = (
    ("repeated_placeholder_format_feedback", "repeated_placeholder_output"),
    ("implementation_repeated_placeholder_blocked", "repeated_placeholder_output"),
    ("context_request", "context_insufficient"),
    ("context insufficient", "context_insufficient"),
    ("implementation_context_insufficient", "context_insufficient"),
    ("implementation_agent_redundant_context_request", "context_insufficient"),
    ("task_type", "task_type_misclassification"),
'''

summary_outcome_old = '''    if status == "blocked":
        blocked_result_id = workflow.get("blocked_result_id")
        last_error = workflow.get("last_error", "")
        if "context_request" in last_error:
            return "context_insufficient"
        if blocked_result_id:
'''
summary_outcome_new = '''    if status == "blocked":
        blocked_result_id = workflow.get("blocked_result_id")
        last_error = workflow.get("last_error", "")
        if "repeated_placeholder_format_feedback" in last_error:
            return "context_insufficient"
        if "context_request" in last_error:
            return "context_insufficient"
        if blocked_result_id:
'''

context_manifest_old = '''    declared_target_files: list[str] = []
    if isinstance(target_record, dict):
        _extend_declared_targets(target_record.get("target_file"), declared_target_files)
        _extend_declared_targets(target_record.get("target_module"), declared_target_files)
        details_text = str(target_record.get("details") or "")
        for part in details_text.split(";"):
            key, sep, value = part.partition("=")
            if sep and key.strip() in {"target_file", "target_module"}:
                _extend_declared_targets(value.strip(), declared_target_files)


    # Get rule source files for this task type from Rule Source Registry
'''
context_manifest_new = '''    declared_target_files: list[str] = []
    if isinstance(target_record, dict):
        _extend_declared_targets(target_record.get("target_file"), declared_target_files)
        _extend_declared_targets(target_record.get("target_module"), declared_target_files)
        manifest = target_record.get("task_coverage_manifest") if isinstance(target_record.get("task_coverage_manifest"), dict) else {}
        _extend_declared_targets(manifest.get("expected_files"), declared_target_files)
        details_text = str(target_record.get("details") or "")
        for part in details_text.split(";"):
            key, sep, value = part.partition("=")
            if sep and key.strip() in {"target_file", "target_module"}:
                _extend_declared_targets(value.strip(), declared_target_files)


    # Get rule source files for this task type from Rule Source Registry
'''

agent_runner_old = '''def _latest_context_request_files(proposal_id: str) -> list[str]:
    """Return files requested by the latest context request for this proposal.

    The actual disclosure safety check remains in Context Broker's target-file
    policy; this helper only carries forward the workflow's recorded request.
    """
    workflows_dir = runtime_root() / "process" / "workflows"
    if not proposal_id or not workflows_dir.exists():
        return []
    workflows = [read_record(path) for path in list_records(workflows_dir, "wf")]
    matches = [wf for wf in workflows if str(wf.get("proposal_id") or "") == proposal_id]
    for workflow in sorted(matches, key=lambda item: item.get("updated_at", ""), reverse=True):
        history = workflow.get("history") if isinstance(workflow.get("history"), list) else []
        last_event = history[-1] if history else {}
        details = last_event.get("details") if isinstance(last_event, dict) else {}
        if not isinstance(details, dict):
            continue
        files = workflow.get("context_request_missing_files") or details.get("missing_files") or []
        if not isinstance(files, list):
            continue
        return [str(path) for path in files if path]
    return []


def _resolve_action_target(target: str) -> Path:
'''
agent_runner_new = '''def _latest_context_request_files(proposal_id: str) -> list[str]:
    """Return concrete files requested by recent context requests for this proposal.

    The actual disclosure safety check remains in Context Broker's target-file
    policy; this helper only carries forward recorded repo-file requests and
    skips format_feedback placeholders such as ``unknown``.
    """
    workflows_dir = runtime_root() / "process" / "workflows"
    if not proposal_id or not workflows_dir.exists():
        return []

    def _concrete_files(raw_files: Any) -> list[str]:
        if not isinstance(raw_files, list):
            return []
        concrete: list[str] = []
        for item in raw_files:
            path = str(item or "").strip()
            if not path or path == "unknown" or "/" not in path:
                continue
            if path not in concrete:
                concrete.append(path)
        return concrete

    workflows = [read_record(path) for path in list_records(workflows_dir, "wf")]
    matches = [wf for wf in workflows if str(wf.get("proposal_id") or "") == proposal_id]
    for workflow in sorted(matches, key=lambda item: item.get("updated_at", ""), reverse=True):
        current_files = _concrete_files(workflow.get("context_request_missing_files"))
        if current_files:
            return current_files
        history = workflow.get("history") if isinstance(workflow.get("history"), list) else []
        for event in reversed(history):
            details = event.get("details") if isinstance(event, dict) else {}
            if not isinstance(details, dict):
                continue
            files = _concrete_files(details.get("missing_files"))
            if files:
                return files
    return []


def _resolve_action_target(target: str) -> Path:
'''

record = {
    "schema": "abyss.change_set.v1",
    "id": "chg_r060_repeated_placeholder_handling",
    "roadmap_id": "R060",
    "summary": "Deterministically block repeated placeholder format_feedback and preserve concrete context-request files",
    "risk_level": "L2",
    "status": "proposed",
    "operations": [
        replace_op("op_001", "abyss_cli/workflow.py", workflow_old, workflow_new),
        replace_op("op_002", "abyss_cli/workflow.py", workflow_branch_old, workflow_branch_new),
        replace_op("op_003", "abyss_cli/summary.py", summary_categories_old, summary_categories_new),
        replace_op("op_004", "abyss_cli/summary.py", summary_outcome_old, summary_outcome_new),
        replace_op("op_005", "abyss_cli/context_pack.py", context_manifest_old, context_manifest_new),
        replace_op("op_006", "abyss_cli/agent_runner.py", agent_runner_old, agent_runner_new),
        {"id": "op_007", "kind": "check.command", "input": {"command": "python -m compileall -q abyss_cli"}},
        {"id": "op_008", "kind": "check.command", "input": {"command": "python -m abyss_cli check"}},
        {"id": "op_009", "kind": "check.command", "input": {"command": "python -m abyss_cli summary --check"}},
    ],
    "created_at": now_iso(),
    "updated_at": now_iso(),
    "metadata": {
        "corrects_workflow_id": "wf_20260526_135904_03e5e5",
        "corrects_block_event": "implementation_repeated_placeholder_blocked",
    },
}

out = ROOT / "artifacts" / "drafts" / "chg_r060_repeated_placeholder_handling.json"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
