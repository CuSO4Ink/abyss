from __future__ import annotations

from typing import Any

from .utils import read_record, repo_root

REQUEST_TYPES_FILE = repo_root() / "rules" / "request_types.v1.yaml"
REQUEST_ENVELOPE_CONTRACT_FILE = repo_root() / "rules" / "contracts" / "request_envelope.v1.yaml"
REQUEST_ENVELOPE_SCHEMA_FILE = repo_root() / "rules" / "schemas" / "request_envelope.v1.schema.json"

REQUEST_RULE_CONTEXT_FILES = [
    "rules/request_types.v1.yaml",
    "rules/contracts/request_envelope.v1.yaml",
    "rules/schemas/request_envelope.v1.schema.json",
]

REQUEST_TYPE_TO_CONTEXT_TASK_TYPE = {
    "analysis_request": "governance_change",
    "bugfix_request": "changeset_validation_feature",
    "maintenance_request": "evolution_feature",
    "feature_request": "evolution_feature",
    "architecture_request": "governance_change",
    "governance_mutation": "governance_core_mutation",
    "meta_evolution_request": "governance_core_mutation",
    "external_task_request": "external_collaboration",
    "documentation_request": "governance_change",
    "insight_request": "summary_feature",
    "memory_request": "governance_change",
    "git_checkpoint_request": "governance_change",
    "obsidian_sync_request": "external_collaboration",
}

GOVERNANCE_CORE_SURFACES = {
    "self_evolution": ["abyss_cli/evolution.py", "abyss_cli/evolution_analysis.py", "prompts/agents/self_evolution_agent.md"],
    "harness_policy": ["abyss_cli/harness.py", "abyss_cli/harness_review.py", "prompts/agents/harness_agent.md"],
    "approval_gates": ["abyss_cli/owner.py", "abyss_cli/workflow.py"],
    "permission_boundaries": ["rules/capabilities.yaml", "rules/policy.yaml", "abyss_cli/changeset.py"],
    "memory_policy": ["rules/request_types.v1.yaml"],
    "context_disclosure_policy": ["abyss_cli/context_pack.py", "abyss_cli/disclosure.py", "rules/context_manifest.yaml"],
    "git_authority": ["abyss_cli/data_sync.py", "rules/capabilities.yaml"],
    "external_ai_authority": ["abyss_cli/external_collab.py", "EXTERNAL_MODEL_ONBOARDING.md"],
    "global_rules": ["ABYSS.md", "SYSTEM_MAP.md", "README.md"],
    "constitution_rules": ["ABYSS_CONSTITUTION.md"],
    "governance_contracts": ["rules/contracts/", "rules/schemas/", "rules/governance.yaml"],
}

GOVERNANCE_CORE_KEYWORDS = [
    "meta self-evolution",
    "meta-governance",
    "meta governance",
    "governance-core",
    "governance core",
    "governance mutation",
    "governance_mutation",
    "meta_evolution_request",
    "self evolution may evolve itself",
    "delayed activation",
    "old-rule review",
    "old rule review",
    "approval gate",
    "owner approval gate",
    "harness policy",
    "permission boundary",
    "permission boundaries",
    "allowed_fs_roots",
    "blocked_path_prefixes",
    "blocked_paths",
    "allowed_check_commands",
    "executor allowlist",
    "executor blocklist",
    "context disclosure policy",
    "memory policy",
    "git authority",
    "external ai authority",
    "constitution-level",
    "sovereign kernel",
]


class RequestRulesError(ValueError):
    pass


def load_request_types() -> dict[str, Any]:
    if not REQUEST_TYPES_FILE.exists():
        raise RequestRulesError(f"request types file not found: {REQUEST_TYPES_FILE}")
    data = read_record(REQUEST_TYPES_FILE)
    if not isinstance(data, dict):
        raise RequestRulesError("request types file must contain an object")
    return data


def load_request_envelope_contract() -> dict[str, Any]:
    if not REQUEST_ENVELOPE_CONTRACT_FILE.exists():
        raise RequestRulesError(f"request envelope contract file not found: {REQUEST_ENVELOPE_CONTRACT_FILE}")
    data = read_record(REQUEST_ENVELOPE_CONTRACT_FILE)
    if not isinstance(data, dict):
        raise RequestRulesError("request envelope contract must contain an object")
    return data


def get_request_type_definition(request_type: str) -> dict[str, Any] | None:
    data = load_request_types()
    request_types = data.get("request_types", {})
    if not isinstance(request_types, dict):
        return None
    definition = request_types.get(request_type)
    return definition if isinstance(definition, dict) else None


