"""Memory v0 — Direction and Decision Records (ROADMAP R085).

First runnable knowledge-precipitation mechanism for Abyss. It records the
user's direction choices and key decisions as structured candidate knowledge
and can project a single record into an Obsidian-friendly Markdown note.

Hard boundaries (Owner-approved constraints for v0):
- Minimal schema: only the fields below; no premature fields that Brain v1
  would later depend on and force a migration.
- ``project`` is a read-only projection (record -> Obsidian note). It is NOT
  the storage->user_data promotion mechanism from data_layers.yaml.
- No LLM calls, no policy/governance/prompt/ROADMAP changes, no agent write
  authority. Records are written only by the Owner through this CLI.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import (
    list_records,
    new_id,
    now_iso,
    read_record,
    relative_to_repo,
    repo_root,
    resolve_record_arg,
    runtime_root,
    write_record,
)

MEMORY_DIR = runtime_root() / "memory" / "records"
MEMORY_RECORD_SCHEMA = "abyss.memory_record.v1"
MEMORY_KINDS = ("decision", "direction")

# Obsidian projection target lives in the user data layer (Obsidian-first).
# Kept inside repo_root()/user_data so it stays consistent with data_layers.yaml
# placeholders; the real synced vault is the private abyss-data repo.
PROJECTION_DIR = repo_root() / "user_data" / "memory"


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
        return [item for item in items if item]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def create_memory_record(
    kind: str,
    title: str,
    body: str,
    *,
    related: Any = None,
    tags: Any = None,
    source: str = "owner_cli",
) -> dict[str, Any]:
    """Create and persist an abyss.memory_record.v1 record.

    This is candidate knowledge written explicitly by the Owner. It executes no
    action, approves nothing, and triggers no workflow transition.
    """
    if kind not in MEMORY_KINDS:
        raise SystemExit(
            f"Invalid memory kind: {kind!r}. Allowed kinds: {', '.join(MEMORY_KINDS)}"
        )
    if not title or not title.strip():
        raise SystemExit("Memory record requires a non-empty --title")
    if not body or not body.strip():
        raise SystemExit("Memory record requires a non-empty --body")

    record_id = new_id("mem")
    record = {
        "schema": MEMORY_RECORD_SCHEMA,
        "id": record_id,
        "kind": kind,
        "title": title.strip(),
        "body": body.strip(),
        "related": _normalize_list(related),
        "tags": _normalize_list(tags),
        "provenance": {
            "created_at": now_iso(),
            "source": source,
        },
    }
    path = MEMORY_DIR / f"{record_id}.yaml"
    write_record(path, record)
    append_event(
        "memory.record.created",
        f"{kind}: {title.strip()[:80]}",
        {"memory_id": record_id, "kind": kind, "path": path.as_posix()},
    )
    return record


def list_memory_records(kind: str | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in list_records(MEMORY_DIR, "mem"):
        try:
            record = read_record(path)
        except Exception as exc:  # defensive: surface unreadable records
            records.append({"path": path.as_posix(), "error": str(exc)})
            continue
        if kind and record.get("kind") != kind:
            continue
        records.append(record)
    return records


def load_memory_record(value: str) -> dict[str, Any]:
    path = resolve_record_arg(MEMORY_DIR, value, prefix="mem")
    return read_record(path)


def _projection_frontmatter(record: dict[str, Any]) -> str:
    provenance = record.get("provenance", {}) if isinstance(record.get("provenance"), dict) else {}
    related = record.get("related") or []
    tags = record.get("tags") or []
    lines = [
        "---",
        f"type: memory_{record.get('kind', 'record')}",
        "status: active",
        f"created: {provenance.get('created_at', '')}",
        f"source: {provenance.get('source', '')}",
        f"memory_id: {record.get('id', '')}",
        f"aliases: [\"{record.get('title', '')}\"]",
        "related: [" + ", ".join(json.dumps(str(r), ensure_ascii=False) for r in related) + "]",
        "tags: [" + ", ".join(json.dumps(str(t), ensure_ascii=False) for t in tags) + "]",
        "projection_note: \"Projected view only; not a storage->user_data promotion.\"",
        "---",
    ]
    return "\n".join(lines)


def project_memory_record(value: str) -> Path:
    """Project a single memory record into an Obsidian-friendly Markdown note.

    This is a read-only projection of an existing record. It does not mutate the
    source record and is explicitly NOT the storage->user_data promotion
    mechanism described in data_layers.yaml.
    """
    record = load_memory_record(value)
    record_id = str(record.get("id"))
    note_path = PROJECTION_DIR / f"{record_id}.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    body = str(record.get("body", "")).strip()
    title = str(record.get("title", "")).strip()
    content = (
        _projection_frontmatter(record)
        + "\n\n"
        + f"# {title}\n\n"
        + body
        + "\n\n---\n"
        + f"> Provenance: memory record `{record_id}` "
        + f"({record.get('kind')}). Source of truth lives in "
        + f"`{relative_to_repo(MEMORY_DIR / (record_id + '.yaml'))}`.\n"
    )
    note_path.write_text(content, encoding="utf-8")
    append_event(
        "memory.record.projected",
        f"projected {record_id} to Obsidian note",
        {"memory_id": record_id, "note_path": note_path.as_posix()},
    )
    return note_path


def validate_memory_record(record: dict[str, Any]) -> list[str]:
    """Return a list of schema problems for a memory record (empty = valid)."""
    problems: list[str] = []
    if record.get("schema") != MEMORY_RECORD_SCHEMA:
        problems.append(f"schema must be {MEMORY_RECORD_SCHEMA}")
    for field in ("id", "kind", "title", "body"):
        if not record.get(field):
            problems.append(f"missing required field: {field}")
    if record.get("kind") and record.get("kind") not in MEMORY_KINDS:
        problems.append(f"kind must be one of {MEMORY_KINDS}")
    for field in ("related", "tags"):
        if field in record and not isinstance(record.get(field), list):
            problems.append(f"{field} must be a list")
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        problems.append("provenance must be an object")
    else:
        if not provenance.get("created_at"):
            problems.append("provenance.created_at is required")
        if not provenance.get("source"):
            problems.append("provenance.source is required")
    return problems


def check_memory_store() -> tuple[bool, list[str]]:
    """Read-only integrity check for the memory store.

    Verifies record schema compliance without raising false positives on an
    empty store. Does not mutate anything.
    """
    messages: list[str] = []
    if not MEMORY_DIR.exists():
        return True, ["memory store empty (no records yet)"]
    ok = True
    for path in list_records(MEMORY_DIR, "mem"):
        try:
            record = read_record(path)
        except Exception as exc:
            ok = False
            messages.append(f"unreadable memory record {path.name}: {exc}")
            continue
        problems = validate_memory_record(record)
        if problems:
            ok = False
            messages.append(f"{path.name}: " + "; ".join(problems))
    if ok and not messages:
        messages.append("memory store ok")
    return ok, messages


def render_memory_records_json(kind: str | None = None) -> str:
    return json.dumps(list_memory_records(kind), ensure_ascii=False, indent=2)


def render_memory_record_json(value: str) -> str:
    return json.dumps(load_memory_record(value), ensure_ascii=False, indent=2)
