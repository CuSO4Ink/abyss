from __future__ import annotations

import json
import re
from typing import Any

from .summary import build_summary
from .utils import repo_root
from .workflow import list_workflows, state_display_label


ROADMAP_ITEM_RE = re.compile(r"^###\s+(R\d+[A-Z]?)\.\s+(.+?)\s*$")


def _parse_roadmap_items(path: Any) -> list[dict[str, Any]]:
    """Parse roadmap item headings from one Markdown file without mutating it."""
    if not path.exists():
        return []

    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = ROADMAP_ITEM_RE.match(line)
        if not match:
            continue
        items.append({
            "id": match.group(1),
            "title": match.group(2),
            "line": line_number,
            "source": str(path.relative_to(repo_root())),
        })
    return items


def _parse_current_roadmap_items() -> list[dict[str, Any]]:
    """Parse active/current approved roadmap item headings from ROADMAP.md."""
    return _parse_roadmap_items(repo_root() / "ROADMAP.md")


def _parse_archived_roadmap_items() -> list[dict[str, Any]]:
    """Parse archived approved roadmap item headings for count/context only."""
    archive_dir = repo_root() / "docs" / "archive"
    items: list[dict[str, Any]] = []
    for path in sorted(archive_dir.glob("ROADMAP_R*.md")) if archive_dir.exists() else []:
        items.extend(_parse_roadmap_items(path))
    return items


def _workflow_index_by_roadmap() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for workflow in list_workflows():
        roadmap_id = str(workflow.get("roadmap_id") or "")
        if not roadmap_id:
            continue
        index.setdefault(roadmap_id, []).append(workflow)
    for workflows in index.values():
        workflows.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    return index


def _outcome_label(outcome: str, fallback_status: str) -> str:
    labels = {
        "true_failure": "True Failure",
        "true_blocked": "True Blocked",
        "successfully_completed": "Done",
        "provider_empty_or_timeout": "Provider Empty/Timeout",
        "implementation_pipeline_issues": "Implementation Pipeline Issue",
        "expected_governance_blocks": "Expected Governance Block",
        "superseded_failures": "Superseded Failure",
        "superseded_by_corrected_changeset": "Superseded by Corrected ChangeSet",
        "owner_rejected": "Owner Rejected",
        "satisfied_without_changes": "Satisfied Without Changes",
        "context_insufficient": "Context Insufficient",
    }
    return labels.get(outcome, state_display_label(fallback_status))


def _compact_workflow(workflow: dict[str, Any], outcome_by_workflow_id: dict[str, str]) -> dict[str, Any]:
    status = str(workflow.get("status") or "")
    workflow_id = str(workflow.get("id") or "")
    outcome = outcome_by_workflow_id.get(workflow_id, "")
    return {
        "id": workflow.get("id"),
        "roadmap_id": workflow.get("roadmap_id"),
        "proposal_id": workflow.get("proposal_id"),
        "status": status,
        "outcome": outcome or None,
        "status_label": _outcome_label(outcome, status),
        "summary": workflow.get("summary"),
        "changeset_id": workflow.get("changeset_id"),
        "report_id": workflow.get("report_id"),
        "updated_at": workflow.get("updated_at"),
    }


