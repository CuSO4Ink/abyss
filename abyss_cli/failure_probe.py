from __future__ import annotations

import json
from typing import Any

from .changeset import list_changesets
from .failure_taxonomy import classify_implementation_failure, classify_workflow_failure, probe_kind_from_categories, validation_messages
from .workflow import list_workflows


def build_failure_probe_candidates(*, limit: int = 20) -> dict[str, Any]:
    """Build candidate probe specs from observed failures.

    Candidate probes are inactive review material. This function does not add
    tests to required gates, execute probes, mutate workflows, or approve any
    generated probe.
    """
    candidates: list[dict[str, Any]] = []

    for changeset in sorted(list_changesets(), key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True):
        if len(candidates) >= limit:
            break
        if changeset.get("status") != "invalid" and not str(changeset.get("id") or "").startswith("chg_invalid"):
            continue
        messages = validation_messages(changeset)
        categories = sorted({classify_implementation_failure(message) for message in messages}) or ["other_invalid_changeset"]
        probe_kind = probe_kind_from_categories(categories)
        candidates.append({
            "id": f"probe_candidate_{len(candidates) + 1:03d}",
            "source_type": "changeset",
            "source_id": changeset.get("id"),
            "roadmap_id": changeset.get("roadmap_id"),
            "probe_kind": probe_kind,
            "categories": categories,
            "title": f"Probe {probe_kind} from {changeset.get('id')}",
            "evidence": {
                "summary": changeset.get("summary"),
                "validation_messages": messages[:5],
                "parse_diagnostics": changeset.get("parse_diagnostics"),
                "retry_guidance": changeset.get("retry_guidance"),
            },
            "candidate_probe_spec": {
                "schema": "abyss.failure_probe_candidate.v1",
                "inactive_by_default": True,
                "goal": "Reproduce the observed failure class as a regression signal before claiming reliability improvement.",
                "expected_signal": categories,
                "activation_requires_owner_approval": True,
            },
        })

    for workflow in sorted(list_workflows(), key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True):
        if len(candidates) >= limit:
            break
        if workflow.get("status") not in {"failed", "blocked", "rejected"}:
            continue
        categories = classify_workflow_failure(workflow)
        probe_kind = probe_kind_from_categories(categories)
        candidates.append({
            "id": f"probe_candidate_{len(candidates) + 1:03d}",
            "source_type": "workflow",
            "source_id": workflow.get("id"),
            "roadmap_id": workflow.get("roadmap_id"),
            "probe_kind": probe_kind,
            "categories": categories,
            "title": f"Probe {probe_kind} from {workflow.get('id')}",
            "evidence": {
                "summary": workflow.get("summary"),
                "status": workflow.get("status"),
                "last_error": workflow.get("last_error"),
                "last_event": (workflow.get("history") or [])[-1] if isinstance(workflow.get("history"), list) and workflow.get("history") else None,
            },
            "candidate_probe_spec": {
                "schema": "abyss.failure_probe_candidate.v1",
                "inactive_by_default": True,
                "goal": "Reproduce the observed workflow failure class as a regression signal before claiming reliability improvement.",
                "expected_signal": categories,
                "activation_requires_owner_approval": True,
            },
        })

    return {
        "schema": "abyss.failure_probe_candidates.v1",
        "read_only": True,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "activation_policy": {
            "inactive_by_default": True,
            "requires_explicit_owner_approval_to_become_gate": True,
            "no_probe_executed": True,
        },
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def render_failure_probe_candidates_json(*, limit: int = 20) -> str:
    return json.dumps(build_failure_probe_candidates(limit=limit), ensure_ascii=False, indent=2) + "\n"
