from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import repo_root


KNOWN_SMOKE_FIXTURES = {
    "artifacts/drafts/meta_governance_smoke_request.json": {
        "area": "meta_governance",
        "purpose": "Example Request Envelope for read-only meta-governance packet construction.",
    },
    "artifacts/drafts/edit_plan_contract_smoke.txt": {
        "area": "edit_plan_contract",
        "purpose": "Negative smoke input for edit-plan contract validation.",
    },
    "artifacts/drafts/edit_plan_recovery_smoke.txt": {
        "area": "context_recovery",
        "purpose": "Negative smoke input for context recovery packet construction.",
    },
}


def _file_summary(rel_path: str, meta: dict[str, str]) -> dict[str, Any]:
    path = repo_root() / rel_path
    return {
        "path": rel_path,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "area": meta.get("area"),
        "purpose": meta.get("purpose"),
        "fixture_role": "negative_or_boundary_smoke_input",
        "candidate_material_only": True,
        "not_a_runtime_record": True,
    }


def build_smoke_fixture_manifest() -> dict[str, Any]:
    """Return a read-only manifest for smoke fixtures created during stabilization."""
    fixtures = [_file_summary(path, meta) for path, meta in sorted(KNOWN_SMOKE_FIXTURES.items())]
    missing = [item["path"] for item in fixtures if not item.get("exists")]
    return {
        "schema": "abyss.smoke_fixture_manifest.v1",
        "read_only": True,
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "diagnostics": {
            "missing_fixture_count": len(missing),
            "missing_fixtures": missing,
        },
        "retention_policy": {
            "keep_under_artifacts_drafts": True,
            "do_not_import_as_changeset": True,
            "do_not_treat_as_owner_approval": True,
            "safe_to_delete_after_equivalent_tests_exist": True,
        },
        "no_action_executed": True,
        "no_approval_granted": True,
    }


def render_smoke_fixture_manifest_json() -> str:
    return json.dumps(build_smoke_fixture_manifest(), ensure_ascii=False, indent=2) + "\n"
