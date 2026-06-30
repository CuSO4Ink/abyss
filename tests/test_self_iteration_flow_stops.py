"""Map of *every* place the self-iteration workflow can stop, with intent.

The user's core concern: besides the one designed human gate
(``waiting_owner_approval``), does the flow frequently get stuck?

This module enumerates each stop the real ``workflow_tick`` state machine can
produce and asserts:
  * which stops are *designed* gates / guards (acceptable), and
  * that healthy input never trips them.

Each test documents whether the stop is DESIGNED (intended control point) or
would be a DEFECT if it fired on healthy input.
"""

from __future__ import annotations

from typing import Any

import pytest

import abyss_cli.workflow as workflow
import abyss_cli.changeset as changeset


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _seed(status: str = "implementation_pending", **extra: Any) -> dict[str, Any]:
    wf = {
        "schema": "abyss.workflow.v1",
        "id": workflow.new_id("wf"),
        "proposal_id": "p_map",
        "roadmap_id": "R901",
        "summary": "stop-map probe",
        "status": status,
        "provider": "cli",
        "source": "test",
        "attempts": {"implementation": 0, "harness_review": 0, "execution": 0},
        "history": [{"at": workflow.now_iso(), "state": status, "event": "seed"}],
        "created_at": workflow.now_iso(),
        "updated_at": workflow.now_iso(),
    }
    wf.update(extra)
    workflow._write_workflow(wf)
    return wf


def _valid_changeset(cs_id: str, roadmap_id: str) -> dict[str, Any]:
    record = {
        "schema": "abyss.change_set.v1",
        "id": cs_id,
        "roadmap_id": roadmap_id,
        "summary": "ok change",
        "risk_level": "L2",
        "status": "proposed",
        "operations": [
            {
                "id": "op_001",
                "kind": "fs.create_file",
                "target": {"path": "artifacts/drafts/stop_map_artifact.md"},
                "input": {"content": "# stop map\n"},
            }
        ],
        "validation": {"ok": True, "messages": ["OK"]},
    }
    changeset.write_record(changeset._record_path(cs_id), record)
    return record


def _agent_yielding(result_factory):
    def _run(agent_id, target="latest", provider=None):
        return {"id": "ar"}, result_factory()
    return _run


# --------------------------------------------------------------------------- #
# DESIGNED stops — must fire on the corresponding input
# --------------------------------------------------------------------------- #

def test_designed_stop_context_insufficient_blocks(mini_repo, monkeypatch):
    """Agent asking for more context is a DESIGNED block (recoverable)."""
    wf = _seed()

    def result():
        return {
            "schema": "abyss.context_request.v1",
            "output_type": "context_request",
            "id": "ctx_req_1",
            "missing": [{"file": "abyss_cli/example.py", "need": "more"}],
            "reason": "Context insufficient",
            "request_kind": "local_edit_context",
        }

    monkeypatch.setattr(workflow, "run_agent", _agent_yielding(result))
    workflow.workflow_run_until_wait(workflow_id=wf["id"], max_steps=6)
    final = workflow.load_workflow(wf["id"])
    assert final["status"] == "blocked"
    assert final["history"][-1]["event"] == "implementation_context_insufficient"


def test_designed_stop_blocked_result(mini_repo, monkeypatch):
    """Agent declaring the task fundamentally blocked is a DESIGNED block."""
    wf = _seed()

    def result():
        return {
            "schema": "abyss.blocked_result.v1",
            "output_type": "blocked_result",
            "id": "blk_1",
            "category": "governance",
            "blocked_reason": "needs meta-governance",
        }

    monkeypatch.setattr(workflow, "run_agent", _agent_yielding(result))
    workflow.workflow_run_until_wait(workflow_id=wf["id"], max_steps=6)
    final = workflow.load_workflow(wf["id"])
    assert final["status"] == "blocked"
    assert final["history"][-1]["event"] == "implementation_blocked"


