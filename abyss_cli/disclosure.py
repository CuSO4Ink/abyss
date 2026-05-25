from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_record, repo_root

SOURCE_PREFIXES = ("abyss_cli/", "prompts/agents/")
RUNTIME_PREFIXES = (".local/runtime/", "audit/")
PROVIDER_WORKSPACE_PREFIXES = (".local/knot_provider_workspace/",)

DISCLOSURE_LEVEL_ORDER = [
    "L0_entry",
    "L1_law",
    "L2_direction",
    "L3_system_map",
    "L4_capsules",
    "L5_contracts",
    "L6_source",
    "L7_runtime",
]

DEFAULT_TASK_DISCLOSURE = {
    "external_collaboration": {
        "default_disclosure_level": "L5_contracts",
        "max_disclosure_level": "L5_contracts",
        "source_access": False,
        "runtime_access": False,
    },
    "context_broker_feature": {
        "default_disclosure_level": "L5_contracts",
        "max_disclosure_level": "L6_source",
        "source_access": True,
        "runtime_access": False,
    },
    "governance_change": {
        "default_disclosure_level": "L5_contracts",
        "max_disclosure_level": "L6_source",
        "source_access": True,
        "runtime_access": False,
    },
}


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def classify_path_level(path: str) -> str:
    normalized = _normalize(path)
    if normalized == "ABYSS.md":
        return "L0_entry"
    if normalized in {"ABYSS_CONSTITUTION.md", "rules/system_brief.yaml"}:
        return "L1_law"
    if normalized.startswith("../abyss-data/user_data/projects/abyss-future-planning/"):
        return "L2_direction"
    if normalized == "SYSTEM_MAP.md" or normalized == "README.md":
        return "L3_system_map"
    if normalized == "rules/modules.yaml":
        return "L4_capsules"
    if normalized.startswith("rules/"):
        return "L5_contracts"
    if normalized.startswith(SOURCE_PREFIXES):
        return "L6_source"
    if normalized.startswith(RUNTIME_PREFIXES) or normalized.startswith(PROVIDER_WORKSPACE_PREFIXES):
        return "L7_runtime"
    return "unknown"


def disclosure_rank(level: str) -> int:
    try:
        return DISCLOSURE_LEVEL_ORDER.index(level)
    except ValueError:
        return -1


def analyze_task_disclosure(task_type: str, spec: dict[str, Any]) -> dict[str, Any]:
    settings = dict(DEFAULT_TASK_DISCLOSURE.get(task_type, {}))
    settings.update({
        key: spec[key]
        for key in ["default_disclosure_level", "max_disclosure_level", "source_access", "runtime_access"]
        if key in spec
    })
    default_level = settings.get("default_disclosure_level") or "L6_source"
    max_level = settings.get("max_disclosure_level") or "L6_source"
    source_access = bool(settings.get("source_access", True))
    runtime_access = bool(settings.get("runtime_access", False))

    referenced: list[str] = []
    for key in ["required_files", "required_rules", "required_prompts", "symbol_index_files"]:
        values = spec.get(key, [])
        if isinstance(values, list):
            referenced.extend(str(item) for item in values)

    files: list[dict[str, Any]] = []
    warnings: list[str] = []
    max_seen_level = "L0_entry"
    for item in referenced:
        normalized = _normalize(item)
        level = classify_path_level(normalized)
        if disclosure_rank(level) > disclosure_rank(max_seen_level):
            max_seen_level = level
        file_info = {"path": normalized, "level": level}
        files.append(file_info)
        if normalized.startswith(PROVIDER_WORKSPACE_PREFIXES):
            warnings.append(f"provider workspace must not be default context: {normalized}")
        if normalized.startswith(RUNTIME_PREFIXES) and not runtime_access:
            warnings.append(f"runtime context included without runtime_access: {normalized}")
        if normalized.startswith(SOURCE_PREFIXES) and not source_access:
            warnings.append(f"source context included while source_access=false: {normalized}")
        if disclosure_rank(level) > disclosure_rank(max_level):
            warnings.append(f"{normalized} is {level}, above max_disclosure_level {max_level}")

    return {
        "task_type": task_type,
        "default_disclosure_level": default_level,
        "max_disclosure_level": max_level,
        "source_access": source_access,
        "runtime_access": runtime_access,
        "max_seen_level": max_seen_level,
        "files": files,
        "warnings": warnings,
    }


