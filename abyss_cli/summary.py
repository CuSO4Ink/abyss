from __future__ import annotations

import json
from typing import Any

from .changeset import list_changesets
from .integrity import run_checks
from .owner import list_owner_items
from .workflow import list_workflows


def build_summary(*, include_check: bool = False) -> dict[str, Any]:
    workflows = list_workflows()
    owner_items = list_owner_items(include_closed=False)
    changesets = list_changesets()
    active_workflows = [item for item in workflows if item.get("status") not in {"done", "failed", "blocked", "rejected"}]
    failed_workflows = [item for item in workflows if item.get("status") in {"failed", "blocked"}]
    summary: dict[str, Any] = {
        "schema": "abyss.summary.v1",
        "active_workflows": [
            {
                "id": item.get("id"),
                "roadmap_id": item.get("roadmap_id"),
                "proposal_id": item.get("proposal_id"),
                "status": item.get("status"),
                "summary": item.get("summary"),
                "owner_item_id": item.get("owner_item_id"),
            }
            for item in active_workflows
        ],
        "pending_owner_items": [
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "target_id": item.get("target_id"),
                "workflow_id": item.get("workflow_id"),
                "title": item.get("title"),
            }
            for item in owner_items
        ],
        "failed_or_blocked_workflows": [
            {
                "id": item.get("id"),
                "roadmap_id": item.get("roadmap_id"),
                "status": item.get("status"),
                "last_error": item.get("last_error"),
            }
            for item in failed_workflows
        ],
        "changesets": {
            "total": len(changesets),
            "proposed": len([item for item in changesets if item.get("status") == "proposed"]),
            "approved": len([item for item in changesets if item.get("status") == "approved"]),
            "applied": len([item for item in changesets if item.get("status") == "applied"]),
            "invalid": len([item for item in changesets if item.get("status") == "invalid"]),
        },
    }
    if include_check:
        ok, messages = run_checks()
        summary["integrity"] = {"ok": ok, "messages": messages}
    return summary


def render_summary(*, include_check: bool = False) -> str:
    return json.dumps(build_summary(include_check=include_check), ensure_ascii=False, indent=2)
