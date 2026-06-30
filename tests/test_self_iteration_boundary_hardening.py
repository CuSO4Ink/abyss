"""Focused hardening tests for self-iteration safety boundaries.

These tests lock down the highest-risk engineering details called out by the
self-iteration review: filesystem isolation, path boundaries, dry-run
read-only behavior, and precise read-only observability counters.
"""

from __future__ import annotations

import pytest

import abyss_cli.changeset as cs
import abyss_cli.failure_taxonomy as ft
import abyss_cli.patch_compiler as pc
import abyss_cli.self_iteration_metrics as metrics


def _changeset_record(*, changeset_id: str = "chg_boundary", status: str = "proposed", operations=None):
    return {
        "schema": cs.SUPPORTED_SCHEMA,
        "id": changeset_id,
        "roadmap_id": "R_BOUNDARY",
        "summary": "boundary test changeset",
        "risk_level": "L2",
        "status": status,
        "operations": operations or [],
    }


def test_parent_traversal_path_is_rejected_without_crashing():
    record = _changeset_record(operations=[
        {
            "id": "op_escape",
            "kind": "fs.create_file",
            "target": {"path": "abyss_cli/../artifacts/drafts/escaped.md"},
            "input": {"content": "escape attempt\n"},
        }
    ])

    ok, messages = cs.validate_changeset(record, for_apply=True)

    assert ok is False
    assert any("PATH_NOT_ALLOWED" in message for message in messages)


def test_backslash_blocked_path_is_normalized_and_rejected():
    record = _changeset_record(operations=[
        {
            "id": "op_rules",
            "kind": "fs.create_file",
            "target": {"path": "rules\\policy.yaml"},
            "input": {"content": "blocked\n"},
        }
    ])

    ok, messages = cs.validate_changeset(record, for_apply=True)

    assert ok is False
    assert any("PATH_NOT_ALLOWED" in message and "rules/policy.yaml" in message for message in messages)


def test_dry_run_with_parent_traversal_reports_failure_not_exception(mini_repo):
    record = _changeset_record(
        changeset_id="chg_dry_escape",
        operations=[
            {
                "id": "op_escape",
                "kind": "fs.create_file",
                "target": {"path": "abyss_cli/../artifacts/drafts/escaped.md"},
                "input": {"content": "escape attempt\n"},
            }
        ],
    )
    cs.write_record(cs._record_path("chg_dry_escape"), record)

    report = cs.dry_run_changeset("chg_dry_escape")

    assert report["ok"] is False
    assert report["no_action_executed"] is True
    assert report["preflight"]["ok"] is False
    assert any(item.get("message") == "PATH_NOT_ALLOWED" for item in report["preflight"]["target_resolution_failures"])
    assert not (mini_repo / "artifacts" / "drafts" / "escaped.md").exists()


def test_dry_run_replace_exact_does_not_mutate_existing_file(mini_repo):
    target = mini_repo / "abyss_cli" / "example.py"
    before = target.read_text(encoding="utf-8")
    record = _changeset_record(
        changeset_id="chg_dry_replace",
        status="proposed",
        operations=[
            {
                "id": "op_replace",
                "kind": "fs.replace_exact",
                "target": {"path": "abyss_cli/example.py"},
                "input": {"old_content": "return 1", "new_content": "return 2"},
            }
        ],
    )
    cs.write_record(cs._record_path("chg_dry_replace"), record)

    report = cs.dry_run_changeset("chg_dry_replace")

    assert report["ok"] is True
    assert report["no_action_executed"] is True
    assert target.read_text(encoding="utf-8") == before


def test_apply_validation_failure_does_not_partially_mutate(mini_repo):
    create_target = mini_repo / "artifacts" / "drafts" / "partial.md"
    existing = mini_repo / "abyss_cli" / "example.py"
    before_existing = existing.read_text(encoding="utf-8")
    record = _changeset_record(
        changeset_id="chg_apply_invalid",
        status="approved",
        operations=[
            {
                "id": "op_create",
                "kind": "fs.create_file",
                "target": {"path": "artifacts/drafts/partial.md"},
                "input": {"content": "should not be written\n"},
            },
            {
                "id": "op_bad_replace",
                "kind": "fs.replace_exact",
                "target": {"path": "abyss_cli/example.py"},
                "input": {"old_content": "not present", "new_content": "changed"},
            },
        ],
    )
    cs.write_record(cs._record_path("chg_apply_invalid"), record)

    with pytest.raises(SystemExit):
        cs.apply_changeset("chg_apply_invalid")

    assert not create_target.exists()
    assert existing.read_text(encoding="utf-8") == before_existing


