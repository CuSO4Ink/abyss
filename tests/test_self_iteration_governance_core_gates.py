"""Regression tests for governance-core detection and hard gates."""

from __future__ import annotations

import pytest

import abyss_cli.evolution as evolution
import abyss_cli.workflow as workflow
from abyss_cli.request_rules import detect_governance_core_scope
from abyss_cli.utils import now_iso, read_record, write_record


def _governance_core_detection() -> dict:
    return {
        "schema": "abyss.governance_core_detection.v1",
        "requires_meta_governance": True,
        "recommended_request_type": "governance_mutation",
        "recommended_route": "meta_governance",
        "matched_keywords": ["approval gate"],
        "matched_surfaces": {"approval_gates": ["abyss_cli/workflow.py"]},
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def _proposal(**overrides: object) -> dict:
    base = {
        "schema": "abyss.evolution_proposal.v1",
        "id": "evo_prop_gate_test",
        "type": "evolution_proposal",
        "request_id": "evo_req_gate_test",
        "title": "Gate test proposal",
        "purpose": "Test governance-core command gates",
        "details": "test",
        "status": "needs_user_decision",
        "approval_required": True,
        "approval_status": "pending",
        "implementation_allowed": False,
        "risk_level": "L3",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "no_action_executed": True,
    }
    base.update(overrides)
    return base


def test_changeset_executor_allowlist_is_permission_boundary_governance_core():
    detection = detect_governance_core_scope(
        "Refactor abyss_cli/changeset.py to expand ALLOWED_FS_ROOTS so rules/ can be modified",
        paths=["abyss_cli/changeset.py"],
    )

    assert detection["requires_meta_governance"] is True
    assert "permission_boundaries" in detection["matched_surfaces"]
    assert "abyss_cli/changeset.py" in detection["matched_surfaces"]["permission_boundaries"]


def test_executor_allowlist_keyword_without_path_is_governance_core():
    detection = detect_governance_core_scope(
        "Please expand ALLOWED_FS_ROOTS and BLOCKED_PATH_PREFIXES for routine self-maintenance"
    )

    assert detection["requires_meta_governance"] is True
    assert "allowed_fs_roots" in detection["matched_keywords"]
    assert "blocked_path_prefixes" in detection["matched_keywords"]


def test_ordinary_evolution_approve_blocks_meta_governance_proposal(mini_repo):
    proposal = _proposal(governance_core_detection=_governance_core_detection())
    evolution.PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    write_record(evolution.PROPOSALS_DIR / f"{proposal['id']}.yaml", proposal)

    with pytest.raises(SystemExit, match="Cannot approve governance-core proposal"):
        evolution.approve_proposal(str(proposal["id"]))

    stored = read_record(evolution.PROPOSALS_DIR / f"{proposal['id']}.yaml")
    assert stored["status"] == "needs_user_decision"
    assert stored["implementation_allowed"] is False


def test_workflow_creation_blocks_meta_governance_proposal_even_if_marked_approved(mini_repo):
    proposal = _proposal(
        status="approved",
        approval_status="approved",
        implementation_allowed=True,
        roadmap_entry="R999",
        governance_core_detection=_governance_core_detection(),
    )

    with pytest.raises(SystemExit, match="Cannot start ordinary workflow for governance-core proposal"):
        workflow.create_workflow_for_proposal(proposal, provider="cli", source="test")

    workflows = list(workflow.WORKFLOWS_DIR.glob("*.yaml")) if workflow.WORKFLOWS_DIR.exists() else []
    assert workflows == []
