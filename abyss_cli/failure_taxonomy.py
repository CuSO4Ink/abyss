from __future__ import annotations

import json
from typing import Any

IMPLEMENTATION_FAILURE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("placeholder content is not allowed", "placeholder_content"),
    ("ellipsis placeholder expression is not allowed", "placeholder_content"),
    ("EDIT_PLAN_PARSE_ERROR", "edit_plan_parse_error"),
    ("EDIT_PLAN_CONTRACT_", "edit_plan_contract_failure"),
    ("symbol not found", "symbol_resolution_failure"),
    ("replace_symbol target is too large", "symbol_resolution_failure"),
    ("anchor match count", "anchor_resolution_failure"),
    ("OLD_CONTENT_MATCH_COUNT", "old_content_match_failure"),
    ("old_content", "old_content_match_failure"),
    ("context_request", "context_insufficient"),
    ("provider returned empty", "provider_empty_or_timeout"),
    ("timeout", "provider_empty_or_timeout"),
    ("unsupported edit kind", "unsupported_edit_kind"),
    ("EDIT_PLAN_CONTRACT_UNSUPPORTED_KIND", "unsupported_edit_kind"),
    ("missing new_content", "missing_new_content"),
    ("EDIT_PLAN_CONTRACT_MISSING_NEW_CONTENT", "missing_new_content"),
    ("EDIT_PLAN_CONTRACT_MISSING_CONTENT", "missing_new_content"),
    ("MISSING_EDITS", "missing_edits"),
    ("MISSING_OPERATIONS", "missing_edits"),
    ("INVALID_EDIT_PLAN_SCHEMA", "invalid_edit_plan_schema"),
    ("PATH_NOT_ALLOWED", "policy_boundary_rejected"),
    ("COMMAND_NOT_ALLOWED", "policy_boundary_rejected"),
    ("task_type", "task_type_misclassification"),
    ("harness_review_violation", "harness_violation"),
    ("harness review violation", "harness_violation"),
)

WORKFLOW_FAILURE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("placeholder content is not allowed", "placeholder_content"),
    ("ellipsis placeholder expression is not allowed", "placeholder_content"),
    ("repeated_placeholder_format_feedback", "repeated_placeholder_output"),
    ("implementation_repeated_placeholder_blocked", "repeated_placeholder_output"),
    ("context_request", "context_insufficient"),
    ("context insufficient", "context_insufficient"),
    ("implementation_context_insufficient", "context_insufficient"),
    ("implementation_agent_redundant_context_request", "context_insufficient"),
    ("task_type", "task_type_misclassification"),
    ("EDIT_PLAN_PARSE_ERROR", "edit_plan_parse_error"),
    ("EDIT_PLAN_CONTRACT_", "edit_plan_contract_failure"),
    ("MISSING_EDITS", "missing_edits"),
    ("MISSING_OPERATIONS", "missing_edits"),
    ("INVALID_EDIT_PLAN_SCHEMA", "invalid_edit_plan_schema"),
    ("implementation_agent_invalid_output", "edit_plan_parse_error"),
    ("symbol not found", "symbol_anchor_resolution_failure"),
    ("replace_symbol target is too large", "symbol_anchor_resolution_failure"),
    ("anchor match count", "symbol_anchor_resolution_failure"),
    ("OLD_CONTENT_MATCH_COUNT", "old_content_match_failure"),
    ("old_content", "old_content_match_failure"),
    ("harness_review_violation", "harness_violation"),
    ("provider returned empty", "provider_empty_or_timeout"),
    ("timeout", "provider_empty_or_timeout"),
    ("timed out", "provider_empty_or_timeout"),
    ("empty stdout", "provider_empty_or_timeout"),
    ("empty filtered response", "provider_empty_or_timeout"),
    ("response field was empty after filtering", "provider_empty_or_timeout"),
    ("implementation_agent_transient_failure", "provider_empty_or_timeout"),
    ("governance_constraint", "expected_governance_block"),
    ("implementation_blocked", "expected_governance_block"),
)

OUTPUT_CONTRACT_CATEGORIES = {
    "placeholder_content",
    "edit_plan_parse_error",
    "edit_plan_contract_failure",
    "invalid_edit_plan_schema",
    "missing_edits",
    "missing_new_content",
    "unsupported_edit_kind",
}

