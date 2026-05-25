from __future__ import annotations

import json
from typing import Any

from .changeset import list_changesets
from .integrity import run_checks
from .owner import list_owner_items
from .workflow import list_workflows, state_display_label


def _extract_last_event(workflow: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the last meaningful event from workflow history for display."""
    history = workflow.get("history", [])
    if not history:
        return None
    last = history[-1]
    return {
        "event": last.get("event"),
        "state": last.get("state"),
        "at": last.get("at"),
        "details": last.get("details"),
    }


def _classify_workflow_outcome(workflow: dict[str, Any]) -> str:
    """Classify workflow outcome based on status and last event details."""
    status = workflow.get("status")

    if status == "superseded":
        return "superseded_by_corrected_changeset"

    if status == "blocked":
        blocked_result_id = workflow.get("blocked_result_id")
        if blocked_result_id:
            # Check if this is an already_satisfied outcome
            last_error = workflow.get("last_error", "")
            if "already_satisfied" in last_error:
                return "satisfied_without_changes"
        # Check if this is a governance_constraint block
        history = workflow.get("history", [])
        if history:
            last_event = history[-1]
            if last_event.get("event") == "implementation_blocked":
                details = last_event.get("details") or {}
                if details.get("category") == "governance_constraint":
                    return "expected_governance_block"
        return "true_blocked"

    if status == "failed":
        # Check if this failure has been explicitly superseded
        if workflow.get("superseded_by_workflow_id") or workflow.get("superseded_by_roadmap_id"):
            return "superseded_failure"
        last_error = workflow.get("last_error", "")
        # Check if failure is due to context insufficiency vs actual implementation failure
        if "context_request" in last_error:
            return "context_insufficient"
        return "true_failure"

    if status == "done":
        return "successfully_completed"

    if status == "rejected":
        return "owner_rejected"

    return "active_or_pending"


def build_summary(*, include_check: bool = False) -> dict[str, Any]:
    workflows = list_workflows()
    owner_items = list_owner_items(include_closed=False)
    changesets = list_changesets()
    
    # Classify workflows using new outcome classification
    classified_workflows = []
    for workflow in workflows:
        outcome = _classify_workflow_outcome(workflow)
        classified_workflows.append({
            "workflow": workflow,
            "outcome": outcome
        })
    
    active_workflows = [item["workflow"] for item in classified_workflows if item["outcome"] == "active_or_pending"]
    
    # Separate true failures from satisfied/context issues
    true_failures = [item["workflow"] for item in classified_workflows if item["outcome"] == "true_failure"]
    superseded_failures = [item["workflow"] for item in classified_workflows if item["outcome"] == "superseded_failure"]
    superseded_by_corrected = [item["workflow"] for item in classified_workflows if item["outcome"] == "superseded_by_corrected_changeset"]
    true_blocked = [item["workflow"] for item in classified_workflows if item["outcome"] == "true_blocked"]
    expected_governance_blocks = [item["workflow"] for item in classified_workflows if item["outcome"] == "expected_governance_block"]
    satisfied_outcomes = [item["workflow"] for item in classified_workflows if item["outcome"] == "satisfied_without_changes"]
    context_issues = [item["workflow"] for item in classified_workflows if item["outcome"] == "context_insufficient"]
    completed_workflows = [item["workflow"] for item in classified_workflows if item["outcome"] == "successfully_completed"]
    rejected_workflows = [item["workflow"] for item in classified_workflows if item["outcome"] == "owner_rejected"]
    
    # Sort completed workflows by date and limit
    recent_completed = sorted(
        completed_workflows,
        key=lambda x: x.get("updated_at", ""),
        reverse=True
    )[:5]
    
    # Compute operations health counts from already-built lists
    operations_health_counts: dict[str, int] = {
        "active_workflows": len(active_workflows),
        "pending_owner_items": len(owner_items),
        "true_failures": len(true_failures),
        "true_blocked": len(true_blocked),
        "expected_governance_blocks": len(expected_governance_blocks),
        "superseded_failures": len(superseded_failures),
        "superseded_by_corrected_changeset": len(superseded_by_corrected),
        "invalid_changesets": len([item for item in changesets if item.get("status") == "invalid"]),
        "recent_completed_workflows": len(recent_completed),
    }

    summary: dict[str, Any] = {
        "schema": "abyss.summary.v1",
        "operations_health_counts": operations_health_counts,
        "active_workflows": [
            {
                "id": item.get("id"),
                "roadmap_id": item.get("roadmap_id"),
                "proposal_id": item.get("proposal_id"),
                "status": item.get("status"),
                "workflow_state_label": state_display_label(item.get("status", "")),
                "summary": item.get("summary"),
                "owner_item_id": item.get("owner_item_id"),
            }
            for item in active_workflows
        ],
        "pending_owner_items": [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "target_id": item.get("target_id"),
                "workflow_id": item.get("workflow_id"),
                "title": item.get("title"),
            }
            for item in owner_items
        ],
        "workflow_outcomes": {
            "true_failures": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "last_event": _extract_last_event(item),
                }
                for item in true_failures
            ],
            "true_blocked": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "blocked_result_id": item.get("blocked_result_id"),
                    "last_event": _extract_last_event(item),
                }
                for item in true_blocked
            ],
            "satisfied_without_changes": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "blocked_result_id": item.get("blocked_result_id"),
                    "last_event": _extract_last_event(item),
                }
                for item in satisfied_outcomes
            ],
            "context_insufficient": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "context_request_id": item.get("context_request_id"),
                    "last_event": _extract_last_event(item),
                }
                for item in context_issues
            ],
            "expected_governance_blocks": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "blocked_result_id": item.get("blocked_result_id"),
                    "last_event": _extract_last_event(item),
                }
                for item in expected_governance_blocks
            ],
            "owner_rejected": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "rejection_reason": item.get("rejection_reason"),
                    "last_event": _extract_last_event(item),
                }
                for item in rejected_workflows
            ],
            "superseded_failures": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "superseded_by_workflow_id": item.get("superseded_by_workflow_id"),
                    "superseded_by_roadmap_id": item.get("superseded_by_roadmap_id"),
                    "last_event": _extract_last_event(item),
                }
                for item in superseded_failures
            ],
            "superseded_by_corrected_changeset": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "superseded_by_changeset_id": item.get("superseded_by_changeset_id"),
                    "superseded_by_workflow_id": item.get("superseded_by_workflow_id"),
                    "superseded_confirmed_by": item.get("superseded_confirmed_by"),
                    "last_event": _extract_last_event(item),
                }
                for item in superseded_by_corrected
            ]
        },
        "recent_completed_workflows": [
            {
                "workflow_id": item.get("id"),
                "roadmap_id": item.get("roadmap_id"),
                "proposal_id": item.get("proposal_id"),
                "changeset_id": item.get("changeset_id"),
                "execution_id": item.get("execution_id"),
                "report_id": item.get("report_id"),
                "updated_at": item.get("updated_at"),
            }
            for item in recent_completed
        ],
        "changesets": {
            "total": len(changesets),
            "proposed": len([item for item in changesets if item.get("status") == "proposed"]),
            "approved": len([item for item in changesets if item.get("status") == "approved"]),
            "applied": len([item for item in changesets if item.get("status") == "applied"]),
            "invalid": len([item for item in changesets if item.get("status") == "invalid"]),
        },
    }
    if include_check:
        ok, messages = run_checks()
        summary["integrity"] = {"ok": ok, "messages": messages}
    return summary


def render_summary(*, include_check: bool = False) -> str:
    return json.dumps(build_summary(include_check=include_check), ensure_ascii=False, indent=2)