def test_compile_anchor_not_unique_generates_recoverable_context_packet(mini_repo):
    duplicate_file = mini_repo / "abyss_cli" / "duplicate_anchor.py"
    duplicate_file.write_text("VALUE = 1\nVALUE = 1\n", encoding="utf-8")
    text = """```abyss-edit-plan
{
  "schema": "abyss.edit_plan.v1",
  "id": "chg_dup_anchor",
  "roadmap_id": "R_BOUNDARY",
  "summary": "duplicate anchor",
  "edits": [
    {
      "id": "op_anchor",
      "kind": "replace_anchor",
      "target": {"path": "abyss_cli/duplicate_anchor.py"},
      "anchor": "VALUE = 1",
      "new_content": "VALUE = 2"
    }
  ]
}
```"""

    record = pc.compile_edit_plan_from_agent_output(text, agent_run_id="agent", result_path=mini_repo / "result.md")

    assert record is not None
    assert record["status"] == "invalid"
    assert record["recoverable"] is True
    assert record["recovery_classification"] == "context_insufficient"
    packet = record["context_recovery_packet"]
    assert packet["schema"] == "abyss.context_recovery_packet.v1"
    assert packet["retry_limit"] == 1
    assert packet["no_action_executed"] is True
    assert packet["no_approval_granted"] is True


def test_failure_taxonomy_review_buckets_for_core_boundary_cases():
    assert ft.classify_invalid_changeset_review_bucket(
        ["policy_boundary_rejected"], ["PATH_NOT_ALLOWED op rules/policy.yaml"]
    ) == "policy_boundary_rejected"
    assert ft.classify_invalid_changeset_review_bucket(
        ["edit_plan_contract_failure"], ["EDIT_PLAN_CONTRACT_MISSING_NEW_CONTENT op"]
    ) == "implementation_output_contract_feedback"
    assert ft.classify_invalid_changeset_review_bucket(
        ["old_content_match_failure"], ["OLD_CONTENT_MATCH_COUNT op count=0"]
    ) == "target_resolution_feedback"
    assert ft.classify_invalid_changeset_review_bucket(
        ["provider_empty_or_timeout"], ["provider returned empty"]
    ) == "pipeline_runtime_feedback"


def test_metrics_precise_rates_and_recent_window_order(monkeypatch):
    workflows = [
        {"id": "wf_old_success", "status": "done", "updated_at": "2026-01-01T00:00:00+08:00", "history": []},
        {"id": "wf_retry_success", "status": "done", "updated_at": "2026-01-02T00:00:00+08:00", "history": [{"event": "retry"}]},
        {"id": "wf_timeout", "status": "failed", "updated_at": "2026-01-03T00:00:00+08:00", "last_error": "provider returned empty"},
    ]
    changesets = [
        {"id": "chg_ok", "status": "applied", "updated_at": "2026-01-01T00:00:00+08:00"},
        {"id": "chg_invalid_a", "status": "invalid", "updated_at": "2026-01-03T00:00:00+08:00"},
        {"id": "chg_manual", "status": "applied", "updated_at": "2026-01-02T00:00:00+08:00", "generated_by": "manual"},
        {
            "id": "chg_recovered",
            "status": "applied",
            "updated_at": "2026-01-04T00:00:00+08:00",
            "context_recovery_packet": {"status": "resolved"},
        },
    ]
    monkeypatch.setattr(metrics, "list_workflows", lambda: workflows)
    monkeypatch.setattr(metrics, "list_changesets", lambda: changesets)
    monkeypatch.setattr(metrics, "compute_reliability_baseline", lambda: {"prompt_size_classes": {"implementation_load": {"empty_or_timeout": 1, "total": 3}}})

    result = metrics.build_self_iteration_reliability_metrics()

    assert result["metrics"]["first_pass_success_rate"] == {"numerator": 1, "denominator": 3, "value": 0.3333, "data_available": True}
    assert result["metrics"]["invalid_changeset_rate"] == {"numerator": 1, "denominator": 4, "value": 0.25, "data_available": True}
    assert result["metrics"]["provider_empty_rate"] == {"numerator": 1, "denominator": 3, "value": 0.3333, "data_available": True}
    assert result["metrics"]["manual_correction_rate"] == {"numerator": 1, "denominator": 4, "value": 0.25, "data_available": True}
    assert result["metrics"]["context_recovery_success_rate"] == {"numerator": 1, "denominator": 1, "value": 1.0, "data_available": True}
    assert result["windows"]["recent_20"]["counts"]["workflows_total"] == 3
    assert result["provider_reliability_reference"]["implementation_load_empty_or_timeout"] == 1
    assert result["provider_reliability_reference"]["implementation_load_total"] == 3


