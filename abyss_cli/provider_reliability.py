"""Abyss Provider Reliability Baseline - read-only diagnostic module.

Reads runtime LLM provider audit events and computes empty-response rates
segmented by prompt-size class (short_health_check vs implementation_load).
Emits a provider_degraded diagnostic when repeated empty/filtered responses
are observed under implementation-load context.

This module is strictly read-only: no credential changes, no automatic model
switching, no network config changes, no governance policy changes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import runtime_root


_SHORT_PROMPT_THRESHOLD = 500
_DEGRADED_THRESHOLD_COUNT = 3
_DEGRADED_THRESHOLD_RATE = 0.5
_MAX_RECENT_EVENTS = 50

_WORKFLOW_EMPTY_RESPONSE_PATTERNS = (
    "knot-cli response field was empty after filtering",
    "empty_stdout",
    "stdout_empty_before_filtering",
    "stdout_empty_after_filtering",
    "provider returned empty stdout",
    "response field is empty or not a string",
    "CLI provider returned empty stdout",
)


def _count_workflow_empty_responses() -> int:
    """Count recent workflow history events matching known empty-response error patterns.

    Scans workflow records and runtime audit for entries that indicate the provider
    returned an empty or filtered response during workflow execution. Only counts
    events from workflows classified as implementation_load (implementation agent runs).
    """
    from .utils import list_records, read_record

    count = 0
    workflows_dir = runtime_root() / "process" / "workflows"
    if not workflows_dir.exists():
        return 0

    workflow_paths = sorted(
        list_records(workflows_dir, "wf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:_MAX_RECENT_EVENTS]

    for path in workflow_paths:
        try:
            wf = read_record(path)
        except Exception:
            continue
        if not isinstance(wf, dict):
            continue
        history = wf.get("history") if isinstance(wf.get("history"), list) else []
        for event in history:
            if not isinstance(event, dict):
                continue
            details = event.get("details") if isinstance(event.get("details"), dict) else {}
            event_text = str(event.get("event") or "") + " " + str(details)
            event_text_lower = event_text.lower()
            for pattern in _WORKFLOW_EMPTY_RESPONSE_PATTERNS:
                if pattern.lower() in event_text_lower:
                    count += 1
                    break
    return count



def _load_audit_events() -> list[dict[str, Any]]:
    """Load recent audit events from the audit log."""
    audit_path = runtime_root() / "audit" / "audit.md"
    if not audit_path.exists():
        return []
    text = audit_path.read_text(encoding="utf-8", errors="replace")
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "llm.provider.retryable_failure" in line or "agent.output.empty" in line:
            events.append({"raw": line, "type": "failure"})
        elif "agent.run.completed" in line:
            events.append({"raw": line, "type": "success"})
    return events[-_MAX_RECENT_EVENTS:]


def _load_llm_result_records() -> list[dict[str, Any]]:
    """Load recent LLM result metadata from runtime process records."""
    results_dir = runtime_root() / "process" / "llm_results"
    if not results_dir.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("llm_result_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:_MAX_RECENT_EVENTS]:
        size = path.stat().st_size
        records.append({
            "path": path.name,
            "size": size,
            "empty": size < 10,
        })
    return records


def _load_agent_run_records() -> list[dict[str, Any]]:
    """Load recent agent run records to classify prompt-size class."""
    agent_runs_dir = runtime_root() / "process" / "agent_runs"
    if not agent_runs_dir.exists():
        return []
    import json
    records: list[dict[str, Any]] = []
    paths = sorted(agent_runs_dir.glob("agent_run_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)[:_MAX_RECENT_EVENTS]
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(text) if text.strip() else {}
        except Exception:
            data = {}
        if isinstance(data, dict):
            records.append(data)
    return records


def _classify_prompt_size(agent_run: dict[str, Any]) -> str:
    """Classify an agent run as short_health_check or implementation_load."""
    agent_id = str(agent_run.get("agent_id") or "")
    if agent_id == "implementation":
        return "implementation_load"
    prompt_path = str(agent_run.get("prompt_package") or "")
    if "health" in prompt_path.lower() or "smoke" in prompt_path.lower():
        return "short_health_check"
    if agent_id in ("harness", "self_evolution"):
        return "implementation_load"
    return "short_health_check"


def _is_empty_or_filtered(agent_run: dict[str, Any]) -> bool:
    """Determine if an agent run produced an empty or filtered response."""
    result_path_str = str(agent_run.get("result_path") or "")
    if not result_path_str:
        return False
    result_path = Path(result_path_str)
    if not result_path.exists():
        return False
    try:
        content = result_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return True
    return len(content) < 10


def compute_reliability_baseline() -> dict[str, Any]:
    """Compute provider reliability baseline segmented by prompt-size class.

    Returns a structured diagnostic report without performing any mutations.
    """
    agent_runs = _load_agent_run_records()

    counts: dict[str, dict[str, int]] = {
        "short_health_check": {"total": 0, "empty": 0, "success": 0},
        "implementation_load": {"total": 0, "empty": 0, "success": 0},
    }

    for run in agent_runs:
        size_class = _classify_prompt_size(run)
        if size_class not in counts:
            counts[size_class] = {"total": 0, "empty": 0, "success": 0}
        counts[size_class]["total"] += 1
        if _is_empty_or_filtered(run):
            counts[size_class]["empty"] += 1
        else:
            counts[size_class]["success"] += 1

    # Include workflow-history empty-response events in implementation_load counts
    workflow_empty_count = _count_workflow_empty_responses()
    counts["implementation_load"]["empty"] += workflow_empty_count
    counts["implementation_load"]["total"] += workflow_empty_count

    impl_counts = counts["implementation_load"]
    impl_total = impl_counts["total"]
    impl_empty = impl_counts["empty"]
    impl_empty_rate = impl_empty / impl_total if impl_total > 0 else 0.0

    short_counts = counts["short_health_check"]
    short_total = short_counts["total"]
    short_empty = short_counts["empty"]
    short_empty_rate = short_empty / short_total if short_total > 0 else 0.0

    provider_degraded = (
        impl_empty >= _DEGRADED_THRESHOLD_COUNT
        and impl_empty_rate >= _DEGRADED_THRESHOLD_RATE
    )

    diagnostic_message = ""
    if provider_degraded:
        diagnostic_message = (
            f"provider_degraded: {impl_empty}/{impl_total} recent implementation-load "
            f"responses were empty/filtered (rate={impl_empty_rate:.0%}). "
            f"Short health-check: {short_empty}/{short_total} empty "
            f"(rate={short_empty_rate:.0%}). "
            f"Provider may pass short prompts while failing on implementation-size context."
        )

    report: dict[str, Any] = {
        "schema": "abyss.provider_reliability_baseline.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workflow_empty_response_events": workflow_empty_count,
        "prompt_size_classes": {
            "short_health_check": {
                "total": short_total,
                "empty_or_filtered": short_empty,
                "success": short_counts["success"],
                "empty_rate": round(short_empty_rate, 3),
            },
            "implementation_load": {
                "total": impl_total,
                "empty_or_filtered": impl_empty,
                "success": impl_counts["success"],
                "empty_rate": round(impl_empty_rate, 3),
            },
        },
        "provider_degraded": provider_degraded,
        "diagnostic_message": diagnostic_message,
        "thresholds": {
            "degraded_count": _DEGRADED_THRESHOLD_COUNT,
            "degraded_rate": _DEGRADED_THRESHOLD_RATE,
            "recent_window": _MAX_RECENT_EVENTS,
        },
        "no_action_executed": True,
    }
    return report


def render_provider_reliability_json() -> str:
    """Render provider reliability baseline as formatted JSON."""
    report = compute_reliability_baseline()
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if report.get("provider_degraded") and report.get("diagnostic_message"):
        output += "\n\n# DIAGNOSTIC: " + report["diagnostic_message"] + "\n"
    return output
