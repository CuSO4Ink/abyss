from __future__ import annotations

import json
from typing import Any

from .audit import append_event
from .changeset import set_changeset_status
from .utils import list_records, new_id, now_iso, read_record, resolve_record_arg, runtime_root, write_record

OWNER_ITEMS_DIR = runtime_root() / "process" / "owner_inbox"

OPEN_STATUSES = {"pending"}


def _owner_item_path(item_id: str):
    return OWNER_ITEMS_DIR / f"{item_id}.yaml"


def create_owner_item(*, item_type: str, target_id: str, workflow_id: str, title: str, details: dict[str, Any]) -> dict[str, Any]:
    for item in list_owner_items(include_closed=False):
        if item.get("type") == item_type and item.get("target_id") == target_id and item.get("workflow_id") == workflow_id:
            return item
    item = {
        "schema": "abyss.owner_inbox_item.v1",
        "id": new_id("owner"),
        "type": item_type,
        "target_id": target_id,
        "workflow_id": workflow_id,
        "title": title,
        "details": details,
        "status": "pending",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    write_record(_owner_item_path(str(item["id"])), item)
    append_event("owner.inbox.created", title, {"owner_item_id": item["id"], "type": item_type, "target_id": target_id, "workflow_id": workflow_id})
    return item


def list_owner_items(*, include_closed: bool = False) -> list[dict[str, Any]]:
    items = [read_record(path) for path in list_records(OWNER_ITEMS_DIR, "owner")]
    if not include_closed:
        items = [item for item in items if item.get("status") in OPEN_STATUSES]
    return items


def resolve_owner_item(value: str):
    return resolve_record_arg(OWNER_ITEMS_DIR, value, "owner")


def load_owner_item(value: str) -> dict[str, Any]:
    return read_record(resolve_owner_item(value))


def approve_owner_item(value: str, *, continue_workflow: bool = True, provider: str | None = None) -> dict[str, Any]:
    path = resolve_owner_item(value)
    item = read_record(path)
    if item.get("status") != "pending":
        raise SystemExit(f"Owner item is not pending: {item.get('status')}")
    if item.get("type") != "changeset_approval":
        raise SystemExit(f"Unsupported owner item type: {item.get('type')}")

    changeset = set_changeset_status(str(item.get("target_id")), "approved")
    item["status"] = "approved"
    item["approved_at"] = now_iso()
    item["updated_at"] = now_iso()
    item["approved_changeset_id"] = changeset.get("id")
    write_record(path, item)
    append_event("owner.inbox.approved", str(item.get("title") or item.get("id")), {"owner_item_id": item.get("id"), "target_id": item.get("target_id")})

    from .workflow import mark_workflow_owner_approved, workflow_run_until_wait

    workflow = mark_workflow_owner_approved(str(item.get("workflow_id")), str(item.get("id")))
    item["workflow_status_after_approval"] = workflow.get("status")
    write_record(path, item)
    if continue_workflow:
        item["continuation"] = workflow_run_until_wait(provider=provider, workflow_id=str(workflow.get("id")))
        item["updated_at"] = now_iso()
        write_record(path, item)
    return item


def reject_owner_item(value: str, *, reason: str = "") -> dict[str, Any]:
    path = resolve_owner_item(value)
    item = read_record(path)
    if item.get("status") != "pending":
        raise SystemExit(f"Owner item is not pending: {item.get('status')}")
    if item.get("type") == "changeset_approval":
        set_changeset_status(str(item.get("target_id")), "rejected", reason=reason)
    item["status"] = "rejected"
    item["rejected_at"] = now_iso()
    item["rejection_reason"] = reason
    item["updated_at"] = now_iso()
    write_record(path, item)
    from .workflow import mark_workflow_owner_rejected

    mark_workflow_owner_rejected(str(item.get("workflow_id")), str(item.get("id")), reason=reason)
    append_event("owner.inbox.rejected", str(item.get("title") or item.get("id")), {"owner_item_id": item.get("id"), "target_id": item.get("target_id"), "reason": reason})
    return item


def render_owner_item(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, indent=2)