# --------------------------------------------------------------------------- #
# Path-boundary blind spots surfaced during the boundary re-review.
# The path allow/deny logic uses *string prefixes* while the actual write uses
# pathlib joining. These tests pin down that the two interpretations stay
# consistent and that OS-specific quirks (Windows case-insensitivity, trailing
# dots/spaces, dot/double-slash segments) cannot escape the allow-list.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "raw_path",
    [
        "C:/Windows/system32/evil.txt",   # absolute drive path
        "C:\\Windows\\evil.txt",          # backslash absolute drive path
        "/etc/passwd",                     # posix absolute
        "abyss_cli/../ROADMAP.md",        # parent traversal to blocked file
        "abyss_cli/a/../../ROADMAP.md",   # nested traversal
        "artifacts/drafts/../../ABYSS_CONSTITUTION.md",  # traversal to blocked
        "ROADMAP.MD",                      # case variant of blocked file
        "Rules/policy.yaml",              # case variant of blocked prefix
        "RULES/policy.yaml",
        ".GIT/config",                     # case variant of blocked .git
        "PYPROJECT.TOML",                  # case variant of blocked file
        "artifacts/draftsEVIL/x.md",      # prefix-confusion (not a real subdir)
        "abyss_cli /x.py",                # space-injected dir name
    ],
)
def test_path_boundary_rejects_all_escape_variants(raw_path):
    assert cs._is_allowed_fs_path(raw_path) is False, f"{raw_path!r} should be rejected"


@pytest.mark.parametrize(
    "raw_path",
    [
        "abyss_cli/x.py",
        "abyss_cli/./x.py",     # dot segment, still inside abyss_cli/
        "abyss_cli//x.py",      # double slash, still inside abyss_cli/
        "artifacts/drafts/ok.md",
        "README.md",
        "SYSTEM_MAP.md",
    ],
)
def test_allowed_paths_resolve_strictly_inside_allowed_roots(raw_path):
    """Allow-listed inputs must resolve to a real on-disk location that is
    still *inside* an allowed root (no string/pathlib divergence escape)."""
    assert cs._is_allowed_fs_path(raw_path) is True
    resolved = cs._target_path(raw_path).resolve()
    repo = cs.repo_root().resolve()
    rel = resolved.relative_to(repo).as_posix()  # raises if it escaped repo
    allowed_roots = ("abyss_cli/", "artifacts/drafts/", "README.md", "SYSTEM_MAP.md")
    assert any(rel == r.rstrip("/") or rel.startswith(r) for r in allowed_roots), (
        f"{raw_path!r} resolved to {rel}, outside allowed roots"
    )


def test_string_prefix_and_pathlib_join_agree_for_dot_segments(mini_repo):
    """A dot/double-slash segment that passes the string allow-list must not,
    once written, land outside abyss_cli/ in the temp repo."""
    record = _changeset_record(
        changeset_id="chg_dot_segment",
        status="approved",
        operations=[
            {
                "id": "op_dot",
                "kind": "fs.create_file",
                "target": {"path": "abyss_cli/./nested_ok.py"},
                "input": {"content": "# ok\n"},
            }
        ],
    )
    cs.write_record(cs._record_path("chg_dot_segment"), record)
    cs.apply_changeset("chg_dot_segment")
    # Must have landed strictly inside the temp repo's abyss_cli/, nowhere else.
    assert (mini_repo / "abyss_cli" / "nested_ok.py").exists()
