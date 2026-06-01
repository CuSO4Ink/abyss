from __future__ import annotations

import json
from typing import Any

from .changeset import list_changesets
from .provider_reliability import compute_reliability_baseline
from .workflow import list_workflows


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 4) if denominator else None,
        "data_available": denominator > 0,
    }


def _history_contains(workflow: dict[str, Any], markers: tuple[str, ...]) -> bool:
    history = workflow.get("history") if isinstance(workflow.get("history"), list) else []
    combined = json.dumps(history, ensure_ascii=False).lower() + " " + str(workflow.get("last_error") or "").lower()
    return any(marker.lower() in combined for marker in markers)


def _is_success(workflow: dict[str, Any]) -> bool:
    status = str(workflow.get("status") or "")
    return status in {"done", "completed", "reported", "success", "closed"} or bool(workflow.get("report_id"))


def _record_time(item: dict[str, Any]) -> str:
    return str(item.get("updated_at") or item.get("created_at") or "")


def _build_metric_window(
    workflows: list[dict[str, Any]],
    changesets: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_total = len(workflows)
    successful_workflows = [workflow for workflow in workflows if _is_success(workflow)]
    first_pass_successes = [
        workflow for workflow in successful_workflows
        if not _history_contains(workflow, ("retry", "invalid_changeset", "implementation_agent_produced_invalid_changeset", "provider returned empty", "timeout"))
    ]

    invalid_changesets = [
        changeset for changeset in changesets
        if changeset.get("status") == "invalid" or str(changeset.get("id") or "").startswith("chg_invalid")
    ]

    provider_empty_workflows = [
        workflow for workflow in workflows
        if _history_contains(workflow, ("provider returned empty", "empty filtered response", "response field was empty after filtering", "timeout", "timed out"))
    ]

    manual_correction_changesets = [
        changeset for changeset in changesets
        if str(changeset.get("source") or "").startswith("manual")
        or str(changeset.get("generated_by") or "") in {"manual", "manual_correction"}
        or bool(changeset.get("manual_correction"))
    ]

    recovery_records = [
        changeset for changeset in changesets
        if isinstance(changeset.get("context_recovery"), dict)
        or isinstance(changeset.get("context_recovery_packet"), dict)
        or changeset.get("recovery_classification") == "context_insufficient"
    ]
    successful_recoveries = [
        changeset for changeset in recovery_records
        if (changeset.get("context_recovery") or {}).get("success") is True
        or (changeset.get("context_recovery_packet") or {}).get("status") == "resolved"
    ]

    return {
        "metrics": {
            "first_pass_success_rate": _rate(len(first_pass_successes), workflow_total),
            "invalid_changeset_rate": _rate(len(invalid_changesets), len(changesets)),
            "provider_empty_rate": _rate(len(provider_empty_workflows), workflow_total),
            "manual_correction_rate": _rate(len(manual_correction_changesets), len(changesets)),
            "context_recovery_success_rate": _rate(len(successful_recoveries), len(recovery_records)),
        },
        "counts": {
            "workflows_total": workflow_total,
            "workflows_successful": len(successful_workflows),
            "workflows_first_pass_successful": len(first_pass_successes),
            "changesets_total": len(changesets),
            "changesets_invalid": len(invalid_changesets),
            "provider_empty_or_timeout_workflows": len(provider_empty_workflows),
            "manual_correction_changesets": len(manual_correction_changesets),
            "context_recovery_records": len(recovery_records),
            "context_recovery_successful": len(successful_recoveries),
        },
    }


def build_self_iteration_reliability_metrics() -> dict[str, Any]:
    """Build read-only reliability metrics for the self-iteration pipeline.

    The metrics are descriptive only. They do not create gates, approve work,
    retry providers, mutate workflows, or infer missing data as success.
    """
    workflows = list_workflows()
    changesets = list_changesets()
    provider_baseline = compute_reliability_baseline()

    all_time = _build_metric_window(workflows, changesets)
    workflows_recent = sorted(workflows, key=_record_time, reverse=True)
    changesets_recent = sorted(changesets, key=_record_time, reverse=True)
    windows = {
        "all_time": {"scope": "all_records", **all_time},
        "recent_20": {"scope": "latest_records", "workflow_limit": 20, "changeset_limit": 20, **_build_metric_window(workflows_recent[:20], changesets_recent[:20])},
        "recent_50": {"scope": "latest_records", "workflow_limit": 50, "changeset_limit": 50, **_build_metric_window(workflows_recent[:50], changesets_recent[:50])},
    }

    prompt_classes = provider_baseline.get("prompt_size_classes", {}) if isinstance(provider_baseline, dict) else {}
    implementation_load = prompt_classes.get("implementation_load", {}) if isinstance(prompt_classes, dict) else {}

    return {
        "schema": "abyss.self_iteration_reliability_metrics.v1",
        "read_only": True,
        "metrics": all_time["metrics"],
        "counts": all_time["counts"],
        "windows": windows,
        "provider_reliability_reference": {
            "provider_degraded": provider_baseline.get("provider_degraded") if isinstance(provider_baseline, dict) else None,
            "implementation_load_empty_or_timeout": implementation_load.get("empty_or_timeout") if isinstance(implementation_load, dict) else None,
            "implementation_load_total": implementation_load.get("total") if isinstance(implementation_load, dict) else None,
        },
        "notes": [
            "Metrics are descriptive read-only observations, not approval gates.",
            "Null metric values mean the denominator is zero or the required record class has not been observed yet.",
            "manual_correction_rate is based on explicit manual markers only and may undercount older records.",
            "Windowed metrics are descriptive trend hints; they are not gates and may be noisy for small denominators.",
        ],
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def render_self_iteration_reliability_metrics_json() -> str:
    return json.dumps(build_self_iteration_reliability_metrics(), ensure_ascii=False, indent=2) + "\n"