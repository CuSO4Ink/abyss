from __future__ import annotations

import json
from typing import Any

from .policy import load_policy
from .utils import read_record, repo_root

CAPABILITIES_FILE = repo_root() / "rules" / "capabilities.yaml"


def harness_snapshot() -> dict[str, Any]:
    """Return the safe, read-only Harness subset that may be shown to an LLM."""
    policy = load_policy()
    capabilities = read_record(CAPABILITIES_FILE) if CAPABILITIES_FILE.exists() else {}
    path_constraints = policy.get("path_constraints", {})

    return {
        "schema": "abyss.harness_snapshot.v1",
        "purpose": "Help the LLM produce valid action proposals without granting execution authority.",
        "execution_boundary": {
            "llm_may": [
                "answer directly",
                "summarize risks and unknowns",
                "suggest abyss-action proposal blocks",
            ],
            "llm_must_not": [
                "claim that actions were executed",
                "modify files directly through provider side effects",
                "request or expose secrets",
                "bypass review or policy gates",
            ],
            "executor": "Abyss imports proposals and applies Harness policy. No action is executed automatically.",
        },
        "risk_decisions": policy.get("decisions", {}),
        "capability_groups": policy.get("capabilities", {}),
        "path_constraints": {
            "deny_absolute_or_repo_escape": path_constraints.get("deny_absolute_or_repo_escape", True),
            "safe_create_prefixes": path_constraints.get("safe_create_prefixes", []),
            "sensitive_patterns": path_constraints.get("sensitive_patterns", []),
        },
        "supported_capabilities_now": capabilities.get("supported_now", []),
        "action_proposal_format": {
            "fence": "abyss-action",
            "required_fields": ["capability", "operation", "path", "reason", "risk_estimate"],
            "example": {
                "capability": "fs.write",
                "operation": "create",
                "path": "artifacts/drafts/example.md",
                "reason": "Save a draft summary for user review.",
                "risk_estimate": "L2",
            },
        },
    }


def render_harness_markdown() -> str:
    snapshot = harness_snapshot()
    return "\n".join(
        [
            "## Harness snapshot for LLM",
            "",
            "This is a safe, read-only subset of the Abyss Harness. It describes how to propose actions; it does not grant execution authority.",
            "",
            "```json",
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            "```",
            "",
            "Important: Never claim an action has been executed. Only propose `abyss-action` blocks when concrete follow-up actions are needed.",
        ]
    )


def render_harness_json() -> str:
    return json.dumps(harness_snapshot(), ensure_ascii=False, indent=2) + "\n"
