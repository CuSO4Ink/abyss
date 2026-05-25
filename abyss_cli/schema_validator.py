from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_record, repo_root

SCHEMAS_DIR = repo_root() / "rules" / "schemas"


class SchemaValidationError(ValueError):
    pass


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    expected_types = expected if isinstance(expected, list) else [expected]
    actual = _type_name(value)
    if actual in expected_types:
        return True
    if actual == "integer" and "number" in expected_types:
        return True
    return False


def validate_json_schema_subset(instance: Any, schema: dict[str, Any], *, path: str = "$") -> list[str]:
    """Validate a JSON value against the Abyss-supported JSON Schema subset.

    Supported keywords: type, required, properties, items, enum, const,
    additionalProperties, minItems, minLength, anyOf, oneOf.
    This intentionally avoids external dependencies while making contracts
    machine-checkable for structural validation. Semantic and governance checks
    still belong in domain code.
    """
    errors: list[str] = []

    if "anyOf" in schema:
        variants = schema.get("anyOf") or []
        if not any(not validate_json_schema_subset(instance, item, path=path) for item in variants if isinstance(item, dict)):
            errors.append(f"{path}: does not match anyOf")
        return errors

    if "oneOf" in schema:
        variants = schema.get("oneOf") or []
        matches = sum(1 for item in variants if isinstance(item, dict) and not validate_json_schema_subset(instance, item, path=path))
        if matches != 1:
            errors.append(f"{path}: expected exactly one oneOf match, got {matches}")
        return errors

    if "const" in schema and instance != schema.get("const"):
        errors.append(f"{path}: expected const {schema.get('const')!r}, got {instance!r}")

    if "enum" in schema and instance not in schema.get("enum", []):
        errors.append(f"{path}: expected one of {schema.get('enum')!r}, got {instance!r}")

    if "type" in schema and not _matches_type(instance, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']!r}, got {_type_name(instance)}")
        return errors

    if isinstance(instance, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for field in required:
                if field not in instance:
                    errors.append(f"{path}: missing required field {field}")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for field, field_schema in properties.items():
                if field in instance and isinstance(field_schema, dict):
                    errors.extend(validate_json_schema_subset(instance[field], field_schema, path=f"{path}.{field}"))

        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            allowed = set(properties.keys())
            for field in instance:
                if field not in allowed:
                    errors.append(f"{path}: additional property not allowed: {field}")

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(instance) < min_items:
            errors.append(f"{path}: expected at least {min_items} items, got {len(instance)}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate_json_schema_subset(item, item_schema, path=f"{path}[{index}]"))

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(instance) < min_length:
            errors.append(f"{path}: expected minLength {min_length}, got {len(instance)}")

    return errors


def load_schema(schema_id: str) -> dict[str, Any]:
    filename = schema_id.removeprefix("abyss.") + ".schema.json"
    path = SCHEMAS_DIR / filename
    if not path.exists():
        raise SchemaValidationError(f"schema file not found for {schema_id}: {path}")
    schema = read_record(path)
    if schema.get("$id") != schema_id:
        raise SchemaValidationError(f"schema id mismatch: expected {schema_id}, got {schema.get('$id')}")
    return schema


def validate_record_against_schema(record: dict[str, Any], schema_id: str | None = None) -> list[str]:
    resolved_schema_id = schema_id or str(record.get("schema") or "")
    if not resolved_schema_id:
        return ["$: missing schema id"]
    try:
        schema = load_schema(resolved_schema_id)
    except SchemaValidationError as exc:
        return [str(exc)]
    return validate_json_schema_subset(record, schema)


def validate_schema_file(path: Path) -> list[str]:
    try:
        schema = read_record(path)
    except Exception as exc:
        return [f"{path}: invalid JSON schema file: {exc}"]
    errors: list[str] = []
    for required in ["$schema", "$id", "type", "required", "properties"]:
        if required not in schema:
            errors.append(f"{path}: missing schema keyword {required}")
    if schema.get("type") != "object":
        errors.append(f"{path}: top-level type must be object")
    return errors
