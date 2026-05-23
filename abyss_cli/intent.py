from __future__ import annotations

from .audit import append_event
from .utils import new_id, now_iso, read_record, runtime_root, write_record

INTENTS_DIR = runtime_root() / "process" / "intents"


def create_intent(goal: str, mode: str = "assisted_prompt", source: str = "user") -> dict:
    intent_id = new_id("intent")
    record = {
        "schema": "abyss.intent.v1",
        "id": intent_id,
        "type": "intent",
        "title": goal[:80],
        "goal": goal,
        "source": source,
        "mode": mode,
        "status": "active",
        "scope": {
            "name": mode,
            "allowed": ["intent.create", "prompt.build", "result.import", "action.propose", "audit.append"],
            "denied": ["automatic.execute", "git.push", "outbound.message"],
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    path = INTENTS_DIR / f"{intent_id}.yaml"
    write_record(path, record)
    append_event("intent.created", goal, {"intent_id": intent_id, "path": path.as_posix()})
    return record


def load_intent(path):
    return read_record(path)
