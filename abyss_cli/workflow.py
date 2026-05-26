from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .agent_runner import run_agent, run_harness_changeset_review
from .audit import append_event
from .changeset import apply_changeset, dry_run_changeset, load_changeset
from .evolution import PROPOSALS_DIR, show_evolution_record
from .integrity import run_checks
from .utils import list_records, new_id, now_iso, read_record, relative_to_repo, resolve_record_arg, runtime_root, write_record

WORKFLOWS_DIR = runtime_root() / "process" / "workflows"
REPORTS_DIR = runtime_root() / "process" / "reports"
LOCK_PATH = runtime_root() / "process" / "workflow.lock"
CONTEXT_PACKS_DIR = runtime_root() / "process" / "context_packs"


TERMINAL_STATES = {"done", "failed", "blocked", "rejected", "superseded"}
WAITING_STATES = {"waiting_owner_approval"}

_STATE_DISPLAY_LABELS: dict[str, str] = {
    "implementation_pending": "Pending Implementation",
    "implementation_running": "Implementing",
    "changeset_proposed": "ChangeSet Proposed",
    "dry_run_passed": "Dry-Run Passed",
    "harness_review_running": "Harness Reviewing",
    "waiting_owner_approval": "Awaiting Owner",
    "approved_for_execution": "Approved for Execution",
    "executing": "Executing",
    "checking": "Checking Integrity",
    "done": "Done",
    "failed": "Failed",
    "blocked": "Blocked",
    "rejected": "Rejected",
    "superseded": "Superseded by Corrected ChangeSet",
}


def state_display_label(status: str) -> str:
    """Return a human-friendly display label for a workflow status."""
    return _STATE_DISPLAY_LABELS.get(status, status)



class WorkflowLock:
    def __enter__(self) -> None:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(now_iso())
        except FileExistsError as exc:
            raise SystemExit(f"Workflow is already running or stale lock exists: {relative_to_repo(LOCK_PATH)}") from exc

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def _workflow_path(workflow_id: str) -> Path:
    return WORKFLOWS_DIR / f"{workflow_id}.yaml"


def _report_path(report_id: str) -> Path:
    return REPORTS_DIR / f"{report_id}.yaml"


def list_workflows() -> list[dict[str, Any]]:
    return [read_record(path) for path in list_records(WORKFLOWS_DIR, "wf")]


def resolve_workflow(value: str) -> Path:
    return resolve_record_arg(WORKFLOWS_DIR, value, "wf")


def load_workflow(value: str) -> dict[str, Any]:
    return read_record(resolve_workflow(value))


def _write_workflow(record: dict[str, Any]) -> dict[str, Any]:
    record["updated_at"] = now_iso()
    write_record(_workflow_path(str(record["id"])), record)
    return record


def _existing_workflow_for_proposal(proposal_id: str) -> dict[str, Any] | None:
    for workflow in list_workflows():
        if workflow.get("proposal_id") == proposal_id:
            return workflow
    return None