def list_request_type_definitions(*, include_reserved: bool = True) -> list[dict[str, Any]]:
    data = load_request_types()
    request_types = data.get("request_types", {})
    if not isinstance(request_types, dict):
        return []
    result: list[dict[str, Any]] = []
    for name in sorted(request_types):
        definition = request_types[name]
        if not isinstance(definition, dict):
            continue
        status = str(definition.get("status") or "")
        if not include_reserved and status != "active":
            continue
        item = dict(definition)
        item["request_type"] = name
        result.append(item)
    return result


def required_fields_for_type(request_type: str) -> list[str]:
    definition = get_request_type_definition(request_type)
    if not definition:
        return []
    fields = definition.get("required_fields", [])
    return [str(field) for field in fields] if isinstance(fields, list) else []


def default_route_for_type(request_type: str) -> str:
    definition = get_request_type_definition(request_type)
    return str(definition.get("default_route") or "") if definition else ""


def request_type_status(request_type: str) -> str:
    definition = get_request_type_definition(request_type)
    return str(definition.get("status") or "unknown") if definition else "unknown"


def request_type_requires_code_change(request_type: str) -> bool:
    definition = get_request_type_definition(request_type)
    return bool(definition.get("requires_code_change")) if definition else False


def request_type_requires_owner_approval(request_type: str) -> bool:
    definition = get_request_type_definition(request_type)
    return bool(definition.get("requires_owner_approval")) if definition else True


def request_type_requires_cognition_update(request_type: str) -> bool:
    definition = get_request_type_definition(request_type)
    return bool(definition.get("requires_cognition_update_assessment")) if definition else False


def context_task_type_for_request_type(request_type: str) -> str | None:
    return REQUEST_TYPE_TO_CONTEXT_TASK_TYPE.get(request_type)


def request_rule_context_files_for_request_type(request_type: str) -> list[str]:
    if not get_request_type_definition(request_type):
        return []
    return list(REQUEST_RULE_CONTEXT_FILES)


def governance_core_surfaces() -> dict[str, list[str]]:
    return {name: list(paths) for name, paths in GOVERNANCE_CORE_SURFACES.items()}