def build_roadmap_current_view(*, recent_limit: int = 10) -> dict[str, Any]:
    """Build a read-only current roadmap view focused on operator attention."""
    summary = build_summary(include_check=False)
    health_counts = summary.get("operations_health_counts", {})
    active_gate_names = summary.get("state_semantics", {}).get("active_health_gates", [])
    active_gates = {name: health_counts.get(name, 0) for name in active_gate_names}

    outcome_by_workflow_id: dict[str, str] = {}
    outcome_aliases = {
        "true_failures": "true_failure",
        "true_blocked": "true_blocked",
    }
    for outcome, records in summary.get("workflow_outcomes", {}).items():
        if not isinstance(records, list):
            continue
        label_outcome = outcome_aliases.get(outcome, outcome)
        for record in records:
            workflow_id = str(record.get("id") or record.get("workflow_id") or "")
            if workflow_id:
                outcome_by_workflow_id[workflow_id] = label_outcome

    roadmap_items = _parse_current_roadmap_items()
    archived_roadmap_items = _parse_archived_roadmap_items()
    workflows_by_roadmap = _workflow_index_by_roadmap()
    latest_items = list(reversed(roadmap_items[-recent_limit:]))

    latest_approved_items: list[dict[str, Any]] = []
    for item in latest_items:
        related_workflows = workflows_by_roadmap.get(item["id"], [])
        latest_workflow = related_workflows[0] if related_workflows else None
        latest_approved_items.append({
            "id": item["id"],
            "title": item["title"],
            "roadmap_line": item["line"],
            "latest_workflow": _compact_workflow(latest_workflow, outcome_by_workflow_id) if latest_workflow else None,
            "workflow_count": len(related_workflows),
        })

    current_attention = {
        "active_workflows": summary.get("active_workflows", []),
        "pending_owner_items": summary.get("pending_owner_items", []),
        "true_failures": summary.get("workflow_outcomes", {}).get("true_failures", []),
        "true_blocked": summary.get("workflow_outcomes", {}).get("true_blocked", []),
    }

    historical_review_inputs = {
        "expected_governance_blocks": health_counts.get("expected_governance_blocks", 0),
        "provider_empty_or_timeout": health_counts.get("provider_empty_or_timeout", 0),
        "implementation_pipeline_issues": health_counts.get("implementation_pipeline_issues", 0),
        "superseded_failures": health_counts.get("superseded_failures", 0),
        "superseded_by_corrected_changeset": health_counts.get("superseded_by_corrected_changeset", 0),
        "invalid_changesets": health_counts.get("invalid_changesets", 0),
        "invalid_changeset_review_buckets": summary.get("implementation_pipeline_diagnostics", {}).get("invalid_changeset_review_bucket_counts", {}),
        "self_iteration_reliability_metrics": summary.get("self_iteration_reliability_metrics", {}).get("metrics", {}),
        "self_iteration_reliability_windows": sorted((summary.get("self_iteration_reliability_metrics", {}).get("windows") or {}).keys()),
        "failure_probe_candidate_count": summary.get("failure_probe_candidates", {}).get("candidate_count", 0),
        "schema_registry_entry_count": summary.get("schema_registry", {}).get("entry_count", 0),
        "runtime_only_schema_count": (summary.get("schema_registry", {}).get("diagnostics") or {}).get("runtime_only_schema_count", 0),
        "smoke_fixture_count": summary.get("smoke_fixture_manifest", {}).get("fixture_count", 0),
    }

    return {
        "schema": "abyss.roadmap_current.v1",
        "source": "ROADMAP.md, docs/archive/ROADMAP_*.md, plus runtime summary/workflow records",
        "read_only": True,
        "roadmap": {
            "current_item_count": len(roadmap_items),
            "archived_item_count": len(archived_roadmap_items),
            "total_known_item_count": len(roadmap_items) + len(archived_roadmap_items),
            "archive_files": sorted({item["source"] for item in archived_roadmap_items}),
            "latest_approved_items": latest_approved_items,
        },
        "operations_current": {
            "active_health_gates": active_gates,
            "needs_operator_attention": any(int(value or 0) > 0 for value in active_gates.values()),
            "current_attention": current_attention,
            "recent_completed_workflows": summary.get("recent_completed_workflows", []),
        },
        "historical_review_inputs": historical_review_inputs,
        "recommended_next_safe_action": _recommended_next_safe_action(active_gates, historical_review_inputs),
    }


def _recommended_next_safe_action(active_gates: dict[str, Any], historical_review_inputs: dict[str, Any]) -> str:
    if any(int(value or 0) > 0 for value in active_gates.values()):
        return "Resolve non-zero active health gates before starting new roadmap work."
    if int(historical_review_inputs.get("invalid_changesets") or 0) > 0:
        return "Use the current view for orientation; treat invalid changesets as historical review input, not active roadmap work."
    return "No active roadmap blockage is visible; choose the next explicitly approved roadmap item before implementation."


def render_roadmap_current_json() -> str:
    return json.dumps(build_roadmap_current_view(), ensure_ascii=False, indent=2)


def render_roadmap_current_text() -> str:
    view = build_roadmap_current_view()
    lines = [
        "Abyss roadmap current view",
        f"read_only={view['read_only']}",
        f"current_items={view['roadmap']['current_item_count']}",
        f"archived_items={view['roadmap']['archived_item_count']}",
        f"total_known_items={view['roadmap']['total_known_item_count']}",
        "",
        "Active health gates:",
    ]
    for name, value in view["operations_current"]["active_health_gates"].items():
        lines.append(f"- {name}: {value}")
    lines.extend([
        "",
        "Historical/review inputs:",
    ])
    for name, value in view["historical_review_inputs"].items():
        lines.append(f"- {name}: {value}")
    lines.extend([
        "",
        "Latest approved roadmap items:",
    ])
    for item in view["roadmap"]["latest_approved_items"]:
        workflow = item.get("latest_workflow") or {}
        status = workflow.get("status_label") or "no_workflow"
        lines.append(f"- {item['id']} [{status}] {item['title']}")
    lines.extend([
        "",
        f"Recommended next safe action: {view['recommended_next_safe_action']}",
    ])
    return "\n".join(lines)
