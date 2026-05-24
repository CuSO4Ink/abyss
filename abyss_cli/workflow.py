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

TERMINAL_STATES = {"done", "failed", "blocked", "rejected"}
WAITING_STATES = {"waiting_owner_approval"}


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
            _record_transition(workflow, "implementation_running", "implementation_agent_started", {"provider": provider_name})
            try:
                agent_run, changeset = run_agent("implementation", target=str(workflow.get("proposal_id")), provider=provider_name)
            except Exception as exc:
                workflow["last_error"] = str(exc)
                return _record_transition(workflow, "failed", "implementation_agent_failed", {"error": str(exc)})
            if not changeset:
                return _record_transition(workflow, "failed", "implementation_agent_produced_no_changeset", {"agent_run_id": agent_run.get("id")})
            workflow["implementation_agent_run_id"] = agent_run.get("id")
            workflow["changeset_id"] = changeset.get("id")
            workflow["changeset_valid"] = changeset.get("validation", {}).get("ok")
            if not changeset.get("validation", {}).get("ok"):
                workflow["last_error"] = "; ".join(changeset.get("validation", {}).get("messages", []))
                return _record_transition(workflow, "failed", "implementation_agent_produced_invalid_changeset", {"changeset_id": changeset.get("id")})
            return _record_transition(workflow, "changeset_proposed", "changeset_generated", {"changeset_id": changeset.get("id")})

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
            except Exception as exc:
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
            except Exception as exc:
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
    if workflow.get("status") not in {"failed", "blocked", "implementation_running", "harness_review_running"}:
        raise SystemExit(f"Workflow is not retryable from status: {workflow.get('status')}")
    if from_stage == "implementation":
        workflow.setdefault("attempts", {})["implementation"] = 0
        workflow.pop("last_error", None)
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


def render_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2)
