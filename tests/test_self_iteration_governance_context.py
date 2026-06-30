"""Unit tests for context coverage, meta-governance, taxonomy."""

from __future__ import annotations

import abyss_cli.context_pack as ctx
import abyss_cli.meta_governance as mg
import abyss_cli.failure_taxonomy as ft


# --------------------------- context coverage ------------------------------ #
# Real signature: validate_task_coverage_manifest(target_record, context_pack)
# manifest lives at target_record["task_coverage_manifest"]; coverage is checked
# against context_pack["files_included"] / ["modules_included"].

def _target(manifest=None):
    rec = {}
    if manifest is not None:
        rec["task_coverage_manifest"] = manifest
    return rec


def _pack(files=None, modules=None):
    return {"files_included": files or [], "modules_included": modules or []}


def test_coverage_no_manifest_is_ok():
    result = ctx.validate_task_coverage_manifest(_target(None), _pack())
    assert result["ok"] is True
    assert result["has_manifest"] is False


def test_coverage_missing_expected_file_reported():
    manifest = {"expected_files": ["abyss_cli/example.py"], "expected_domains": []}
    result = ctx.validate_task_coverage_manifest(_target(manifest), _pack(files=[]))
    assert result["missing_files"] == ["abyss_cli/example.py"]
    assert result["ok"] is False


def test_coverage_missing_domain_reported():
    manifest = {"expected_files": [], "expected_domains": ["changeset"]}
    result = ctx.validate_task_coverage_manifest(_target(manifest), _pack(modules=[]))
    assert result["missing_domains"] == ["changeset"]


def test_coverage_full_is_ok():
    manifest = {"expected_files": ["abyss_cli/example.py"], "expected_domains": ["changeset"]}
    result = ctx.validate_task_coverage_manifest(
        _target(manifest), _pack(files=["abyss_cli/example.py"], modules=["changeset"])
    )
    assert result["ok"] is True
    assert not result["missing_files"]
    assert not result["missing_domains"]


def test_coverage_unknown_field_warns():
    manifest = {"expected_files": [], "expected_domains": [], "bogus_field": 1}
    result = ctx.validate_task_coverage_manifest(_target(manifest), _pack())
    assert any("UNKNOWN_FIELD" in w for w in result["warnings"])


def test_coverage_does_not_grant_authority():
    """Coverage validator must be purely descriptive (no execute/approve keys)."""
    manifest = {"expected_files": [], "expected_domains": []}
    result = ctx.validate_task_coverage_manifest(_target(manifest), _pack())
    assert "approval" not in result
    assert "execute" not in result


# --------------------------- meta-governance -------------------------------- #

def test_meta_packet_incomplete_needs_completion(make_envelope):
    env = make_envelope(request_type="governance_mutation_request", title="change a core rule")
    packet = mg.build_meta_governance_packet(env)
    assert packet["no_action_executed"] is True
    assert packet["no_approval_granted"] is True
    assert packet["no_files_modified_by_packet_builder"] is True
    # Missing required governance fields -> not ready, no same-cycle activation.
    assert packet["status"] == "needs_meta_governance_completion"
    assert packet["readiness"]["ready_for_implementation_work"] is False
    assert packet["activation_policy"]["activation_allowed_in_this_cycle"] is False
    assert packet["readiness"]["missing_meta_requirements"]


def test_meta_packet_forbids_self_approval_closure(make_envelope):
    env = make_envelope(request_type="governance_mutation_request", title="rewrite governance")
    packet = mg.build_meta_governance_packet(env)
    forbidden = packet["forbidden_closure"]
    for marker in (
        "self_approval",
        "ordinary_self_evolution_apply",
        "same_cycle_activation",
        "retroactive_legitimization_by_new_rule",
        "brain_or_external_model_approval",
    ):
        assert marker in forbidden


def test_meta_packet_complete_can_be_ready_but_not_for_impl(make_envelope):
    """Even a complete meta request is owner-review-ready, never impl-ready."""
    env = make_envelope(
        request_type="governance_mutation_request",
        title="adjust a governance rule",
        scope=["rules/governance.yaml"],
        request_fields={
            "owner_approval_required": True,
            "activation_policy": "delayed",
            "old_rule_review": "reviewed",
            "risk_assessment": "done",
            "rollback_plan": "documented",
            "validation_plan": "documented",
        },
    )
    packet = mg.build_meta_governance_packet(env)
    # Regardless of completeness, impl work and same-cycle activation stay off.
    assert packet["readiness"]["ready_for_implementation_work"] is False
    assert packet["activation_policy"]["activation_allowed_in_this_cycle"] is False


# --------------------------- failure taxonomy ------------------------------- #

def test_classify_placeholder():
    assert ft.classify_implementation_failure("placeholder content is not allowed") == "placeholder_content"


def test_classify_parse_error():
    assert ft.classify_implementation_failure("EDIT_PLAN_PARSE_ERROR bad") == "edit_plan_parse_error"


def test_classify_policy_boundary():
    assert ft.classify_implementation_failure("PATH_NOT_ALLOWED op rules/x") == "policy_boundary_rejected"


def test_describe_taxonomy_is_read_only():
    assert ft.describe_taxonomy().get("read_only") is True


def test_probe_kind_from_categories_returns_string():
    kind = ft.probe_kind_from_categories(["placeholder_content"])
    assert isinstance(kind, str) and kind