def detect_governance_core_scope(text: str, paths: list[str] | None = None) -> dict[str, Any]:
    """Conservatively detect whether text/paths touch governance-core surfaces.

    This detector grants no authority. It only marks requests or proposals that
    require meta-governance review instead of ordinary self-evolution closure.
    """
    text_lower = text.lower()
    matched_keywords = [keyword for keyword in GOVERNANCE_CORE_KEYWORDS if keyword in text_lower]
    matched_surfaces: dict[str, list[str]] = {}

    path_values = [str(path).replace("\\", "/") for path in (paths or [])]
    combined_path_text = "\n".join(path_values).lower()
    combined_text = f"{text_lower}\n{combined_path_text}"

    for surface, surface_paths in GOVERNANCE_CORE_SURFACES.items():
        hits: list[str] = []
        surface_phrase = surface.replace("_", " ")
        if surface in combined_text or surface_phrase in combined_text:
            hits.append(surface)
        for surface_path in surface_paths:
            normalized = surface_path.rstrip("/").lower()
            if normalized.endswith("/"):
                normalized = normalized[:-1]
            if normalized and normalized in combined_text:
                hits.append(surface_path)
        if hits:
            matched_surfaces[surface] = sorted(set(hits))

    requires_meta_governance = bool(matched_keywords or matched_surfaces)
    return {
        "schema": "abyss.governance_core_detection.v1",
        "requires_meta_governance": requires_meta_governance,
        "recommended_request_type": "governance_mutation" if requires_meta_governance else "",
        "recommended_route": "meta_governance" if requires_meta_governance else "",
        "matched_keywords": matched_keywords,
        "matched_surfaces": matched_surfaces,
        "protected_surfaces": sorted(GOVERNANCE_CORE_SURFACES.keys()),
        "required_review": [
            "review_under_prior_accepted_rules",
            "explicit_owner_approval",
            "risk_assessment",
            "rollback_plan",
            "validation_plan",
            "activation_note",
            "delayed_activation_in_later_cycle",
        ] if requires_meta_governance else [],
        "forbidden_closure": [
            "self_approval",
            "ordinary_self_evolution_apply",
            "same_cycle_activation",
            "retroactive_legitimization_by_new_rule",
        ] if requires_meta_governance else [],
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def validate_request_rules_config() -> list[str]:
    errors: list[str] = []
    try:
        data = load_request_types()
    except Exception as exc:
        return [f"REQUEST_TYPES_LOAD_FAILED {exc}"]

    if data.get("schema") != "abyss.request_types.v1":
        errors.append(f"REQUEST_TYPES_INVALID_SCHEMA {data.get('schema')}")

    if data.get("authority") != "canonical_request_semantics":
        errors.append(f"REQUEST_TYPES_INVALID_AUTHORITY {data.get('authority')}")

    request_types = data.get("request_types")
    if not isinstance(request_types, dict) or not request_types:
        errors.append("REQUEST_TYPES_MISSING_MAP")
        request_types = {}

    active = data.get("active_request_types", [])
    reserved = data.get("reserved_request_types", [])
    if not isinstance(active, list) or not active:
        errors.append("REQUEST_TYPES_MISSING_ACTIVE_LIST")
        active = []
    if not isinstance(reserved, list):
        errors.append("REQUEST_TYPES_INVALID_RESERVED_LIST")
        reserved = []

    for request_type in [*active, *reserved]:
        if request_type not in request_types:
            errors.append(f"REQUEST_TYPES_DECLARED_BUT_UNDEFINED {request_type}")

    expected_active = {
        "analysis_request",
        "bugfix_request",
        "maintenance_request",
        "feature_request",
        "architecture_request",
        "governance_mutation",
        "meta_evolution_request",
        "external_task_request",
    }
    for request_type in sorted(expected_active - set(str(item) for item in active)):
        errors.append(f"REQUEST_TYPES_MISSING_V0_ACTIVE {request_type}")

    for request_type in ("governance_mutation", "meta_evolution_request"):
        definition = request_types.get(request_type)
        if not isinstance(definition, dict):
            errors.append(f"REQUEST_TYPES_MISSING_META_GOVERNANCE_TYPE {request_type}")
            continue
        if definition.get("default_route") != "meta_governance":
            errors.append(f"REQUEST_TYPES_META_GOVERNANCE_BAD_ROUTE {request_type} {definition.get('default_route')}")
        for required_field in ["affected_governance_surface", "old_rule_review", "risk_assessment", "rollback_plan", "validation_plan", "activation_policy", "owner_approval_required"]:
            if required_field not in definition.get("required_fields", []):
                errors.append(f"REQUEST_TYPES_META_GOVERNANCE_MISSING_FIELD {request_type} {required_field}")

    if not GOVERNANCE_CORE_SURFACES:
        errors.append("GOVERNANCE_CORE_SURFACES_EMPTY")

    if "refactor_request" in request_types:
        errors.append("REQUEST_TYPES_REFACTOR_MUST_BE_MAINTENANCE_SUBTYPE")

    for name, definition in request_types.items():
        if not isinstance(definition, dict):
            errors.append(f"REQUEST_TYPE_INVALID_DEFINITION {name}")
            continue
        status = definition.get("status")
        if status not in {"active", "reserved", "deprecated"}:
            errors.append(f"REQUEST_TYPE_INVALID_STATUS {name} {status}")
        required_fields = definition.get("required_fields")
        if not isinstance(required_fields, list) or not all(isinstance(field, str) for field in required_fields):
            errors.append(f"REQUEST_TYPE_INVALID_REQUIRED_FIELDS {name}")
        if not definition.get("default_route"):
            errors.append(f"REQUEST_TYPE_MISSING_DEFAULT_ROUTE {name}")
        hard_boundaries = definition.get("hard_boundaries")
        if not isinstance(hard_boundaries, list) or not hard_boundaries:
            errors.append(f"REQUEST_TYPE_MISSING_HARD_BOUNDARIES {name}")

    try:
        contract = load_request_envelope_contract()
        if contract.get("schema") != "abyss.contract.v1":
            errors.append(f"REQUEST_ENVELOPE_CONTRACT_INVALID_SCHEMA {contract.get('schema')}")
        if contract.get("contract_id") != "abyss.request_envelope.v1":
            errors.append(f"REQUEST_ENVELOPE_CONTRACT_INVALID_ID {contract.get('contract_id')}")
        if not contract.get("hard_boundaries"):
            errors.append("REQUEST_ENVELOPE_CONTRACT_MISSING_HARD_BOUNDARIES")
    except Exception as exc:
        errors.append(f"REQUEST_ENVELOPE_CONTRACT_LOAD_FAILED {exc}")

    if not REQUEST_ENVELOPE_SCHEMA_FILE.exists():
        errors.append(f"REQUEST_ENVELOPE_SCHEMA_MISSING {REQUEST_ENVELOPE_SCHEMA_FILE.relative_to(repo_root())}")

    return errors