TARGET_RESOLUTION_CATEGORIES = {
    "symbol_resolution_failure",
    "symbol_anchor_resolution_failure",
    "anchor_resolution_failure",
    "old_content_match_failure",
}

PIPELINE_RUNTIME_CATEGORIES = {
    "provider_empty_or_timeout",
    "task_type_misclassification",
    "harness_violation",
}

CONTEXT_DISCOVERY_CATEGORIES = {
    "context_insufficient",
    "task_type_misclassification",
}


def validation_messages(changeset: dict[str, Any]) -> list[str]:
    validation = changeset.get("validation") if isinstance(changeset.get("validation"), dict) else {}
    messages = changeset.get("validation_errors") or changeset.get("errors") or validation.get("messages") or []
    if not isinstance(messages, list):
        return [str(messages)]
    return [str(message) for message in messages]


def classify_implementation_failure(message: str) -> str:
    lowered = message.lower()
    for marker, category in IMPLEMENTATION_FAILURE_CATEGORIES:
        if marker.lower() in lowered:
            return category
    return "other_invalid_changeset"


def classify_invalid_changeset_review_bucket(categories: list[str], messages: list[str]) -> str:
    combined = " ".join(messages).lower()
    category_set = set(categories)
    if "path_not_allowed" in combined or "command_not_allowed" in combined:
        return "policy_boundary_rejected"
    if category_set & OUTPUT_CONTRACT_CATEGORIES:
        return "implementation_output_contract_feedback"
    if category_set & TARGET_RESOLUTION_CATEGORIES:
        return "target_resolution_feedback"
    if category_set & PIPELINE_RUNTIME_CATEGORIES:
        return "pipeline_runtime_feedback"
    return "uncategorized_invalid_changeset"


def workflow_failure_text(workflow: dict[str, Any]) -> str:
    texts: list[str] = []
    last_error = str(workflow.get("last_error") or "")
    if last_error:
        texts.append(last_error)
    history = workflow.get("history") or []
    if history:
        last_event = history[-1] if isinstance(history[-1], dict) else {}
        event_name = str(last_event.get("event") or "")
        texts.append(event_name)
        details = last_event.get("details") or {}
        if isinstance(details, dict):
            texts.append(str(details.get("category") or ""))
            texts.append(str(details.get("reason") or ""))
            for msg in details.get("messages") or []:
                texts.append(str(msg))
    if not texts:
        texts.append(json.dumps(history, ensure_ascii=False))
    return " ".join(texts)


def classify_workflow_failure(workflow: dict[str, Any]) -> list[str]:
    combined = workflow_failure_text(workflow).lower()
    categories: set[str] = set()
    for marker, category in WORKFLOW_FAILURE_CATEGORIES:
        if marker.lower() in combined:
            categories.add(category)
    if "context" in combined:
        categories.add("context_insufficient")
    return sorted(categories) if categories else ["other"]


def probe_kind_from_categories(categories: list[str]) -> str:
    category_set = set(categories)
    if category_set & TARGET_RESOLUTION_CATEGORIES:
        return "target_resolution_probe"
    if category_set & OUTPUT_CONTRACT_CATEGORIES:
        return "edit_plan_contract_probe"
    if category_set & {"provider_empty_or_timeout"}:
        return "provider_reliability_probe"
    if category_set & CONTEXT_DISCOVERY_CATEGORIES:
        return "context_discovery_probe"
    return "general_failure_probe"


def describe_taxonomy() -> dict[str, Any]:
    return {
        "schema": "abyss.failure_taxonomy.v1",
        "implementation_failure_markers": len(IMPLEMENTATION_FAILURE_CATEGORIES),
        "workflow_failure_markers": len(WORKFLOW_FAILURE_CATEGORIES),
        "review_buckets": [
            "policy_boundary_rejected",
            "implementation_output_contract_feedback",
            "target_resolution_feedback",
            "pipeline_runtime_feedback",
            "uncategorized_invalid_changeset",
        ],
        "probe_kinds": [
            "target_resolution_probe",
            "edit_plan_contract_probe",
            "provider_reliability_probe",
            "context_discovery_probe",
            "general_failure_probe",
        ],
        "read_only": True,
    }
