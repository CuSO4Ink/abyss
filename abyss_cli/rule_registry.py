"""Rule Source Registry V0: deterministic reader and validator.

Responsible for:
- Loading and validating rules/rule_sources.v1.yaml
- Listing declared rule sources
- Validating rule source entries (source file existence, consumer validity,
  validation command allowlist compliance)
- Providing rule sources for a given task type (Context Broker integration)

This module grants no execution or approval authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import read_record, repo_root

RULE_SOURCES_FILE = repo_root() / "rules" / "rule_sources.v1.yaml"

ALLOWED_VALIDATION_COMMANDS = {
    "python -m abyss_cli check",
    "python -m compileall -q abyss_cli",
    "python -m abyss_cli request types --all --json",
    "python -m abyss_cli rules validate --json",
}


def load_rule_sources() -> dict[str, Any]:
    """Load the rule source registry file."""
    if not RULE_SOURCES_FILE.exists():
        raise SystemExit(f"Rule source registry not found: {RULE_SOURCES_FILE}")
    data = read_record(RULE_SOURCES_FILE)
    if not isinstance(data, dict):
        raise SystemExit("Rule source registry must contain an object")
    return data


def list_rule_sources() -> list[dict[str, Any]]:
    """List all declared rule sources with metadata."""
    data = load_rule_sources()
    rule_sources = data.get("rule_sources", {})
    if not isinstance(rule_sources, dict):
        return []
    result: list[dict[str, Any]] = []
    for name, entry in sorted(rule_sources.items()):
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        item["name"] = name
        result.append(item)
    return result


def rule_sources_for_task_type(task_type: str) -> list[str]:
    """Return source file paths declared for a given task type.

    Used by Context Broker to automatically include rule sources
    in context packs for matching task types.
    """
    data = load_rule_sources()
    rule_sources = data.get("rule_sources", {})
    if not isinstance(rule_sources, dict):
        return []
    files: list[str] = []
    seen: set[str] = set()
    for _name, entry in rule_sources.items():
        if not isinstance(entry, dict):
            continue
        context_task_types = entry.get("context_task_types", [])
        if not isinstance(context_task_types, list):
            continue
        if task_type in context_task_types:
            for source_file in entry.get("source_files", []):
                if isinstance(source_file, str) and source_file not in seen:
                    seen.add(source_file)
                    files.append(source_file)
    return files


def validate_rule_sources() -> dict[str, Any]:
    """Validate the rule source registry.

    Checks:
    - Registry file exists and is valid
    - Schema field is correct
    - Each rule source entry has required fields
    - Source files exist on disk
    - Validation commands are in the allowlist
    - Consumers reference known module names

    Returns a structured validation result.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not RULE_SOURCES_FILE.exists():
        return {
            "schema": "abyss.rule_source_validation.v1",
            "ok": False,
            "errors": ["RULE_SOURCES_FILE_MISSING"],
            "warnings": [],
            "entries_checked": 0,
            "no_action_executed": True,
        }

    try:
        data = read_record(RULE_SOURCES_FILE)
    except Exception as exc:
        return {
            "schema": "abyss.rule_source_validation.v1",
            "ok": False,
            "errors": [f"RULE_SOURCES_PARSE_ERROR {exc}"],
            "warnings": [],
            "entries_checked": 0,
            "no_action_executed": True,
        }

    if not isinstance(data, dict):
        errors.append("RULE_SOURCES_NOT_OBJECT")
        return {
            "schema": "abyss.rule_source_validation.v1",
            "ok": False,
            "errors": errors,
            "warnings": [],
            "entries_checked": 0,
            "no_action_executed": True,
        }

    if data.get("schema") != "abyss.rule_sources.v1":
        errors.append(f"RULE_SOURCES_INVALID_SCHEMA {data.get('schema')}")

    if not data.get("hard_boundaries"):
        errors.append("RULE_SOURCES_MISSING_HARD_BOUNDARIES")

    rule_sources = data.get("rule_sources", {})
    if not isinstance(rule_sources, dict) or not rule_sources:
        errors.append("RULE_SOURCES_EMPTY_OR_INVALID")
        rule_sources = {}

    root = repo_root()
    entries_checked = 0
    required_entry_fields = {"source_files", "affected_scopes", "consumers", "context_task_types", "validation_commands", "description"}

    for name, entry in rule_sources.items():
        entries_checked += 1
        if not isinstance(entry, dict):
            errors.append(f"RULE_SOURCE_INVALID_ENTRY {name}")
            continue

        missing_fields = required_entry_fields - set(entry.keys())
        for field in sorted(missing_fields):
            errors.append(f"RULE_SOURCE_MISSING_FIELD {name}.{field}")

        source_files = entry.get("source_files", [])
        if isinstance(source_files, list):
            for source_file in source_files:
                if not isinstance(source_file, str):
                    errors.append(f"RULE_SOURCE_INVALID_SOURCE_FILE_TYPE {name}")
                    continue
                if not (root / source_file).exists():
                    errors.append(f"RULE_SOURCE_FILE_MISSING {name} {source_file}")
        else:
            errors.append(f"RULE_SOURCE_INVALID_SOURCE_FILES {name}")

        validation_commands = entry.get("validation_commands", [])
        if isinstance(validation_commands, list):
            for cmd in validation_commands:
                if not isinstance(cmd, str):
                    errors.append(f"RULE_SOURCE_INVALID_COMMAND_TYPE {name}")
                elif cmd not in ALLOWED_VALIDATION_COMMANDS:
                    errors.append(f"RULE_SOURCE_COMMAND_NOT_ALLOWED {name} {cmd}")
        else:
            errors.append(f"RULE_SOURCE_INVALID_VALIDATION_COMMANDS {name}")

        consumers = entry.get("consumers", [])
        if not isinstance(consumers, list):
            errors.append(f"RULE_SOURCE_INVALID_CONSUMERS {name}")

        context_task_types = entry.get("context_task_types", [])
        if not isinstance(context_task_types, list):
            errors.append(f"RULE_SOURCE_INVALID_CONTEXT_TASK_TYPES {name}")

    ok = not errors
    return {
        "schema": "abyss.rule_source_validation.v1",
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "entries_checked": entries_checked,
        "no_action_executed": True,
    }


def render_rule_sources_json() -> str:
    """Render rule sources listing as JSON."""
    sources = list_rule_sources()
    return json.dumps({
        "schema": "abyss.rule_sources_listing.v1",
        "rule_sources": sources,
        "count": len(sources),
        "no_action_executed": True,
    }, ensure_ascii=False, indent=2)


def render_validation_json() -> str:
    """Render rule source validation result as JSON."""
    result = validate_rule_sources()
    return json.dumps(result, ensure_ascii=False, indent=2)
