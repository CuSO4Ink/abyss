"""Unit tests for ChangeSet validation and execution boundaries."""

from __future__ import annotations

import abyss_cli.changeset as cs


def _record(**over):
    base = {
        "schema": cs.SUPPORTED_SCHEMA,
        "id": "chg_t",
        "roadmap_id": "R1",
        "operations": [
            {"id": "op_1", "kind": "fs.create_file",
             "target": {"path": "artifacts/drafts/x.md"}, "input": {"content": "x\n"}}
        ],
    }
    base.update(over)
    return base


def test_valid_changeset_passes():
    ok, msgs = cs.validate_changeset(_record(), for_apply=False)
    assert ok, msgs


def test_invalid_schema_fails():
    ok, msgs = cs.validate_changeset(_record(schema="nope"))
    assert not ok
    assert any("INVALID_SCHEMA" in m for m in msgs)


def test_missing_id_fails():
    rec = _record()
    rec.pop("id")
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("MISSING_ID" in m for m in msgs)


def test_missing_roadmap_id_fails():
    rec = _record()
    rec.pop("roadmap_id")
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("MISSING_ROADMAP_ID" in m for m in msgs)


def test_missing_operations_fails():
    ok, msgs = cs.validate_changeset(_record(operations=[]))
    assert not ok
    assert any("MISSING_OPERATIONS" in m for m in msgs)


def test_unsupported_operation_kind_fails():
    rec = _record(operations=[{"id": "op", "kind": "fs.delete_everything", "target": {"path": "x"}}])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("UNSUPPORTED_OPERATION" in m for m in msgs)


def test_disallowed_path_fails():
    rec = _record(operations=[
        {"id": "op", "kind": "fs.create_file", "target": {"path": "rules/policy.yaml"}, "input": {"content": "x"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("PATH_NOT_ALLOWED" in m for m in msgs)


def test_blocked_path_constitution_fails():
    rec = _record(operations=[
        {"id": "op", "kind": "fs.create_file", "target": {"path": "ABYSS_CONSTITUTION.md"}, "input": {"content": "x"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("PATH_NOT_ALLOWED" in m for m in msgs)


def test_disallowed_command_fails():
    rec = _record(operations=[
        {"id": "op", "kind": "check.command", "input": {"command": "rm -rf /"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("COMMAND_NOT_ALLOWED" in m for m in msgs)


def test_allowed_command_passes():
    rec = _record(operations=[
        {"id": "op", "kind": "check.command", "input": {"command": "python -m abyss_cli check"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert ok, msgs


def test_replace_exact_noop_fails():
    rec = _record(operations=[
        {"id": "op", "kind": "fs.replace_exact", "target": {"path": "abyss_cli/example.py"},
         "input": {"old_content": "same", "new_content": "same"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("NOOP_REPLACE" in m for m in msgs)


def test_replace_exact_missing_old_content_fails():
    rec = _record(operations=[
        {"id": "op", "kind": "fs.replace_exact", "target": {"path": "abyss_cli/example.py"},
         "input": {"old_content": "", "new_content": "y"}}
    ])
    ok, msgs = cs.validate_changeset(rec)
    assert not ok
    assert any("MISSING_OLD_CONTENT" in m for m in msgs)


def test_dry_run_is_read_only_and_no_action(mini_repo):
    rec = _record(id="chg_dry")
    cs.write_record(cs._record_path("chg_dry"), rec)
    report = cs.dry_run_changeset("chg_dry")
    assert report.get("no_action_executed") is True
    # File must NOT have been created by a dry-run.
    assert not (mini_repo / "artifacts" / "drafts" / "x.md").exists()


def test_apply_requires_approved_status(mini_repo):
    rec = _record(id="chg_unappr", status="proposed")
    cs.write_record(cs._record_path("chg_unappr"), rec)
    import pytest
    with pytest.raises(SystemExit):
        cs.apply_changeset("chg_unappr")


def test_apply_approved_valid_changeset_writes_only_in_tmp(mini_repo):
    rec = _record(id="chg_appl", status="approved")
    cs.write_record(cs._record_path("chg_appl"), rec)
    execution = cs.apply_changeset("chg_appl")
    assert execution.get("status") == "succeeded"
    # The created file lives under the *temp* repo, never the real one.
    assert (mini_repo / "artifacts" / "drafts" / "x.md").exists()
