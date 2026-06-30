"""External Adapter v0 — Outbox Pattern (ROADMAP R090).

Implements the Outbox Pattern for Abyss's external platform interactions.
Abyss writes needs to a local outbox directory; external platforms (e.g., BoxAI)
poll, read, fulfill, and write back fulfillment records.

Abyss never makes outbound calls. This module only:
  - writes need declarations to local files (outbox)
  - reads fulfillment records from local files
  - lists/shows the registry and outbox state (read-only)
  - validates registry consistency (read-only)

This is the originator side of the Outbox Pattern. The platform side
(BoxAI fulfillment) happens outside Abyss.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import new_id, now_iso, read_record, repo_root, runtime_root, write_record

REGISTRY_PATH = repo_root() / "rules" / "external_adapters.yaml"
NEED_SCHEMA_ID = "abyss.external_need.v1"
REGISTRY_SCHEMA_ID = "abyss.external_need_registry.v1"

OUTBOX_DIR = runtime_root() / "outbox" / "needs"
FULFILLMENT_DIR = runtime_root() / "outbox" / "fulfillments"

VALID_LIFECYCLE_STATUSES = ("pending", "fulfilled", "failed")

REGISTRY_REQUIRED_FIELDS = (
    "schema",
    "purpose",
    "need_type_namespace",
    "lifecycle_states",
    "outbox_transport",
    "need_templates",
    "capability_cards",
    "hard_boundaries",
)

NEED_REQUIRED_FIELDS = (
    "schema",
    "id",
    "type",
    "version",
    "payload",
    "lifecycle",
)

NEED_TEMPLATE_REQUIRED_FIELDS = (
    "description",
    "type",
    "trigger",
    "payload_fields",
)


def _load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"External need registry not found: {REGISTRY_PATH}")
    return read_record(REGISTRY_PATH)


def _ensure_dirs() -> None:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    FULFILLMENT_DIR.mkdir(parents=True, exist_ok=True)


def _write_need_record(need: dict[str, Any]) -> Path:
    _ensure_dirs()
    path = OUTBOX_DIR / f"{need['id']}.json"
    write_record(path, need)
    return path


def _read_need_record(need_id: str) -> dict[str, Any] | None:
    path = OUTBOX_DIR / f"{need_id}.json"
    if not path.exists():
        return None
    return read_record(path)


def _list_need_files() -> list[Path]:
    if not OUTBOX_DIR.exists():
        return []
    return sorted(OUTBOX_DIR.glob("*.json"))


def _list_fulfillment_files() -> list[Path]:
    if not FULFILLMENT_DIR.exists():
        return []
    return sorted(FULFILLMENT_DIR.glob("*.json"))


def _read_fulfillment(need_id: str) -> dict[str, Any] | None:
    path = FULFILLMENT_DIR / f"{need_id}.fulfillment.json"
    if not path.exists():
        return None
    return read_record(path)


# ── Registry operations (read-only) ──────────────────────────────

def list_need_templates() -> list[dict[str, Any]]:
    """Return compact list of declared need templates."""
    registry = _load_registry()
    templates = registry.get("need_templates", {})
    result: list[dict[str, Any]] = []
    for tid, spec in templates.items():
        if not isinstance(spec, dict):
            continue
        result.append({
            "id": tid,
            "description": spec.get("description", ""),
            "type": spec.get("type", ""),
            "trigger": spec.get("trigger", ""),
        })
    return result


def show_need_template(template_id: str) -> dict[str, Any]:
    """Return full spec for a single need template."""
    registry = _load_registry()
    templates = registry.get("need_templates", {})
    if template_id not in templates:
        raise SystemExit(f"Unknown need template: {template_id!r}. Use 'abyss adapter list' to see registered templates.")
    return templates[template_id]


def list_capability_cards() -> list[dict[str, Any]]:
    """Return compact list of registered platform capability cards."""
    registry = _load_registry()
    cards = registry.get("capability_cards", {})
    result: list[dict[str, Any]] = []
    for pid, spec in cards.items():
        if not isinstance(spec, dict):
            continue
        result.append({
            "platform_id": pid,
            "description": spec.get("description", ""),
            "supported_types": spec.get("supported_types", []),
            "transport": spec.get("transport", ""),
            "enabled": spec.get("enabled", False),
            "polling_cadence": spec.get("polling_cadence", ""),
        })
    return result


def show_capability_card(platform_id: str) -> dict[str, Any]:
    """Return full spec for a single capability card."""
    registry = _load_registry()
    cards = registry.get("capability_cards", {})
    if platform_id not in cards:
        raise SystemExit(f"Unknown platform: {platform_id!r}. Use 'abyss adapter platforms' to see registered platforms.")
    return cards[platform_id]


def check_registry() -> tuple[bool, list[str]]:
    """Read-only integrity check for the external need registry."""
    messages: list[str] = []
    if not REGISTRY_PATH.exists():
        messages.append("external need registry missing (rules/external_adapters.yaml)")
        return False, messages

    try:
        registry = read_record(REGISTRY_PATH)
    except Exception as exc:
        messages.append(f"unreadable registry: {exc}")
        return False, messages

    if registry.get("schema") != REGISTRY_SCHEMA_ID:
        messages.append(f"invalid schema: expected {REGISTRY_SCHEMA_ID}, got {registry.get('schema')}")
        return False, messages

    ok = True
    for field in REGISTRY_REQUIRED_FIELDS:
        if field not in registry:
            messages.append(f"registry missing required field: {field}")
            ok = False

    templates = registry.get("need_templates", {})
    if not isinstance(templates, dict):
        messages.append("need_templates must be a map")
        ok = False
    else:
        for tid, spec in templates.items():
            if not isinstance(spec, dict):
                messages.append(f"invalid template spec: {tid}")
                ok = False
                continue
            for field in NEED_TEMPLATE_REQUIRED_FIELDS:
                if field not in spec:
                    messages.append(f"template {tid} missing required field: {field}")
                    ok = False

    cards = registry.get("capability_cards", {})
    if not isinstance(cards, dict):
        messages.append("capability_cards must be a map")
        ok = False
    else:
        for pid, spec in cards.items():
            if not isinstance(spec, dict):
                messages.append(f"invalid capability card: {pid}")
                ok = False
                continue
            if "supported_types" not in spec or not isinstance(spec["supported_types"], list):
                messages.append(f"capability card {pid} missing supported_types list")
                ok = False
            if "transport" not in spec:
                messages.append(f"capability card {pid} missing transport field")
                ok = False

    if ok and not messages:
        messages.append("external need registry ok")
    return ok, messages


# ── Outbox operations (write needs, read fulfillments) ───────────

def write_need(
    need_type: str,
    payload: dict[str, Any],
    *,
    created_by: str = "manual",
    template_id: str = "",
) -> dict[str, Any]:
    """Write a need declaration to the outbox.

    Abyss calls this to declare an external need. The need is written as a
    local JSON file. An external platform will later read and fulfill it.
    Abyss never makes an outbound call.
    """
    need_id = new_id("need")
    need = {
        "schema": NEED_SCHEMA_ID,
        "id": need_id,
        "type": need_type,
        "version": "1",
        "payload": payload,
        "lifecycle": {
            "status": "pending",
            "created_at": now_iso(),
        },
        "created_by": created_by,
    }
    if template_id:
        need["template_id"] = template_id

    path = _write_need_record(need)
    append_event("external_need.written", f"Need {need_id} ({need_type}) written to outbox", {
        "need_id": need_id,
        "need_type": need_type,
        "created_by": created_by,
        "path": path.as_posix(),
    })
    return need


def list_needs(status_filter: str | None = None) -> list[dict[str, Any]]:
    """List all needs in the outbox, optionally filtered by lifecycle status."""
    needs: list[dict[str, Any]] = []
    for path in _list_need_files():
        try:
            need = read_record(path)
        except Exception:
            continue
        if status_filter:
            lifecycle = need.get("lifecycle", {})
            if lifecycle.get("status") != status_filter:
                continue
        needs.append(need)
    return needs


def show_need(need_id: str) -> dict[str, Any]:
    """Show a single need by id (supports prefix match)."""
    need = _read_need_record(need_id)
    if need is None:
        # try prefix match
        for path in _list_need_files():
            if path.stem.startswith(need_id):
                need = read_record(path)
                break
    if need is None:
        raise SystemExit(f"Need not found: {need_id!r}")
    return need


def list_pending_needs() -> list[dict[str, Any]]:
    """List all needs with lifecycle.status=pending — for platform polling."""
    return list_needs(status_filter="pending")


def read_fulfillment(need_id: str) -> dict[str, Any] | None:
    """Read the fulfillment record for a need, if it exists."""
    return _read_fulfillment(need_id)


def check_outbox() -> tuple[bool, list[str]]:
    """Check outbox consistency: all need files valid, fulfillments reference real needs."""
    messages: list[str] = []
    ok = True

    need_ids: set[str] = set()
    for path in _list_need_files():
        try:
            need = read_record(path)
        except Exception as exc:
            messages.append(f"unreadable need file {path.name}: {exc}")
            ok = False
            continue
        need_id = need.get("id", "")
        if not need_id:
            messages.append(f"need file {path.name} missing id")
            ok = False
            continue
        need_ids.add(need_id)
        if need.get("schema") != NEED_SCHEMA_ID:
            messages.append(f"need {need_id} has wrong schema: {need.get('schema')}")
            ok = False
        lifecycle = need.get("lifecycle", {})
        status = lifecycle.get("status", "")
        if status not in VALID_LIFECYCLE_STATUSES:
            messages.append(f"need {need_id} has invalid lifecycle status: {status}")
            ok = False

    for path in _list_fulfillment_files():
        try:
            fulfillment = read_record(path)
        except Exception as exc:
            messages.append(f"unreadable fulfillment file {path.name}: {exc}")
            ok = False
            continue
        ref_id = fulfillment.get("need_id", "")
        if ref_id and ref_id not in need_ids:
            messages.append(f"fulfillment {path.name} references unknown need: {ref_id}")
            ok = False

    if ok and not messages:
        if not need_ids:
            messages.append("outbox empty (no needs written yet)")
        else:
            messages.append(f"outbox ok ({len(need_ids)} needs, {len(list(_list_fulfillment_files()))} fulfillments)")
    return ok, messages


# ── JSON renderers ───────────────────────────────────────────────

def render_templates_json() -> str:
    return json.dumps(list_need_templates(), ensure_ascii=False, indent=2)


def render_template_json(template_id: str) -> str:
    return json.dumps(show_need_template(template_id), ensure_ascii=False, indent=2)


def render_platforms_json() -> str:
    return json.dumps(list_capability_cards(), ensure_ascii=False, indent=2)


def render_platform_json(platform_id: str) -> str:
    return json.dumps(show_capability_card(platform_id), ensure_ascii=False, indent=2)


def render_needs_json(status_filter: str | None = None) -> str:
    return json.dumps(list_needs(status_filter), ensure_ascii=False, indent=2)


def render_need_json(need_id: str) -> str:
    return json.dumps(show_need(need_id), ensure_ascii=False, indent=2)


def render_fulfillment_json(need_id: str) -> str:
    fulfillment = read_fulfillment(need_id)
    if fulfillment is None:
        raise SystemExit(f"No fulfillment found for need: {need_id!r}")
    return json.dumps(fulfillment, ensure_ascii=False, indent=2)
