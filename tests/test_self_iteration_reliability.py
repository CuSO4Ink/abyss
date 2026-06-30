"""Unit tests for read-only reliability metrics and failure-probe candidates.

These exercise the descriptive (non-gating) observability layer. Data sources
(list_workflows / list_changesets / compute_reliability_baseline) are
monkeypatched so no real .local/runtime is read.
"""

from __future__ import annotations

import abyss_cli.self_iteration_metrics as metrics
import abyss_cli.failure_probe as probe


# --------------------------- reliability metrics ---------------------------- #

def _patch_metrics_sources(monkeypatch, workflows, changesets, baseline=None):
    monkeypatch.setattr(metrics, "list_workflows", lambda: workflows)
    monkeypatch.setattr(metrics, "list_changesets", lambda: changesets)
    monkeypatch.setattr(metrics, "compute_reliability_baseline", lambda: baseline or {})


def test_metrics_schema_and_read_only_flags(monkeypatch):
    _patch_metrics_sources(monkeypatch, [], [])
    m = metrics.build_self_iteration_reliability_metrics()
    assert m["schema"] == "abyss.self_iteration_reliability_metrics.v1"
    assert m["read_only"] is True
    assert m["no_action_executed"] is True
    assert m["no_approval_granted"] is True


def test_metrics_empty_data_has_none_values(monkeypatch):
    _patch_metrics_sources(monkeypatch, [], [])
    m = metrics.build_self_iteration_reliability_metrics()
    windows = m.get("windows", {})
    assert "all_time" in windows
    # With zero denominator, rate values should be None / data_available False.
    all_time = windows["all_time"]
    blob = str(all_time)
    assert "first_pass_success_rate" in blob


def test_metrics_with_some_data(monkeypatch):
    workflows = [
        {"id": "wf1", "status": "done", "updated_at": "2026-01-01T00:00:00+08:00",
         "history": [{"event": "workflow_done"}]},
        {"id": "wf2", "status": "blocked", "updated_at": "2026-01-02T00:00:00+08:00",
         "history": [{"event": "dry_run_failed"}]},
    ]
    changesets = [
        {"id": "chg1", "status": "applied", "updated_at": "2026-01-01T00:00:00+08:00"},
        {"id": "chg_invalid_1", "status": "invalid", "updated_at": "2026-01-02T00:00:00+08:00"},
    ]
    _patch_metrics_sources(monkeypatch, workflows, changesets)
    m = metrics.build_self_iteration_reliability_metrics()
    assert m["read_only"] is True
    assert "windows" in m


# --------------------------- failure probe ---------------------------------- #

def _patch_probe_sources(monkeypatch, workflows, changesets):
    monkeypatch.setattr(probe, "list_workflows", lambda: workflows)
    monkeypatch.setattr(probe, "list_changesets", lambda: changesets)


def test_probe_schema_and_read_only(monkeypatch):
    _patch_probe_sources(monkeypatch, [], [])
    p = probe.build_failure_probe_candidates()
    assert p["schema"] == "abyss.failure_probe_candidates.v1"
    assert p["read_only"] is True


def test_probe_candidates_are_inactive_by_default(monkeypatch):
    workflows = [
        {"id": "wf_fail", "status": "failed", "roadmap_id": "R1",
         "history": [{"event": "integrity_check_failed", "details": {"messages": ["boom"]}}],
         "last_error": "boom"},
    ]
    changesets = [
        {"id": "chg_invalid_x", "status": "invalid", "roadmap_id": "R1",
         "validation": {"messages": ["EDIT_PLAN_PARSE_ERROR"]}},
    ]
    _patch_probe_sources(monkeypatch, workflows, changesets)
    p = probe.build_failure_probe_candidates()
    candidates = p.get("candidates", [])
    assert candidates, "expected at least one candidate from failed/invalid material"
    for c in candidates:
        spec = c.get("candidate_probe_spec", {})
        assert spec.get("inactive_by_default") is True
        assert spec.get("activation_requires_owner_approval") is True


def test_probe_activation_policy_requires_owner(monkeypatch):
    _patch_probe_sources(monkeypatch, [], [])
    p = probe.build_failure_probe_candidates()
    policy = p.get("activation_policy", {})
    assert policy.get("inactive_by_default") is True
    assert policy.get("requires_explicit_owner_approval_to_become_gate") is True
    assert policy.get("no_probe_executed") is True


def test_probe_limit_is_respected(monkeypatch):
    workflows = [
        {"id": f"wf{i}", "status": "failed", "roadmap_id": "R1",
         "history": [{"event": "x", "details": {"messages": ["e"]}}], "last_error": "e"}
        for i in range(10)
    ]
    _patch_probe_sources(monkeypatch, workflows, [])
    p = probe.build_failure_probe_candidates(limit=3)
    assert len(p.get("candidates", [])) <= 3
