from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .request_rules import (
    default_route_for_type,
    detect_governance_core_scope,
    get_request_type_definition,
    required_fields_for_type,
    request_type_requires_code_change,
    request_type_requires_cognition_update,
    request_type_requires_owner_approval,
    request_type_status,
)
from .schema_validator import validate_record_against_schema
from .utils import now_iso, read_record


def _normalize_list(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def validate_request_envelope(record: dict[str, Any]) -> dict[str, Any]:
    """Validate a Request Envelope structurally and semantically.

    This validator is intentionally conservative. It grants no execution or
    approval authority; it only reports whether the envelope is complete enough
    to enter later governance stages.
    """
    errors: list[str] = []
    warnings: list[str] = []

    schema_errors = validate_record_against_schema(record, "abyss.request_envelope.v1")
    errors.extend(schema_errors)

    request_type = str(record.get("request_type") or "")
    definition = get_request_type_definition(request_type) if request_type else None
    if not request_type:
        errors.append("REQUEST_ENVELOPE_MISSING_REQUEST_TYPE")
    elif not definition:
        errors.append(f"REQUEST_ENVELOPE_UNKNOWN_REQUEST_TYPE {request_type}")
    else:
        status = request_type_status(request_type)
        if status == "reserved":
            warnings.append(f"REQUEST_ENVELOPE_RESERVED_REQUEST_TYPE {request_type}")
        elif status not in {"active", "deprecated"}:
            warnings.append(f"REQUEST_ENVELOPE_UNUSUAL_REQUEST_TYPE_STATUS {request_type} {status}")

        expected_route = default_route_for_type(request_type)
        actual_route = record.get("governance_route")
        if expected_route and actual_route and actual_route != expected_route:
            warnings.append(f"REQUEST_ENVELOPE_ROUTE_DIFFERS_FROM_DEFAULT expected={expected_route} actual={actual_route}")

        if bool(record.get("requires_code_change")) != request_type_requires_code_change(request_type):
            warnings.append("REQUEST_ENVELOPE_REQUIRES_CODE_CHANGE_DIFFERS_FROM_TYPE_DEFAULT")
        if bool(record.get("requires_owner_approval")) != request_type_requires_owner_approval(request_type):
            warnings.append("REQUEST_ENVELOPE_REQUIRES_OWNER_APPROVAL_DIFFERS_FROM_TYPE_DEFAULT")
        if bool(record.get("requires_cognition_update")) != request_type_requires_cognition_update(request_type):
            warnings.append("REQUEST_ENVELOPE_REQUIRES_COGNITION_UPDATE_DIFFERS_FROM_TYPE_DEFAULT")

    request_fields = record.get("request_fields", {})
    if request_fields is None:
        request_fields = {}
    if not isinstance(request_fields, dict):
        errors.append("REQUEST_ENVELOPE_REQUEST_FIELDS_MUST_BE_OBJECT")
        request_fields = {}

    missing_type_fields: list[str] = []
    if request_type and definition:
        for field in required_fields_for_type(request_type):
            value = request_fields.get(field)
            if value in (None, "", []):
                missing_type_fields.append(field)

    declared_missing = record.get("missing_required_fields", [])
    if declared_missing and not isinstance(declared_missing, list):
        errors.append("REQUEST_ENVELOPE_MISSING_REQUIRED_FIELDS_MUST_BE_ARRAY")
        declared_missing = []

    if missing_type_fields:
        warnings.append("REQUEST_ENVELOPE_MISSING_TYPE_REQUIRED_FIELDS " + ",".join(missing_type_fields))

    if record.get("request_id", "").startswith("R-"):
        warnings.append("REQUEST_ENVELOPE_LEGACY_R_PREFIX_USE_REQ_PREFIX_FOR_NEW_REQUESTS")

    detection_text = "\n".join([
        str(record.get("title") or ""),
        str(record.get("description") or ""),
        str(record.get("notes") or ""),
        json.dumps(record.get("request_fields", {}), ensure_ascii=False),
        json.dumps(record.get("scope", []), ensure_ascii=False),
        json.dumps(record.get("related_documents", []), ensure_ascii=False),
    ])
    detection = detect_governance_core_scope(detection_text, paths=_normalize_list(record.get("scope")))
    if detection.get("requires_meta_governance") and request_type not in {"governance_mutation", "meta_evolution_request"}:
        warnings.append("REQUEST_ENVELOPE_GOVERNANCE_CORE_SCOPE_REQUIRES_META_GOVERNANCE")
    if request_type in {"governance_mutation", "meta_evolution_request"}:
        activation_policy = str(request_fields.get("activation_policy") or "")
        if "later" not in activation_policy.lower() and "delayed" not in activation_policy.lower() and "next" not in activation_policy.lower():
            warnings.append("REQUEST_ENVELOPE_META_GOVERNANCE_ACTIVATION_POLICY_SHOULD_BE_DELAYED")
        owner_required = str(request_fields.get("owner_approval_required") or "").lower()
        if owner_required not in {"true", "yes", "required", "explicit"}:
            warnings.append("REQUEST_ENVELOPE_META_GOVERNANCE_OWNER_APPROVAL_MUST_BE_EXPLICIT")

    ok = not errors and not missing_type_fields
    return {
        "schema": "abyss.request_envelope_validation.v1",
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "missing_required_fields": missing_type_fields,
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def normalize_request_envelope(
    *,
    request_type: str,
    title: str,
    description: str = "",
    request_id: str = "",
    source: str = "cli",
    created_by: str = "owner",
    scope: list[str] | str | None = None,
    risk_level: str = "medium",
    required_context: list[str] | str | None = None,
    expected_artifacts: list[str] | str | None = None,
    validation_plan: list[str] | str | None = None,
    related_documents: list[str] | str | None = None,
    notes: str = "",
    request_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized Request Envelope candidate.

    The returned envelope is a candidate semantic object only. It does not create
    a workflow, approve a request, or execute any mutation.
    """
    generated_request_id = request_id or "REQ-CANDIDATE-NOT-PERSISTED"
    definition = get_request_type_definition(request_type) or {}
    route = default_route_for_type(request_type) or "unknown"
    fields = dict(request_fields or {})

    envelope: dict[str, Any] = {
        "schema": "abyss.request_envelope.v1",
        "request_id": generated_request_id,
        "request_type": request_type,
        "source": source,
        "created_at": now_iso(),
        "created_by": created_by,
        "user_intent": title,
        "title": title,
        "description": description,
        "scope": _normalize_list(scope),
        "risk_level": risk_level,
        "governance_route": route,
        "requires_code_change": bool(definition.get("requires_code_change", False)),
        "requires_cognition_update": bool(definition.get("requires_cognition_update_assessment", False)),
        "requires_owner_approval": bool(definition.get("requires_owner_approval", True)),
        "required_context": _normalize_list(required_context),
        "expected_artifacts": _normalize_list(expected_artifacts),
        "validation_plan": _normalize_list(validation_plan),
        "related_documents": _normalize_list(related_documents),
        "status": "normalized",
        "request_fields": fields,
        "missing_required_fields": [],
        "warnings": [],
        "notes": notes,
        "contract_version": "abyss.request_envelope.v1",
    }

    validation = validate_request_envelope(envelope)
    envelope["missing_required_fields"] = validation.get("missing_required_fields", [])
    envelope["warnings"] = validation.get("warnings", [])
    if envelope["missing_required_fields"]:
        envelope["status"] = "needs_clarification"
    if not request_id:
        envelope["warnings"].append("REQUEST_ENVELOPE_CANDIDATE_ID_NOT_PERSISTED_SUPPLY_REQUEST_ID_BEFORE_STORAGE")
    return envelope


def load_request_envelope(path: Path) -> dict[str, Any]:
    try:
        return read_record(path)
    except UnicodeDecodeError:
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
            try:
                data = json.loads(raw.decode(encoding))
                if not isinstance(data, dict):
                    raise ValueError("request envelope file must contain an object")
                return data
            except Exception:
                continue
        raise


def render_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
