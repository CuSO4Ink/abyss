"""Abyss Insight v0 - read-only snapshot command.

Provides a compact abyss.insight_snapshot.v1 JSON view wrapping existing
summary data for operator review. Performs no mutations, LLM calls,
scheduling, or Git operations.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .summary import build_summary


def build_insight_snapshot() -> dict[str, Any]:
    """Build a read-only insight snapshot from existing summary data."""
    summary = build_summary(include_check=True)

    health = summary.get("operations_health_counts", {})
    state_semantics = summary.get("state_semantics", {})
    active_workflows = summary.get("active_workflows", [])
    pending_owner_items = summary.get("pending_owner_items", [])
    workflow_outcomes = summary.get("workflow_outcomes", {})
    true_failures = workflow_outcomes.get("true_failures", [])
    true_blocked = workflow_outcomes.get("true_blocked", [])

    # Historical review inputs
    invalid_changesets_section = summary.get("implementation_pipeline_diagnostics", {})
    workflow_failure_section = summary.get("workflow_failure_diagnostics", {})
    historical_review_inputs = {
        "invalid_changesets": invalid_changesets_section.get("invalid_changeset_failure_counts", {}),
        "diagnostics": workflow_failure_section.get("workflow_failure_counts", {}),
    }

    # Determine recommended next safe action based on current state
    recommended = _recommend_next_safe_action(health, pending_owner_items, active_workflows)

    snapshot: dict[str, Any] = {
        "schema": "abyss.insight_snapshot.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "health": health,
        "state_semantics": state_semantics,
        "active_workflows": [
            {
                "id": wf.get("id"),
                "roadmap_id": wf.get("roadmap_id"),
                "status": wf.get("status"),
                "summary": wf.get("summary"),
            }
            for wf in active_workflows
        ],
        "pending_owner_items": [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "title": item.get("title"),
            }
            for item in pending_owner_items
        ],
        "true_failures": [
            {
                "id": f.get("id"),
                "roadmap_id": f.get("roadmap_id"),
                "last_error": (f.get("last_error") or "")[:200],
            }
            for f in true_failures
        ],
        "true_blocked": [
            {
                "id": b.get("id"),
                "roadmap_id": b.get("roadmap_id"),
                "last_error": (b.get("last_error") or "")[:200],
            }
            for b in true_blocked
        ],
        "historical_review_inputs": historical_review_inputs,
        "recommended_next_safe_action": recommended,
    }

    # Include integrity if available
    integrity = summary.get("integrity")
    if integrity is not None:
        snapshot["integrity"] = integrity

    return snapshot


def _recommend_next_safe_action(
    health: dict[str, int],
    pending_owner_items: list[dict[str, Any]],
    active_workflows: list[dict[str, Any]],
) -> str:
    """Return a static heuristic recommendation string.

    This is purely informational and does not make decisions or trigger actions.
    """
    if health.get("pending_owner_items", 0) > 0:
        return "Review and resolve pending owner inbox items before starting new work."
    if health.get("true_failures", 0) > 0:
        return "Investigate true workflow failures; consider retry or supersede."
    if health.get("true_blocked", 0) > 0:
        return "Review blocked workflows for actionable context requests or governance issues."
    if health.get("active_workflows", 0) > 0:
        return "Active workflows in progress; monitor or tick to advance."
    return "System is idle; safe to start new evolution requests or workflow runs."


def render_insight_snapshot_json() -> str:
    """Render the insight snapshot as formatted JSON string."""
    return json.dumps(build_insight_snapshot(), ensure_ascii=False, indent=2)
