from __future__ import annotations

import json
from typing import Any

from .changeset import list_changesets
from .failure_probe import build_failure_probe_candidates
from .failure_taxonomy import (
    classify_implementation_failure,
    classify_invalid_changeset_review_bucket,
    classify_workflow_failure,
    describe_taxonomy,
    validation_messages,
)
from .integrity import run_checks
from .schema_registry import build_schema_registry
from .self_iteration_metrics import build_self_iteration_reliability_metrics
from .smoke_fixtures import build_smoke_fixture_manifest

from .owner import list_owner_items

from .workflow import list_workflows, state_display_label



def _implementation_pipeline_diagnostics(changesets: list[dict[str, Any]], *, limit: int = 10) -> dict[str, Any]:
    invalid_changesets = [
        item for item in changesets
        if item.get("status") == "invalid" or str(item.get("id", "")).startswith("chg_invalid")
    ]
    invalid_changesets = sorted(
        invalid_changesets,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )

    failure_counts: dict[str, int] = {}
    review_bucket_counts: dict[str, int] = {}
    recent: list[dict[str, Any]] = []
    for item in invalid_changesets:
        messages = validation_messages(item)
        categories = sorted({classify_implementation_failure(message) for message in messages}) or ["unknown"]
        review_bucket = classify_invalid_changeset_review_bucket(categories, messages)
        for category in categories:
            failure_counts[category] = failure_counts.get(category, 0) + 1
        review_bucket_counts[review_bucket] = review_bucket_counts.get(review_bucket, 0) + 1
        if len(recent) < limit:
            recent.append({
                "id": item.get("id"),
                "roadmap_id": item.get("roadmap_id"),
                "summary": item.get("summary"),
                "review_bucket": review_bucket,
                "categories": categories,
                "validation_messages": messages,
                "parse_diagnostics": item.get("parse_diagnostics"),
                "agent_run_id": item.get("agent_run_id"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })

    return {
        "invalid_changeset_review_bucket_counts": review_bucket_counts,
        "invalid_changeset_failure_counts": failure_counts,
        "recent_invalid_changesets": recent,
    }


def _workflow_failure_diagnostics(workflows: list[dict[str, Any]], *, limit: int = 10) -> dict[str, Any]:
    """Classify recent actionable workflow issues into pipeline failure categories.


    Excludes terminal non-action items that are summarized elsewhere:
    - satisfied_without_changes
    - owner_rejected
    - superseded_failure

    Categories reported:
    - context_insufficient
    - task_type_misclassification
    - edit_plan_parse_error
    - symbol_anchor_resolution_failure
    - old_content_match_failure
    - harness_violation
    - provider_empty_or_timeout
    - expected_governance_block
    - other
    """
    non_actionable_outcomes = {
        "satisfied_without_changes",
        "owner_rejected",
        "superseded_failure",
        "implementation_pipeline_issue",
        "expected_governance_block",
    }
    failed_workflows = [

        wf for wf in workflows
        if wf.get("status") in {"failed", "blocked", "rejected"}
        and _classify_workflow_outcome(wf) not in non_actionable_outcomes
    ]

    failed_workflows = sorted(

        failed_workflows,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )

    failure_counts: dict[str, int] = {}
    recent: list[dict[str, Any]] = []
    for wf in failed_workflows:
        categories = classify_workflow_failure(wf)
        for category in categories:
            failure_counts[category] = failure_counts.get(category, 0) + 1
        if len(recent) < limit:
            recent.append({
                "id": wf.get("id"),
                "roadmap_id": wf.get("roadmap_id"),
                "status": wf.get("status"),
                "categories": categories,
                "last_error": (wf.get("last_error") or "")[:200],
                "updated_at": wf.get("updated_at"),
            })

    return {
        "workflow_failure_counts": failure_counts,
        "recent_failed_workflows": recent,
    }


def _workflow_expected_governance_diagnostics(workflows: list[dict[str, Any]], *, limit: int = 10) -> dict[str, Any]:
    """Summarize expected governance blocks separately from failures."""
    governance_workflows = [
        wf for wf in workflows
        if _classify_workflow_outcome(wf) == "expected_governance_block"
    ]
    governance_workflows = sorted(
        governance_workflows,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    recent = [
        {
            "id": wf.get("id"),
            "roadmap_id": wf.get("roadmap_id"),
            "status": wf.get("status"),
            "last_error": (wf.get("last_error") or "")[:200],
            "last_event": _extract_last_event(wf),
            "updated_at": wf.get("updated_at"),
        }
        for wf in governance_workflows[:limit]
    ]
    return {
        "count": len(governance_workflows),
        "meaning": "Expected governance blocks are deliberate Owner/governance boundary stops, not active execution failures.",
        "recent_expected_governance_blocks": recent,
    }


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
        last_error = workflow.get("last_error", "")
        history = workflow.get("history", [])
        last_event = history[-1] if history else {}
        details = last_event.get("details") or {}
        if details.get("category") == "already_satisfied" or "blocked: [already_satisfied]" in last_error:
            return "satisfied_without_changes"
        failure_categories = classify_workflow_failure(workflow)
        if "repeated_placeholder_output" in failure_categories:
            return "implementation_pipeline_issue"
        if "context_request" in last_error and any(marker in last_error.lower() for marker in ("malformed", "placeholder", "edit-plan")):
            return "implementation_pipeline_issue"
        if "repeated_placeholder_format_feedback" in last_error:
            return "context_insufficient"
        if "context_request" in last_error:
            return "context_insufficient"
        # Check if this is a governance_constraint block
        if last_event.get("event") == "implementation_blocked" and details.get("category") == "governance_constraint":

            return "expected_governance_block"
        return "true_blocked"

    if status == "failed":
        # Check if this failure has been explicitly superseded
        if workflow.get("superseded_by_workflow_id") or workflow.get("superseded_by_roadmap_id"):
            return "superseded_failure"
        last_error = workflow.get("last_error", "")
        failure_categories = classify_workflow_failure(workflow)
        # Check if failure is due to context insufficiency vs actual implementation failure
        if "context_request" in last_error:
            return "context_insufficient"
        if failure_categories == ["provider_empty_or_timeout"]:
            return "provider_empty_or_timeout"
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
    provider_empty_or_timeout = [item["workflow"] for item in classified_workflows if item["outcome"] == "provider_empty_or_timeout"]
    implementation_pipeline_issues = [item["workflow"] for item in classified_workflows if item["outcome"] == "implementation_pipeline_issue"]
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
        "provider_empty_or_timeout": len(provider_empty_or_timeout),
        "implementation_pipeline_issues": len(implementation_pipeline_issues),
        "superseded_failures": len(superseded_failures),
        "superseded_by_corrected_changeset": len(superseded_by_corrected),

        "invalid_changesets": len([item for item in changesets if item.get("status") == "invalid"]),

        "recent_completed_workflows": len(recent_completed),
    }

    state_semantics: dict[str, Any] = {
        "active_health_gates": [
            "active_workflows",
            "pending_owner_items",
            "true_failures",
            "true_blocked",
        ],
        "historical_or_expected_buckets": [
            "expected_governance_blocks",
            "provider_empty_or_timeout",
            "implementation_pipeline_issues",
            "superseded_failures",
            "superseded_by_corrected_changeset",

            "satisfied_without_changes",
            "context_insufficient",
            "owner_rejected",
        ],

        "review_input_buckets": [
            "invalid_changesets",
            "implementation_pipeline_diagnostics",
            "workflow_failure_diagnostics",
            "workflow_expected_governance_diagnostics",
        ],
        "notes": {
            "active_health_gates": "Non-zero values here require current operator attention before continuing normal work.",
            "historical_or_expected_buckets": "These buckets may describe legitimate terminal outcomes, expected governance blocks, or resolved historical failures rather than active health failures.",
            "review_input_buckets": "These buckets preserve historical evidence for structural review and stability work.",
            "workflow_expected_governance_diagnostics": "Expected governance blocks indicate the governance boundary is working as designed; they are not active execution failures.",
        },
    }


    summary: dict[str, Any] = {
        "schema": "abyss.summary.v1",
        "operations_health_counts": operations_health_counts,
        "state_semantics": state_semantics,
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
            "provider_empty_or_timeout": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "last_event": _extract_last_event(item),
                }
                for item in provider_empty_or_timeout
            ],
            "implementation_pipeline_issues": [
                {
                    "id": item.get("id"),
                    "roadmap_id": item.get("roadmap_id"),
                    "status": item.get("status"),
                    "last_error": item.get("last_error"),
                    "last_event": _extract_last_event(item),
                }
                for item in implementation_pipeline_issues
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
        "implementation_pipeline_diagnostics": _implementation_pipeline_diagnostics(changesets),
        "workflow_failure_diagnostics": _workflow_failure_diagnostics(workflows),
        "workflow_expected_governance_diagnostics": _workflow_expected_governance_diagnostics(workflows),
        "failure_taxonomy": describe_taxonomy(),
        "schema_registry": build_schema_registry(),
        "smoke_fixture_manifest": build_smoke_fixture_manifest(),
        "self_iteration_reliability_metrics": build_self_iteration_reliability_metrics(),
        "failure_probe_candidates": build_failure_probe_candidates(limit=10),
    }

    if include_check:

        ok, messages = run_checks()
        summary["integrity"] = {"ok": ok, "messages": messages}
    return summary


def render_summary(*, include_check: bool = False) -> str:
    return json.dumps(build_summary(include_check=include_check), ensure_ascii=False, indent=2)