def audit_context_manifest() -> dict[str, Any]:
    path = repo_root() / "rules" / "context_manifest.yaml"
    manifest = read_record(path)
    task_types = manifest.get("task_types", {})
    tasks: list[dict[str, Any]] = []
    warnings: list[str] = []
    if isinstance(task_types, dict):
        for task_type, spec in task_types.items():
            if not isinstance(spec, dict):
                continue
            result = analyze_task_disclosure(task_type, spec)
            tasks.append(result)
            warnings.extend(f"{task_type}: {warning}" for warning in result["warnings"])
    return {
        "schema": "abyss.disclosure_audit.v1",
        "ok": not warnings,
        "warnings": warnings,
        "tasks": tasks,
    }


def build_disclosure_plan(task_type: str, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a read-only disclosure plan for a task type.

    The plan explains the minimum declared context level and boundary checks.
    It does not expand context dynamically, grant source/runtime access, approve
    work, or mutate files.
    """
    if spec is None:
        manifest_path = repo_root() / "rules" / "context_manifest.yaml"
        manifest = read_record(manifest_path)
        task_types = manifest.get("task_types", {})
        fallback = manifest.get("fallback", {})
        if isinstance(task_types, dict) and task_type in task_types and isinstance(task_types[task_type], dict):
            spec = task_types[task_type]
        elif isinstance(fallback, dict):
            spec = fallback
        else:
            spec = {}

    analysis = analyze_task_disclosure(task_type, spec)
    warnings = list(analysis.get("warnings") or [])
    escalation_triggers = spec.get("escalation_triggers", []) if isinstance(spec, dict) else []
    forbidden_paths = spec.get("forbidden_paths", []) if isinstance(spec, dict) else []
    if not isinstance(escalation_triggers, list):
        escalation_triggers = []
    if not isinstance(forbidden_paths, list):
        forbidden_paths = []

    max_seen_level = str(analysis.get("max_seen_level") or "unknown")
    max_disclosure_level = str(analysis.get("max_disclosure_level") or "unknown")
    over_limit = disclosure_rank(max_seen_level) > disclosure_rank(max_disclosure_level)
    missing_policy = not spec

    recommended_action = "include_declared_context_only"
    if missing_policy:
        warnings.append(f"no disclosure policy found for task_type={task_type}; fallback/default context only")
        recommended_action = "request_context_manifest_policy"
    elif over_limit or warnings:
        recommended_action = "reduce_context_or_request_owner_review"

    return {
        "schema": "abyss.disclosure_plan.v1",
        "task_type": task_type,
        "ok": not warnings and not over_limit and not missing_policy,
        "default_disclosure_level": analysis.get("default_disclosure_level"),
        "max_disclosure_level": max_disclosure_level,
        "max_seen_level": max_seen_level,
        "source_access": analysis.get("source_access"),
        "runtime_access": analysis.get("runtime_access"),
        "files": analysis.get("files", []),
        "warnings": warnings,
        "escalation_triggers": escalation_triggers,
        "forbidden_paths": forbidden_paths,
        "recommended_action": recommended_action,
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def render_disclosure_plan(plan: dict[str, Any]) -> str:
    lines = [
        f"disclosure_plan_ok={plan.get('ok')}",
        f"task_type={plan.get('task_type')}",
        f"default={plan.get('default_disclosure_level')} max={plan.get('max_disclosure_level')} seen={plan.get('max_seen_level')}",
        f"source_access={plan.get('source_access')} runtime_access={plan.get('runtime_access')}",
        f"recommended_action={plan.get('recommended_action')}",
    ]
    warnings = plan.get("warnings") or []
    lines.append(f"warnings={len(warnings)}")
    for warning in warnings:
        lines.append(f"WARNING {warning}")
    triggers = plan.get("escalation_triggers") or []
    if triggers:
        lines.append("escalation_triggers:")
        for trigger in triggers:
            lines.append(f"- {trigger}")
    forbidden = plan.get("forbidden_paths") or []
    if forbidden:
        lines.append("forbidden_paths:")
        for path in forbidden:
            lines.append(f"- {path}")
    return "\n".join(lines)


def render_disclosure_audit(audit: dict[str, Any]) -> str:
    lines = [
        f"disclosure_audit_ok={audit.get('ok')}",
        f"warnings={len(audit.get('warnings') or [])}",
    ]
    for warning in audit.get("warnings") or []:
        lines.append(f"WARNING {warning}")
    lines.append("task_levels:")
    for task in audit.get("tasks") or []:
        lines.append(
            f"- {task.get('task_type')}: default={task.get('default_disclosure_level')} max={task.get('max_disclosure_level')} seen={task.get('max_seen_level')} source_access={task.get('source_access')} runtime_access={task.get('runtime_access')} warnings={len(task.get('warnings') or [])}"
        )
    return "\n".join(lines)
