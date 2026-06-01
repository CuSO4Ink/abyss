from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .request_envelope import validate_request_envelope
from .request_rules import detect_governance_core_scope
from .utils import new_id, now_iso, relative_to_repo, repo_root, runtime_root, write_record


META_GOVERNANCE_DIR = runtime_root() / "meta_governance"
META_GOVERNANCE_PACKETS_DIR = META_GOVERNANCE_DIR / "packets"
META_REQUEST_TYPES = {"governance_mutation", "meta_evolution_request"}
PRIOR_RULE_SOURCES = [
    "ABYSS.md",
    "ABYSS_CONSTITUTION.md",
    "rules/request_types.v1.yaml",
    "rules/contracts/request_envelope.v1.yaml",
    "rules/context_manifest.yaml",
]


def _text_for_detection(envelope: dict[str, Any]) -> str:
    return "\n".join([
        str(envelope.get("title") or ""),
        str(envelope.get("description") or ""),
        str(envelope.get("notes") or ""),
        json.dumps(envelope.get("request_fields", {}), ensure_ascii=False),
        json.dumps(envelope.get("scope", []), ensure_ascii=False),
        json.dumps(envelope.get("related_documents", []), ensure_ascii=False),
    ])


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _activation_policy_is_delayed(value: Any) -> bool:
    text = str(value or "").lower()
    return any(token in text for token in ("later", "delayed", "next", "后续", "延迟", "下一"))


def _owner_approval_is_explicit(value: Any) -> bool:
    text = str(value or "").lower()
    return text in {"true", "yes", "required", "explicit", "owner", "explicit_owner_approval", "是", "需要", "显式"}


def build_meta_governance_packet(envelope: dict[str, Any], *, source_path: Path | None = None) -> dict[str, Any]:
    """Build a meta-governance review packet for governance-core changes.

    The packet is candidate review material only. It grants no approval, does
    not execute workflows, does not apply changes, and does not activate any
    governance-core behavior.
    """
    request_type = str(envelope.get("request_type") or "")
    scope = _string_list(envelope.get("scope"))
    detection = detect_governance_core_scope(_text_for_detection(envelope), paths=scope)
    validation = validate_request_envelope(envelope)
    fields = envelope.get("request_fields") if isinstance(envelope.get("request_fields"), dict) else {}

    is_meta_type = request_type in META_REQUEST_TYPES
    requires_meta = bool(detection.get("requires_meta_governance")) or is_meta_type

    missing_meta_requirements: list[str] = []
    if not requires_meta:
        missing_meta_requirements.append("governance_core_scope_or_meta_request_type")
    if not is_meta_type:
        missing_meta_requirements.append("request_type_governance_mutation_or_meta_evolution_request")
    if not _owner_approval_is_explicit(fields.get("owner_approval_required")):
        missing_meta_requirements.append("explicit_owner_approval_required")
    if not _activation_policy_is_delayed(fields.get("activation_policy")):
        missing_meta_requirements.append("delayed_activation_policy")
    for required in ("old_rule_review", "risk_assessment", "rollback_plan", "validation_plan"):
        if not fields.get(required):
            missing_meta_requirements.append(required)

    prior_rule_sources = []
    for rel in PRIOR_RULE_SOURCES:
        path = repo_root() / rel
        prior_rule_sources.append({
            "path": rel,
            "exists": path.exists(),
        })

    return {
        "schema": "abyss.meta_governance_packet.v1",
        "id": new_id("meta_pkt"),
        "created_at": now_iso(),
        "source_request_path": relative_to_repo(source_path) if source_path else None,
        "request_id": envelope.get("request_id"),
        "request_type": request_type,
        "governance_route": envelope.get("governance_route"),
        "status": "ready_for_owner_review" if requires_meta and not missing_meta_requirements and validation.get("ok") else "needs_meta_governance_completion",
        "request_envelope": envelope,
        "request_validation": validation,
        "governance_core_detection": detection,
        "prior_rule_review": {
            "review_must_use_prior_accepted_rules": True,
            "candidate_prior_rule_sources": prior_rule_sources,
            "old_rule_review_from_request": fields.get("old_rule_review"),
            "new_rule_must_not_retroactively_legitimize_itself": True,
        },
        "required_meta_review": [
            "review_under_prior_accepted_rules",
            "explicit_owner_approval",
            "risk_assessment",
            "rollback_plan",
            "validation_plan",
            "activation_note",
            "delayed_activation_in_later_cycle",
        ],
        "forbidden_closure": [
            "self_approval",
            "ordinary_self_evolution_apply",
            "same_cycle_activation",
            "retroactive_legitimization_by_new_rule",
            "brain_or_external_model_approval",
        ],
        "activation_policy": {
            "delayed_activation_required": True,
            "activation_policy_from_request": fields.get("activation_policy"),
            "activation_allowed_in_this_cycle": False,
            "requires_later_cycle_activation_record": True,
        },
        "readiness": {
            "requires_meta_governance": requires_meta,
            "is_meta_request_type": is_meta_type,
            "missing_meta_requirements": missing_meta_requirements,
            "ready_for_implementation_work": False,
            "reason": "Meta-governance packet preparation is review material only; implementation still requires Harness and explicit Owner approval.",
        },
        "no_action_executed": True,
        "no_approval_granted": True,
        "no_files_modified_by_packet_builder": True,
    }


def persist_meta_governance_packet(packet: dict[str, Any]) -> Path:
    packet_id = str(packet.get("id") or new_id("meta_pkt"))
    path = META_GOVERNANCE_PACKETS_DIR / f"{packet_id}.yaml"
    write_record(path, packet)
    return path


def render_meta_governance_packet_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
