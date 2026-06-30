"""Skill v0 — Read-only Skill Registry (ROADMAP R089).

First runnable skill registry for Abyss. Declares available skills as named
candidate capabilities without granting execution authority. The registry is
a static declaration layer — no skill is executed, invoked, or scheduled.

Hard boundaries (Owner-approved constraints for v0):
- Read-only: list, show, and check the registry. No execution.
- No LLM calls, no file mutation, no workflow transitions.
- Skills are declarations only. Future proposals may add execution bindings,
  prompt templates, or agent wiring — each requiring its own roadmap item.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import repo_root, read_record

SKILLS_PATH = repo_root() / "rules" / "skills.yaml"
SKILL_REGISTRY_SCHEMA = "abyss.skill_registry.v1"
SKILL_REQUIRED_FIELDS = (
    "name",
    "description",
    "category",
    "status",
    "risk_level",
    "inputs",
    "outputs",
    "forbidden_actions",
    "invariants",
)


def _load_registry() -> dict[str, Any]:
    if not SKILLS_PATH.exists():
        raise SystemExit(f"Skill registry not found: {SKILLS_PATH}")
    return read_record(SKILLS_PATH)


def list_skills() -> list[dict[str, Any]]:
    """Return a compact list of all registered skills."""
    registry = _load_registry()
    skills = registry.get("skills", {})
    if not isinstance(skills, dict):
        return []
    result: list[dict[str, Any]] = []
    for skill_id, spec in skills.items():
        if not isinstance(spec, dict):
            continue
        result.append({
            "name": spec.get("name", skill_id),
            "description": spec.get("description", ""),
            "category": spec.get("category", ""),
            "status": spec.get("status", ""),
            "risk_level": spec.get("risk_level", ""),
            "mapped_command": spec.get("mapped_command", ""),
            "mapped_module": spec.get("mapped_module", ""),
        })
    return result


def show_skill(skill_id: str) -> dict[str, Any]:
    """Return the full spec for a single skill."""
    registry = _load_registry()
    skills = registry.get("skills", {})
    if not isinstance(skills, dict) or skill_id not in skills:
        raise SystemExit(f"Unknown skill: {skill_id!r}. Use 'abyss skill list' to see registered skills.")
    return skills[skill_id]


def check_skill_registry() -> tuple[bool, list[str]]:
    """Read-only integrity check for the skill registry.

    Verifies schema compliance and required fields without raising false
    positives on a valid registry. Does not mutate anything.
    """
    messages: list[str] = []
    if not SKILLS_PATH.exists():
        messages.append("skill registry missing (rules/skills.yaml)")
        return False, messages

    try:
        registry = read_record(SKILLS_PATH)
    except Exception as exc:
        messages.append(f"unreadable skill registry: {exc}")
        return False, messages

    if registry.get("schema") != SKILL_REGISTRY_SCHEMA:
        messages.append(f"invalid schema: expected {SKILL_REGISTRY_SCHEMA}, got {registry.get('schema')}")
        return False, messages

    skills = registry.get("skills", {})
    if not isinstance(skills, dict):
        messages.append("skills must be a map of skill_id -> spec")
        return False, messages

    if not skills:
        messages.append("skill registry empty (no skills registered)")
        return True, messages

    ok = True
    for skill_id, spec in skills.items():
        if not isinstance(spec, dict):
            messages.append(f"invalid skill spec: {skill_id}")
            ok = False
            continue
        for field in SKILL_REQUIRED_FIELDS:
            if field not in spec:
                messages.append(f"skill {skill_id} missing required field: {field}")
                ok = False
        if spec.get("status") and spec.get("status") not in ("registered", "active", "deprecated"):
            messages.append(f"skill {skill_id} has invalid status: {spec.get('status')}")
            ok = False
        if spec.get("risk_level") and spec.get("risk_level") not in ("low", "medium", "high"):
            messages.append(f"skill {skill_id} has invalid risk_level: {spec.get('risk_level')}")
            ok = False

    if ok and not messages:
        messages.append("skill registry ok")
    return ok, messages


def render_skills_json() -> str:
    """Render the full skill list as JSON."""
    return json.dumps(list_skills(), ensure_ascii=False, indent=2)


def render_skill_json(skill_id: str) -> str:
    """Render a single skill spec as JSON."""
    return json.dumps(show_skill(skill_id), ensure_ascii=False, indent=2)