def create_workflow_for_proposal(proposal: dict[str, Any], *, provider: str = "cli", source: str = "proposal_approved") -> dict[str, Any]:
    proposal_id = str(proposal.get("id") or "")
    if not proposal_id:
        raise SystemExit("Cannot create workflow for proposal without id")
    existing = _existing_workflow_for_proposal(proposal_id)
    if existing:
        return existing
    if proposal.get("status") != "approved" or not proposal.get("implementation_allowed"):
        raise SystemExit(f"Proposal is not approved for implementation: {proposal_id}")
    roadmap_id = str(proposal.get("roadmap_entry") or "")
    if not roadmap_id:
        raise SystemExit(f"Approved proposal has no roadmap entry: {proposal_id}")
    workflow = {
        "schema": "abyss.workflow.v1",
        "id": new_id("wf"),
        "proposal_id": proposal_id,
        "roadmap_id": roadmap_id,
        "summary": proposal.get("title") or proposal.get("purpose") or proposal_id,
        "status": "implementation_pending",
        "provider": provider,
        "source": source,
        "attempts": {"implementation": 0, "harness_review": 0, "execution": 0},
        "history": [
            {"at": now_iso(), "state": "implementation_pending", "event": "workflow_created", "source": source}
        ],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    _write_workflow(workflow)
    append_event("workflow.created", str(workflow.get("summary")), {"workflow_id": workflow["id"], "proposal_id": proposal_id, "roadmap_id": roadmap_id})
    return workflow


def start_workflow(target: str = "latest", *, provider: str = "cli") -> dict[str, Any]:
    _path, proposal = show_evolution_record(target)
    if proposal.get("type") != "evolution_proposal":
        raise SystemExit("Workflow can only start from an approved evolution proposal")
    return create_workflow_for_proposal(proposal, provider=provider, source="workflow_start")


def _active_workflow() -> dict[str, Any] | None:
    active = [wf for wf in list_workflows() if wf.get("status") not in TERMINAL_STATES]
    if not active:
        return None
    return sorted(active, key=lambda item: item.get("updated_at", ""))[0]


def _record_transition(workflow: dict[str, Any], status: str, event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    workflow["status"] = status
    workflow.setdefault("history", []).append({"at": now_iso(), "state": status, "event": event, "details": details or {}})
    _write_workflow(workflow)
    append_event("workflow.transition", event, {"workflow_id": workflow.get("id"), "status": status, **(details or {})})
    return workflow


def _context_pack_included_files(agent_run: dict[str, Any]) -> set[str]:
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
    combined = "\n".join(texts).lower()
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

    from .owner import create_owner_item

    return create_owner_item(
        item_type="changeset_approval",
        target_id=str(changeset.get("id")),
        workflow_id=str(workflow.get("id")),
        title=f"Approve ChangeSet {changeset.get('id')} for {workflow.get('roadmap_id')}",
        details={
            "roadmap_id": workflow.get("roadmap_id"),
            "proposal_id": workflow.get("proposal_id"),
            "changeset_summary": changeset.get("summary"),
            "risk_level": changeset.get("risk_level"),
            "harness_review_id": review.get("id"),
            "harness_verdict": review.get("verdict"),
            "harness_recommendation": review.get("recommendation"),
        },
    )


def generate_workflow_report(workflow: dict[str, Any]) -> dict[str, Any]:
    report = {
        "schema": "abyss.workflow_report.v1",
        "id": new_id("wfrep"),
        "workflow_id": workflow.get("id"),
        "roadmap_id": workflow.get("roadmap_id"),
        "proposal_id": workflow.get("proposal_id"),
        "status": workflow.get("status"),
        "changeset_id": workflow.get("changeset_id"),
        "harness_review_id": workflow.get("harness_review_id"),
        "owner_item_id": workflow.get("owner_item_id"),
        "execution_id": workflow.get("execution_id"),
        "check": workflow.get("check"),
        "history": workflow.get("history", []),
        "created_at": now_iso(),
    }
    write_record(_report_path(str(report["id"])), report)
    workflow["report_id"] = report["id"]
    _write_workflow(workflow)
    append_event("workflow.report.created", "Workflow report created", {"workflow_id": workflow.get("id"), "report_id": report["id"]})
    return report


def workflow_tick(*, provider: str | None = None, workflow_id: str | None = None) -> dict[str, Any]:
    with WorkflowLock():
        workflow = load_workflow(workflow_id) if workflow_id else _active_workflow()
        if not workflow:
            return {"schema": "abyss.workflow_tick.v1", "status": "idle", "message": "no active workflow", "created_at": now_iso()}

        status = str(workflow.get("status"))
        provider_name = provider or str(workflow.get("provider") or "cli")

        if status == "implementation_running":
            if int(workflow.get("attempts", {}).get("implementation", 0)) < 2:
                return _record_transition(workflow, "implementation_pending", "recovered_stale_implementation_running", {"reason": "no active workflow lock"})
            return _record_transition(workflow, "failed", "stale_implementation_running", {"reason": "implementation was started but did not produce a changeset"})

        if status == "harness_review_running":
            if int(workflow.get("attempts", {}).get("harness_review", 0)) < 2:
                return _record_transition(workflow, "dry_run_passed", "recovered_stale_harness_review_running", {"reason": "no active workflow lock"})
            return _record_transition(workflow, "failed", "stale_harness_review_running", {"reason": "harness review was started but did not produce a review"})

        if status == "executing":
            return _record_transition(workflow, "blocked", "stale_executor_running", {"reason": "executor may have been interrupted; owner recovery required before retry"})

        if status == "implementation_pending":
            workflow["provider"] = provider_name
            workflow["attempts"]["implementation"] = int(workflow.get("attempts", {}).get("implementation", 0)) + 1
            workflow["context_pack_id"] = None  # Track context pack usage for audit
            _record_transition(workflow, "implementation_running", "implementation_agent_started", {"provider": provider_name})
            try:
                agent_run, result = run_agent("implementation", target=str(workflow.get("proposal_id")), provider=provider_name)
            except (Exception, SystemExit) as exc:
                error_msg = str(exc)
                workflow["last_error"] = error_msg
                # Detect transient provider errors and allow one retry
                transient_markers = ["timed out", "timeout", "empty stdout", "empty filtered response", "empty response"]
                is_transient = any(marker in error_msg.lower() for marker in transient_markers)
                current_attempts = int(workflow.get("attempts", {}).get("implementation", 0))
                if is_transient and current_attempts < 2:
                    return _record_transition(workflow, "implementation_pending", "implementation_agent_transient_failure_retry", {"error": error_msg, "attempt": current_attempts, "transient": True})
                return _record_transition(workflow, "failed", "implementation_agent_failed", {"error": error_msg})
            if not result:
                return _record_transition(workflow, "failed", "implementation_agent_produced_no_output", {"agent_run_id": agent_run.get("id")})

            output_type = result.get("output_type", "changeset")
            workflow["implementation_agent_run_id"] = agent_run.get("id")

            # Handle context_request output
            if output_type == "context_request":
                missing_items = result.get("missing", []) if isinstance(result.get("missing"), list) else []
                missing_files = [m.get("file") for m in missing_items if isinstance(m, dict)]
                reason = result.get("reason", "Context insufficient")
                request_kind = str(result.get("request_kind") or "")
                has_local_edit_request = request_kind == "local_edit_context" or any(
                    isinstance(m, dict) and m.get("request_kind") == "local_edit_context" for m in missing_items
                )
                included_files = _context_pack_included_files(agent_run)
                requested_existing_files = [f for f in missing_files if f and f in included_files]
                if requested_existing_files and not has_local_edit_request:
                    workflow["last_error"] = "context_request_redundant: agent requested files already included in Context Pack"
                    workflow["context_request_id"] = result.get("id")
                    workflow["context_request_missing_files"] = missing_files
                    return _record_transition(workflow, "failed", "implementation_agent_redundant_context_request", {
                        "agent_run_id": agent_run.get("id"),
                        "context_request_id": result.get("id"),
                        "missing_files": missing_files,
                        "files_already_included": requested_existing_files,
                        "context_pack_id": agent_run.get("context", {}).get("context_pack_id") if isinstance(agent_run.get("context"), dict) else None,
                        "reason": reason,
                    })
                ctx_id = str(result.get("id") or "")
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



            if output_type == "blocked_result":
                blocked_reason = result.get("blocked_reason", "Task blocked")
                category = result.get("category", "unknown")
                workflow["last_error"] = f"blocked: [{category}] {blocked_reason}"
                workflow["blocked_result_id"] = result.get("id")
                return _record_transition(workflow, "blocked", "implementation_blocked", {
                    "agent_run_id": agent_run.get("id"),
                    "blocked_result_id": result.get("id"),
                    "category": category,
                    "reason": blocked_reason,
                })

            # Handle normal changeset output
            workflow["changeset_id"] = result.get("id")
            workflow["changeset_valid"] = result.get("validation", {}).get("ok")
            if not result.get("validation", {}).get("ok"):
                validation_messages = [str(message) for message in result.get("validation", {}).get("messages", [])]
                workflow["last_error"] = "; ".join(validation_messages)
                format_error_markers = (
                    "EDIT_PLAN_PARSE_ERROR",
                    "MISSING_EDITS",
                    "MISSING_OPERATIONS",
                    "Invalid ImplementationAgent ChangeSet JSON output",
                    "ChangeSet block was not a JSON object",
                    "placeholder content is not allowed",
                    "ellipsis placeholder expression is not allowed",
                )
                current_attempts = int(workflow.get("attempts", {}).get("implementation", 0))
                has_format_error = any(any(marker in message for marker in format_error_markers) for message in validation_messages)
                if current_attempts < 2 and has_format_error:
                    return _record_transition(workflow, "implementation_pending", "implementation_agent_invalid_output_retry", {
                        "changeset_id": result.get("id"),
                        "messages": validation_messages,
                        "attempt": current_attempts,
                    })
                if has_format_error:
                    return _record_transition(workflow, "blocked", "implementation_agent_invalid_output_blocked", {
                        "changeset_id": result.get("id"),
                        "messages": validation_messages,
                        "attempt": current_attempts,
                    })
                return _record_transition(workflow, "failed", "implementation_agent_produced_invalid_changeset", {"changeset_id": result.get("id")})
            return _record_transition(workflow, "changeset_proposed", "changeset_generated", {"changeset_id": result.get("id")})

        if status == "changeset_proposed":
            changeset_id = str(workflow.get("changeset_id"))
            report = dry_run_changeset(changeset_id)
            workflow["dry_run"] = report
            if report.get("ok"):
                return _record_transition(workflow, "dry_run_passed", "dry_run_passed", {"changeset_id": changeset_id})
            return _record_transition(workflow, "blocked", "dry_run_failed", {"changeset_id": changeset_id, "messages": report.get("messages")})

        if status == "dry_run_passed":
            changeset_id = str(workflow.get("changeset_id"))
            workflow["attempts"]["harness_review"] = int(workflow.get("attempts", {}).get("harness_review", 0)) + 1
            _record_transition(workflow, "harness_review_running", "harness_review_started", {"changeset_id": changeset_id, "provider": provider_name})
            try:
                agent_run, review = run_harness_changeset_review(changeset_id, provider=provider_name)
            except (Exception, SystemExit) as exc:
                workflow["last_error"] = str(exc)
                return _record_transition(workflow, "failed", "harness_review_failed", {"error": str(exc)})
            workflow["harness_agent_run_id"] = agent_run.get("id")
            workflow["harness_review_id"] = review.get("id")
            verdict = str(review.get("verdict"))
            if verdict == "violation":
                return _record_transition(workflow, "blocked", "harness_review_violation", {"harness_review_id": review.get("id")})
            changeset = load_changeset(changeset_id)
            owner_item = _create_owner_changeset_item(workflow, changeset, review)
            workflow["owner_item_id"] = owner_item.get("id")
            return _record_transition(workflow, "waiting_owner_approval", "owner_approval_required", {"owner_item_id": owner_item.get("id"), "harness_review_id": review.get("id")})

        if status == "waiting_owner_approval":
            return {"schema": "abyss.workflow_tick.v1", "status": "waiting_owner_approval", "workflow_id": workflow.get("id"), "owner_item_id": workflow.get("owner_item_id"), "created_at": now_iso()}

        if status == "approved_for_execution":
            changeset_id = str(workflow.get("changeset_id"))
            workflow["attempts"]["execution"] = int(workflow.get("attempts", {}).get("execution", 0)) + 1
            _record_transition(workflow, "executing", "executor_started", {"changeset_id": changeset_id})
            try:
                execution = apply_changeset(changeset_id)
            except (Exception, SystemExit) as exc:
                workflow["last_error"] = str(exc)
                return _record_transition(workflow, "failed", "executor_failed", {"error": str(exc)})
            workflow["execution_id"] = execution.get("id")
            if execution.get("status") != "succeeded":
                return _record_transition(workflow, "failed", "executor_returned_failure", {"execution_id": execution.get("id")})
            return _record_transition(workflow, "checking", "executor_succeeded", {"execution_id": execution.get("id")})

        if status == "checking":
            ok, messages = run_checks()
            workflow["check"] = {"ok": ok, "messages": messages, "checked_at": now_iso()}
            if ok:
                _record_transition(workflow, "done", "workflow_done", {"messages": messages})
                report = generate_workflow_report(workflow)
                return {"schema": "abyss.workflow_tick.v1", "status": "done", "workflow_id": workflow.get("id"), "report_id": report.get("id"), "created_at": now_iso()}
            _record_transition(workflow, "failed", "integrity_check_failed", {"messages": messages})
            report = generate_workflow_report(workflow)
            return {"schema": "abyss.workflow_tick.v1", "status": "failed", "workflow_id": workflow.get("id"), "report_id": report.get("id"), "created_at": now_iso()}

        return {"schema": "abyss.workflow_tick.v1", "status": status, "workflow_id": workflow.get("id"), "message": "no transition available", "created_at": now_iso()}


def workflow_run_until_wait(*, provider: str | None = None, workflow_id: str | None = None, max_steps: int = 12) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    current_id = workflow_id
    for _ in range(max_steps):
        result = workflow_tick(provider=provider, workflow_id=current_id)
        results.append(result)
        if result.get("workflow_id"):
            current_id = str(result.get("workflow_id"))
        status = str(result.get("status"))
        if status in TERMINAL_STATES or status in WAITING_STATES or status == "idle":
            break
    return results


def workflow_watch(*, provider: str | None = None, workflow_id: str | None = None, interval_seconds: int = 300, once: bool = False) -> None:
    interval = max(60, int(interval_seconds))
    current_id = workflow_id
    while True:
        results = workflow_run_until_wait(provider=provider, workflow_id=current_id, max_steps=12)
        print(render_json(results))
        if results and results[-1].get("workflow_id"):
            current_id = str(results[-1].get("workflow_id"))
        if once:
            return
        time.sleep(interval)


def load_report(value: str) -> dict[str, Any]:
    from .utils import resolve_record_arg

    return read_record(resolve_record_arg(REPORTS_DIR, value, "wfrep"))


def list_reports() -> list[dict[str, Any]]:
    return [read_record(path) for path in list_records(REPORTS_DIR, "wfrep")]


def retry_workflow(value: str, *, from_stage: str = "implementation") -> dict[str, Any]:
    workflow = load_workflow(value)
    if workflow.get("status") not in {"failed", "blocked", "rejected", "implementation_running", "harness_review_running"}:
        raise SystemExit(f"Workflow is not retryable from status: {workflow.get('status')}")
    if from_stage == "implementation":
        workflow.setdefault("attempts", {})["implementation"] = 0
        workflow.pop("last_error", None)
        workflow.pop("rejection_reason", None)
        return _record_transition(workflow, "implementation_pending", "owner_retry_implementation", {})
    if from_stage == "changeset":
        changeset_id = str(workflow.get("changeset_id") or "")
        if not changeset_id:
            raise SystemExit("Workflow has no changeset_id to retry")
        from .changeset import validate_changeset

        changeset = load_changeset(changeset_id)
        ok, messages = validate_changeset(changeset, for_apply=False)
        if not ok:
            workflow["last_error"] = "; ".join(messages)
            _write_workflow(workflow)
            raise SystemExit("Existing changeset is still invalid: " + "; ".join(messages))
        workflow["changeset_valid"] = True
        workflow.pop("last_error", None)
        return _record_transition(workflow, "changeset_proposed", "owner_retry_existing_changeset", {"changeset_id": changeset_id})
    if from_stage == "harness_review":
        workflow.setdefault("attempts", {})["harness_review"] = 0
        workflow.pop("last_error", None)
        return _record_transition(workflow, "dry_run_passed", "owner_retry_harness_review", {})
    raise SystemExit(f"Unsupported retry stage: {from_stage}")


def mark_workflow_owner_approved(workflow_id: str, owner_item_id: str) -> dict[str, Any]:
    workflow = load_workflow(workflow_id)
    if workflow.get("status") != "waiting_owner_approval":
        raise SystemExit(f"Workflow is not waiting for owner approval: {workflow.get('status')}")
    if str(workflow.get("owner_item_id")) != owner_item_id:
        raise SystemExit("Owner item does not match workflow")
    return _record_transition(workflow, "approved_for_execution", "owner_approved_changeset", {"owner_item_id": owner_item_id})


def mark_workflow_owner_rejected(workflow_id: str, owner_item_id: str, reason: str = "") -> dict[str, Any]:
    workflow = load_workflow(workflow_id)
    if str(workflow.get("owner_item_id")) != owner_item_id:
        raise SystemExit("Owner item does not match workflow")
    workflow["rejection_reason"] = reason
    return _record_transition(workflow, "rejected", "owner_rejected_changeset", {"owner_item_id": owner_item_id, "reason": reason})

def mark_workflow_superseded(workflow_id: str, *, corrected_changeset_id: str, corrected_workflow_id: str = "", confirmed_by: str = "owner") -> dict[str, Any]:
    """Mark a blocked/failed workflow as superseded by a corrected ChangeSet.

    This transition requires Owner confirmation and records evidence linking
    the corrected ChangeSet to the original workflow. The original execution
    history remains unmodified.
    """
    workflow = load_workflow(workflow_id)
    if workflow.get("status") not in {"blocked", "failed"}:
        raise SystemExit(f"Only blocked or failed workflows can be superseded; current status: {workflow.get('status')}")
    if not corrected_changeset_id:
        raise SystemExit("corrected_changeset_id is required to mark a workflow as superseded")
    # Verify the corrected changeset exists and is applied
    try:
        corrected_cs = load_changeset(corrected_changeset_id)
    except (SystemExit, Exception) as exc:
        raise SystemExit(f"Cannot load corrected changeset {corrected_changeset_id}: {exc}")
    if corrected_cs.get("status") != "applied":
        raise SystemExit(f"Corrected changeset must be in 'applied' status; current: {corrected_cs.get('status')}")
    # Verify roadmap alignment
    cs_roadmap = str(corrected_cs.get("roadmap_id") or "")
    wf_roadmap = str(workflow.get("roadmap_id") or "")
    if cs_roadmap and wf_roadmap and cs_roadmap != wf_roadmap:
        raise SystemExit(f"Roadmap mismatch: workflow targets {wf_roadmap} but corrected changeset targets {cs_roadmap}")
    workflow["superseded_by_changeset_id"] = corrected_changeset_id
    if corrected_workflow_id:
        workflow["superseded_by_workflow_id"] = corrected_workflow_id
    workflow["superseded_confirmed_by"] = confirmed_by
    return _record_transition(workflow, "superseded", "workflow_superseded_by_corrected_changeset", {
        "corrected_changeset_id": corrected_changeset_id,
        "corrected_workflow_id": corrected_workflow_id,
        "confirmed_by": confirmed_by,
        "original_status": workflow.get("status"),
    })



def render_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2)
