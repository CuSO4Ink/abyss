"""Unit tests for the deterministic edit-plan compiler (patch_compiler)."""

from __future__ import annotations

import json

import abyss_cli.patch_compiler as pc


def _wrap(plan: dict) -> str:
    return "```abyss-edit-plan\n" + json.dumps(plan) + "\n```\n"


def test_no_block_returns_none(mini_repo):
    assert pc.compile_edit_plan_from_agent_output("no fenced block here", agent_run_id="a", result_path=(mini_repo / "r.md")) is None


def test_valid_create_file_compiles_to_changeset(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_ok",
        "roadmap_id": "R1",
        "summary": "s",
        "risk_level": "L2",
        "edits": [
            {
                "id": "op_001",
                "kind": "create_file",
                "target": {"path": "artifacts/drafts/new_file.md"},
                "content": "# hello\n",
            }
        ],
        "checks": ["python -m abyss_cli check"],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs["schema"] == "abyss.change_set.v1"
    ops = cs.get("operations", [])
    assert any(op.get("kind") == "fs.create_file" for op in ops)


def test_unparseable_block_returns_none_for_fallback(mini_repo):
    """An edit-plan block that cannot be parsed returns None so the caller can
    fall back to legacy changeset parsing — this is the real contract."""
    bad = "```abyss-edit-plan\n{not valid json,,}\n```\n"
    cs = pc.compile_edit_plan_from_agent_output(bad, agent_run_id="a", result_path=(mini_repo / "r.md"))
    # Contract: either None (fallback) or an invalid changeset; never a silent
    # success that would execute actions.
    if cs is not None:
        assert cs.get("status") == "invalid"
        assert cs.get("no_action_executed") is True


def test_valid_json_wrong_schema_yields_invalid(mini_repo):
    """A syntactically valid block with the wrong schema must be invalid."""
    plan = {"schema": "wrong.schema", "id": "chg_w", "roadmap_id": "R1", "edits": [
        {"id": "op_1", "kind": "create_file", "target": {"path": "artifacts/drafts/w.md"}, "content": "x\n"}
    ]}
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "invalid"
    assert cs.get("no_action_executed") is True


def test_missing_edits_yields_invalid(mini_repo):
    plan = {"schema": "abyss.edit_plan.v1", "id": "chg_x", "roadmap_id": "R1", "summary": "s"}
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "invalid"


def test_placeholder_content_rejected(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_ph",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "create_file",
                "target": {"path": "artifacts/drafts/ph.md"},
                "content": "# ... existing code ...\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "invalid"


def test_symbol_not_found_yields_invalid_with_recovery(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_sym",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "replace_symbol",
                "target": {"path": "abyss_cli/example.py"},
                "symbol": "does_not_exist_function",
                "symbol_type": "function",
                "new_content": "def does_not_exist_function():\n    return 2\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "invalid"
    assert cs.get("no_action_executed") is True


def test_replace_anchor_accepts_canonical_top_level_anchor(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_anchor_top",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "replace_anchor",
                "target": {"path": "abyss_cli/example.py"},
                "anchor": "    return 1\n",
                "new_content": "    return 2\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "proposed"
    replace_ops = [op for op in cs.get("operations", []) if op.get("kind") == "fs.replace_exact"]
    assert replace_ops[0]["input"]["old_content"] == "    return 1\n"


def test_replace_anchor_accepts_target_anchor_alias(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_anchor_nested",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "replace_anchor",
                "target": {"path": "abyss_cli/example.py", "anchor": "    return 1\n"},
                "new_content": "    return 3\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "proposed"
    replace_ops = [op for op in cs.get("operations", []) if op.get("kind") == "fs.replace_exact"]
    assert replace_ops[0]["input"]["old_content"] == "    return 1\n"


def test_conflicting_top_level_and_target_anchor_is_invalid(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_anchor_conflict",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "replace_anchor",
                "target": {"path": "abyss_cli/example.py", "anchor": "    return 1\n"},
                "anchor": "def sample_function():\n",
                "new_content": "    return 4\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "invalid"
    assert any("CONFLICTING_ANCHOR" in message for message in cs.get("validation_errors", []))


def test_append_after_anchor_accepts_target_anchor_alias(mini_repo):
    plan = {
        "schema": "abyss.edit_plan.v1",
        "id": "chg_anchor_append_nested",
        "roadmap_id": "R1",
        "summary": "s",
        "edits": [
            {
                "id": "op_001",
                "kind": "append_after_anchor",
                "target": {"path": "abyss_cli/example.py", "anchor": "    return 1\n"},
                "content": "# appended\n",
            }
        ],
    }
    cs = pc.compile_edit_plan_from_agent_output(_wrap(plan), agent_run_id="a", result_path=(mini_repo / "r.md"))
    assert cs is not None
    assert cs.get("status") == "proposed"
    replace_ops = [op for op in cs.get("operations", []) if op.get("kind") == "fs.replace_exact"]
    assert replace_ops[0]["input"]["new_content"] == "    return 1\n# appended\n"


def test_preflight_reject_placeholder_edits_detects_markers():
    edits = [{"id": "op_1", "kind": "create_file", "content": "TODO: omitted"}]
    msgs = pc.preflight_reject_placeholder_edits(edits)
    assert msgs  # non-empty -> rejected


def test_preflight_validate_edit_plan_contract_flags_missing_fields():
    edits = [{"id": "op_1", "kind": "replace_symbol", "target": {"path": "abyss_cli/example.py"}}]
    msgs = pc.preflight_validate_edit_plan_contract(edits)
    assert any("symbol" in m.lower() or "MISSING" in m for m in msgs)