def test_designed_stop_harness_violation_blocks(mini_repo, monkeypatch):
    """Harness verdict 'violation' is a DESIGNED safety block before owner."""
    wf = _seed()
    monkeypatch.setattr(
        workflow, "run_agent",
        _agent_yielding(lambda: {**_valid_changeset("chg_v", "R901"), "output_type": "changeset"}),
    )
    monkeypatch.setattr(
        workflow, "run_harness_changeset_review",
        lambda target, provider=None: ({"id": "arh"}, {"id": "hr", "verdict": "violation"}),
    )
    workflow.workflow_run_until_wait(workflow_id=wf["id"], max_steps=8)
    final = workflow.load_workflow(wf["id"])
    assert final["status"] == "blocked"
    assert final["history"][-1]["event"] == "harness_review_violation"


def test_designed_stop_invalid_output_after_retries_blocks(mini_repo, monkeypatch):
    """Repeated invalid/format-error output blocks after the retry budget.

    DESIGNED: the flow retries format errors up to a budget, then blocks rather
    than looping forever — this is the *opposite* of "stuck forever".
    """
    wf = _seed()

    def result():
        cs_id = "chg_invalid_fmt"
        record = {
            "schema": "abyss.change_set.v1",
            "id": cs_id,
            "roadmap_id": "R901",
            "summary": "bad",
            "status": "invalid",
            "operations": [],
            "validation": {"ok": False, "messages": ["EDIT_PLAN_PARSE_ERROR bad json"]},
        }
        changeset.write_record(changeset._record_path(cs_id), record)
        r = dict(record)
        r["output_type"] = "changeset"
        return r

    monkeypatch.setattr(workflow, "run_agent", _agent_yielding(result))
    # Drive enough steps for the retry budget to be exhausted.
    for _ in range(8):
        workflow.workflow_tick(workflow_id=wf["id"])
    final = workflow.load_workflow(wf["id"])
    # It must NOT be perpetually pending; it converges to a terminal-ish state.
    assert final["status"] in {"blocked", "failed"}, final["status"]


# --------------------------------------------------------------------------- #
# Liveness — healthy input must converge, never loop forever
# --------------------------------------------------------------------------- #

def test_liveness_healthy_flow_converges_in_bounded_steps(mini_repo, monkeypatch):
    """Healthy input reaches the owner gate within a small bounded step count.

    This is the direct liveness guarantee: no livelock, no infinite pending.
    """
    wf = _seed()
    monkeypatch.setattr(
        workflow, "run_agent",
        _agent_yielding(lambda: {**_valid_changeset("chg_live", "R901"), "output_type": "changeset"}),
    )
    monkeypatch.setattr(
        workflow, "run_harness_changeset_review",
        lambda target, provider=None: ({"id": "arh"}, {"id": "hr", "verdict": "within_executor_boundary"}),
    )
    results = workflow.workflow_run_until_wait(workflow_id=wf["id"], max_steps=12)
    # Bounded: it stopped because it reached a waiting/terminal state, not the cap.
    assert len(results) <= 12
    final = workflow.load_workflow(wf["id"])
    assert final["status"] == "waiting_owner_approval"


def test_liveness_no_active_workflow_is_idle_not_error(mini_repo):
    """With no active workflow, ticking returns idle (not a crash/stuck)."""
    result = workflow.workflow_tick()
    assert result["status"] == "idle"


def test_transient_provider_error_retries_then_proceeds(mini_repo, monkeypatch):
    """A transient provider error retries rather than dead-ending.

    DESIGNED resilience: first call simulates a timeout, second succeeds.
    """
    wf = _seed()
    state = {"calls": 0}

    def flaky(agent_id, target="latest", provider=None):
        state["calls"] += 1
        if state["calls"] == 1:
            raise RuntimeError("provider request timed out")
        return {"id": "ar"}, {**_valid_changeset("chg_retry", "R901"), "output_type": "changeset"}

    monkeypatch.setattr(workflow, "run_agent", flaky)
    monkeypatch.setattr(
        workflow, "run_harness_changeset_review",
        lambda target, provider=None: ({"id": "arh"}, {"id": "hr", "verdict": "within_executor_boundary"}),
    )
    workflow.workflow_run_until_wait(workflow_id=wf["id"], max_steps=12)
    final = workflow.load_workflow(wf["id"])
    # The transient error must not have dead-ended the flow.
    assert final["status"] == "waiting_owner_approval", (
        f"transient error was not recovered; status={final['status']} "
        f"last_error={final.get('last_error')}"
    )
    assert state["calls"] >= 2
