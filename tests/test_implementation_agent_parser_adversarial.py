"""Strict adversarial tests for the Implementation Agent output parser.

The Implementation Agent is the single most important "engine" of the
self-iteration flow: the deterministic state machine merely consumes whatever
this parser decides. So the parser's classification logic is exactly where a
misbehaving / lazy / malformed LLM must be defended against.

``_parse_implementation_output`` is the decision core. Its documented priority
is:

    context_request  >  blocked_result  >  edit_plan  >  legacy changeset
                                                        >  unrecognized-fallback

These tests attack that core directly. They do NOT call a real provider; they
feed crafted ``response_text`` straight into the parser and assert the system's
*defensive* behaviour. The real ``compile_edit_plan_from_agent_output`` is used
(not mocked) so the edit-plan path exercises the genuine compiler contract.

All tests run under ``mini_repo`` so every write lands in a temp runtime and the
real ``.local/runtime`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import abyss_cli.agent_runner as runner


def _result_path(mini_repo: Path) -> Path:
    p = mini_repo / ".local" / "runtime" / "process" / "llm_results" / "llm_result_x.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("stub\n", encoding="utf-8")
    return p


def _silence_audit(monkeypatch):
    monkeypatch.setattr(runner, "append_event", lambda *a, **k: None)


# --------------------------------------------------------------------------- #
# 1. Empty / whitespace-only output must be rejected, not silently accepted.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("payload", ["", "   ", "\n\n\t  \n"])
def test_empty_output_returns_none(mini_repo, monkeypatch, payload):
    _silence_audit(monkeypatch)
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_empty", result_path=_result_path(mini_repo)
    )
    assert out is None, "empty/whitespace output must NOT be treated as a valid result"


# --------------------------------------------------------------------------- #
# 2. Non-empty garbage must NOT be dropped: it must become a recoverable
#    format_feedback context_request (so the flow can retry, not stall).
# --------------------------------------------------------------------------- #

def test_unrecognized_nonempty_output_becomes_format_feedback(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    out = runner._parse_implementation_output(
        "I think we should refactor everything. Trust me, it's done now.",
        agent_run_id="ar_garbage",
        result_path=_result_path(mini_repo),
    )
    assert out is not None
    assert out["output_type"] == "context_request"
    assert out["request_kind"] == "format_feedback"
    assert out["recovery_classification"] == "format_feedback"
    # It must be persisted so the workflow can pick it up.
    ctx_dir = mini_repo / ".local" / "runtime" / "process" / "context_requests"
    assert any(ctx_dir.glob("*.yaml"))


def test_prose_claiming_execution_is_not_trusted(mini_repo, monkeypatch):
    """A model that *claims* it already applied changes must not be believed."""
    _silence_audit(monkeypatch)
    out = runner._parse_implementation_output(
        "DONE. I have already edited abyss_cli/example.py and committed it.",
        agent_run_id="ar_claim",
        result_path=_result_path(mini_repo),
    )
    # No action was executed; this is just unrecognized prose -> format feedback.
    assert out["output_type"] == "context_request"
    assert "no_action" not in json.dumps(out).lower() or out["request_kind"] == "format_feedback"


# --------------------------------------------------------------------------- #
# 3. Output-type priority: context_request wins over everything else, even if a
#    (valid-looking) edit-plan is also present in the same response.
# --------------------------------------------------------------------------- #

def test_context_request_takes_priority_over_edit_plan(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-context-request\n"
        '{"schema":"abyss.context_request.v1","missing":[{"file":"abyss_cli/example.py",'
        '"need":"exact body"}],"reason":"need more"}\n'
        "```\n"
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_x","roadmap_id":"R1","summary":"s",'
        '"edits":[{"id":"op1","kind":"create_file","target":{"path":"artifacts/drafts/x.md"},'
        '"new_content":"hello\\n"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_prio", result_path=_result_path(mini_repo)
    )
    assert out["output_type"] == "context_request", (
        "context_request must win over a co-present edit-plan"
    )


def test_blocked_result_takes_priority_over_edit_plan(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-blocked-result\n"
        '{"schema":"abyss.blocked_result.v1","category":"infeasible",'
        '"blocked_reason":"cannot proceed"}\n'
        "```\n"
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_y","roadmap_id":"R1","summary":"s",'
        '"edits":[{"id":"op1","kind":"create_file","target":{"path":"artifacts/drafts/y.md"},'
        '"new_content":"hi\\n"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_blk", result_path=_result_path(mini_repo)
    )
    assert out["output_type"] == "blocked_result"
    assert out["category"] == "infeasible"


# --------------------------------------------------------------------------- #
# 4. THE anti-laziness gate: `already_satisfied` must be REJECTED (SystemExit)
#    when there is relevant recent failure evidence. This stops the agent from
#    falsely claiming the task is done to escape a hard problem.
# --------------------------------------------------------------------------- #

def test_already_satisfied_blocked_when_relevant_failures_exist(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    target_record = {
        "id": "evo_prop_zz",
        "roadmap_entry": "R_HARD",
        "title": "implement feature for R_HARD",
    }
    # Force the "relevant recent failures" detector to say YES.
    monkeypatch.setattr(runner, "_has_relevant_recent_implementation_failures", lambda tr: True)
    payload = (
        "```abyss-blocked-result\n"
        '{"schema":"abyss.blocked_result.v1","category":"already_satisfied",'
        '"blocked_reason":"nothing to do"}\n'
        "```\n"
    )
    with pytest.raises(SystemExit) as exc:
        runner._parse_implementation_output(
            payload,
            agent_run_id="ar_lazy",
            result_path=_result_path(mini_repo),
            target_record=target_record,
        )
    assert "already_satisfied" in str(exc.value)


def test_already_satisfied_allowed_when_no_relevant_failures(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    target_record = {"id": "evo_prop_ok", "roadmap_entry": "R_EASY", "title": "trivial"}
    monkeypatch.setattr(runner, "_has_relevant_recent_implementation_failures", lambda tr: False)
    payload = (
        "```abyss-blocked-result\n"
        '{"schema":"abyss.blocked_result.v1","category":"already_satisfied",'
        '"blocked_reason":"truly nothing to do"}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload,
        agent_run_id="ar_ok",
        result_path=_result_path(mini_repo),
        target_record=target_record,
    )
    assert out["output_type"] == "blocked_result"
    assert out["category"] == "already_satisfied"


# --------------------------------------------------------------------------- #
# 5. A genuinely valid edit-plan compiles to a proposed changeset and executes
#    nothing.
# --------------------------------------------------------------------------- #

def test_valid_edit_plan_compiles_to_proposed_changeset(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_good","roadmap_id":"R1",'
        '"summary":"create draft","edits":[{"id":"op1","kind":"create_file",'
        '"target":{"path":"artifacts/drafts/good.md"},"new_content":"hello world\\n"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_good", result_path=_result_path(mini_repo)
    )
    assert out["output_type"] == "changeset"
    assert out["status"] == "proposed"
    assert out.get("no_action_executed") is True
    # The real file must NOT have been created (compile != apply).
    assert not (mini_repo / "artifacts" / "drafts" / "good.md").exists()


# --------------------------------------------------------------------------- #
# 6. Placeholder content handling.
#
#    These tests enforce that placeholder-like Implementation Agent output is
#    rejected before it can compile into a clean proposed ChangeSet. The marker
#    list intentionally uses precise forms rather than a bare "todo" substring
#    so legitimate identifiers such as todo_list are not rejected.
# --------------------------------------------------------------------------- #

def _compile_create_file_placeholder(mini_repo, monkeypatch, smuggled):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_ph","roadmap_id":"R1","summary":"s",'
        '"edits":[{"id":"op1","kind":"create_file","target":{"path":"artifacts/drafts/ph.md"},'
        '"new_content":"' + smuggled + '"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_ph", result_path=_result_path(mini_repo)
    )
    # Regardless of classification, compile must never touch the real file.
    assert not (mini_repo / "artifacts" / "drafts" / "ph.md").exists()
    return out


@pytest.mark.parametrize("smuggled", ["# ... existing code ...\\n"])
def test_known_placeholder_marker_is_rejected(mini_repo, monkeypatch, smuggled):
    """Markers already in PLACEHOLDER_MARKERS must NOT compile clean."""
    out = _compile_create_file_placeholder(mini_repo, monkeypatch, smuggled)
    if out["output_type"] == "context_request":
        assert out["recovery_classification"] in {"format_feedback", "context_insufficient"}
    else:
        assert out.get("status") == "invalid"


@pytest.mark.parametrize(
    "smuggled",
    [
        "# TODO: fill this in\\n",
        "// other code unchanged\\n",
    ],
)
def test_prompt_forbidden_placeholder_markers_are_rejected(mini_repo, monkeypatch, smuggled):
    """Markers forbidden by prompt/retry guidance must not compile clean."""
    out = _compile_create_file_placeholder(mini_repo, monkeypatch, smuggled)
    if out["output_type"] == "context_request":
        assert out["recovery_classification"] in {"format_feedback", "context_insufficient"}
    else:
        assert out.get("status") == "invalid"


def test_placeholder_marker_detection_does_not_reject_todo_identifier(mini_repo, monkeypatch):
    """The marker list must not use a bare todo substring that rejects identifiers."""
    out = _compile_create_file_placeholder(
        mini_repo,
        monkeypatch,
        "todo_list = []\\nprint(todo_list)\\n",
    )
    assert out["output_type"] == "changeset"
    assert out.get("status") == "proposed"


# --------------------------------------------------------------------------- #
# 7. Malformed JSON inside the edit-plan fence must not crash; it must be
#    classified as a recoverable failure, never a silent success.
# --------------------------------------------------------------------------- #

def test_malformed_edit_plan_json_is_recoverable_not_crash(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_bad", THIS IS NOT JSON ,,,}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_badjson", result_path=_result_path(mini_repo)
    )
    assert out is not None, "malformed JSON must not be silently dropped"
    if out["output_type"] == "context_request":
        assert out["recovery_classification"] in {"format_feedback", "context_insufficient"}
    else:
        assert out.get("status") == "invalid"


# --------------------------------------------------------------------------- #
# 8. An edit-plan targeting a symbol/anchor that does NOT exist must not guess;
#    it must surface a recoverable context_request (target-resolution failure).
# --------------------------------------------------------------------------- #

def test_edit_plan_unresolvable_symbol_is_recoverable(mini_repo, monkeypatch):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_sym","roadmap_id":"R1","summary":"s",'
        '"edits":[{"id":"op1","kind":"replace_symbol",'
        '"target":{"path":"abyss_cli/example.py"},"symbol":"this_symbol_does_not_exist",'
        '"symbol_type":"function","new_content":"def x():\\n    return 2\\n"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_sym", result_path=_result_path(mini_repo)
    )
    assert out is not None
    if out["output_type"] == "context_request":
        # symbol-not-found should be treated as needing more local context.
        assert out["recovery_classification"] in {"context_insufficient", "format_feedback"}
    else:
        assert out.get("status") == "invalid"
    # Real source file must be untouched.
    assert (mini_repo / "abyss_cli" / "example.py").read_text(encoding="utf-8") == (
        "def sample_function():\n    return 1\n"
    )


# --------------------------------------------------------------------------- #
# 9. An edit-plan that tries to write OUTSIDE the allowed roots must never
#    compile into an applyable changeset.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "evil_path",
    ["rules/policy.yaml", "ROADMAP.md", ".git/config", "pyproject.toml", "../escape.txt"],
)
def test_edit_plan_to_forbidden_path_is_invalid(mini_repo, monkeypatch, evil_path):
    _silence_audit(monkeypatch)
    payload = (
        "```abyss-edit-plan\n"
        '{"schema":"abyss.edit_plan.v1","id":"chg_evil","roadmap_id":"R1","summary":"s",'
        '"edits":[{"id":"op1","kind":"create_file","target":{"path":"' + evil_path + '"},'
        '"new_content":"pwned\\n"}]}\n'
        "```\n"
    )
    out = runner._parse_implementation_output(
        payload, agent_run_id="ar_evil", result_path=_result_path(mini_repo)
    )
    assert out is not None
    # Must NOT be a clean proposed changeset.
    if out["output_type"] == "changeset":
        assert out.get("status") == "invalid", f"{evil_path} should never compile clean"
    else:
        assert out["output_type"] == "context_request"
