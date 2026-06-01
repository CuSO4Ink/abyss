from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import repo_root


RUNTIME_SCHEMAS = {
    "abyss.summary.v1": {"producer": "summary.build_summary", "contract_file": None, "json_schema_file": None},
    "abyss.insight_snapshot.v1": {"producer": "insight.build_insight_snapshot", "contract_file": None, "json_schema_file": None},
    "abyss.brain_brief.v1": {"producer": "brain.build_brain_brief", "contract_file": None, "json_schema_file": None},
    "abyss.failure_taxonomy.v1": {"producer": "failure_taxonomy.describe_taxonomy", "contract_file": None, "json_schema_file": None},
    "abyss.self_iteration_reliability_metrics.v1": {"producer": "self_iteration_metrics.build_self_iteration_reliability_metrics", "contract_file": None, "json_schema_file": None},
    "abyss.failure_probe_candidates.v1": {"producer": "failure_probe.build_failure_probe_candidates", "contract_file": None, "json_schema_file": None},
    "abyss.failure_probe_candidate.v1": {"producer": "failure_probe.build_failure_probe_candidates", "contract_file": None, "json_schema_file": None},
    "abyss.context_recovery_packet.v1": {"producer": "patch_compiler._build_context_recovery_packet", "contract_file": None, "json_schema_file": None},
    "abyss.changeset_preflight.v1": {"producer": "changeset.changeset_preflight_report", "contract_file": None, "json_schema_file": None},
    "abyss.changeset_dry_run.v1": {"producer": "changeset.dry_run_changeset", "contract_file": None, "json_schema_file": None},
}


def _rel(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def _rules_contracts() -> dict[str, dict[str, Any]]:
    root = repo_root()
    contracts_dir = root / "rules" / "contracts"
    schemas_dir = root / "rules" / "schemas"
    registry: dict[str, dict[str, Any]] = {}
    for contract_path in sorted(contracts_dir.glob("*.v*.yaml")) if contracts_dir.exists() else []:
        name = contract_path.name.removesuffix(".yaml")
        schema_name = f"{name}.schema.json"
        schema_path = schemas_dir / schema_name
        schema_id = "abyss." + name.replace(".v", ".v")
        registry[schema_id] = {
            "producer": "rules/contracts",
            "contract_file": _rel(contract_path),
            "json_schema_file": _rel(schema_path) if schema_path.exists() else None,
            "json_schema_exists": schema_path.exists(),
        }
    return registry


def build_schema_registry() -> dict[str, Any]:
    """Build a read-only registry of exposed schemas and contract files."""
    registry = _rules_contracts()
    for schema, meta in RUNTIME_SCHEMAS.items():
        registry.setdefault(schema, {}).update(meta)
        registry[schema].setdefault("runtime_only", True)
        registry[schema].setdefault("json_schema_exists", bool(registry[schema].get("json_schema_file")))

    entries = []
    for schema, meta in sorted(registry.items()):
        entries.append({
            "schema": schema,
            "producer": meta.get("producer"),
            "contract_file": meta.get("contract_file"),
            "json_schema_file": meta.get("json_schema_file"),
            "json_schema_exists": bool(meta.get("json_schema_exists")),
            "runtime_only": bool(meta.get("runtime_only")),
        })

    runtime_only_missing_schema = [item for item in entries if item.get("runtime_only") and not item.get("json_schema_file")]
    contracts_missing_json_schema = [item for item in entries if item.get("contract_file") and not item.get("json_schema_exists")]
    return {
        "schema": "abyss.schema_registry.v1",
        "read_only": True,
        "entry_count": len(entries),
        "entries": entries,
        "diagnostics": {
            "runtime_only_schema_count": len(runtime_only_missing_schema),
            "contracts_missing_json_schema_count": len(contracts_missing_json_schema),
            "contracts_missing_json_schema": [item.get("schema") for item in contracts_missing_json_schema],
        },
        "stabilization_notes": [
            "Runtime-only schemas are allowed during stabilization but should be promoted to rules/contracts plus JSON Schema before becoming external contracts.",
            "This registry is observational only; it does not validate, approve, or modify schemas.",
        ],
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def render_schema_registry_json() -> str:
    return json.dumps(build_schema_registry(), ensure_ascii=False, indent=2) + "\n"
