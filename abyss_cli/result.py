from __future__ import annotations

import re
from pathlib import Path

from .audit import append_event
from .policy import classify_action
from .utils import new_id, now_iso, read_record, repo_root, write_record

ACTIONS_DIR = repo_root() / "process" / "actions"
REVIEWS_DIR = repo_root() / "process" / "reviews"
IMPORTS_DIR = repo_root() / "process" / "imports"

ACTION_BLOCK_RE = re.compile(r"```abyss-action\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _parse_simple_yaml(block: str) -> dict:
    data = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def import_result(response_path: Path, intent_path: Path | None = None) -> list[dict]:
    text = response_path.read_text(encoding="utf-8")
    import_id = new_id("import")
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    imported_copy = IMPORTS_DIR / f"{import_id}.md"
    imported_copy.write_text(text, encoding="utf-8")

    intent_id = None
    if intent_path:
        intent_id = read_record(intent_path).get("id")

    proposals = []
    blocks = ACTION_BLOCK_RE.findall(text)
    for block in blocks:
        raw = _parse_simple_yaml(block)
        action_id = new_id("act")
        risk, decision, reason = classify_action(raw)
        proposal = {
            "schema": "abyss.action_proposal.v1",
            "id": action_id,
            "type": "action_proposal",
            "intent_id": intent_id,
            "source": "llm_result_import",
            "capability": raw.get("capability", "unknown"),
            "operation": raw.get("operation", "unknown"),
            "path": raw.get("path", ""),
            "reason": raw.get("reason", ""),
            "risk_estimate": raw.get("risk_estimate", risk),
            "policy": {
                "risk": risk,
                "decision": decision,
                "reason": reason,
                "decided_at": now_iso(),
            },
            "status": "proposed" if decision == "review" else decision,
            "created_at": now_iso(),
        }
        action_path = ACTIONS_DIR / f"{action_id}.yaml"
        write_record(action_path, proposal)
        append_event("action.proposed", proposal["reason"] or proposal["capability"], {"action_id": action_id, "decision": decision, "risk": risk})

        if decision == "review":
            review_id = new_id("rev")
            review = {
                "schema": "abyss.review.v1",
                "id": review_id,
                "type": "review",
                "action_id": action_id,
                "intent_id": intent_id,
                "status": "pending",
                "risk": risk,
                "reason": reason,
                "created_at": now_iso(),
                "options": ["approve_once", "reject"],
            }
            review_path = REVIEWS_DIR / f"{review_id}.yaml"
            write_record(review_path, review)
            append_event("review.created", "Action requires human review", {"review_id": review_id, "action_id": action_id, "risk": risk})
        proposals.append(proposal)

    append_event("result.imported", "Imported LLM response", {"import_id": import_id, "actions_found": len(proposals), "path": imported_copy.as_posix()})
    return proposals
