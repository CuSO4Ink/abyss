from __future__ import annotations

import time
from typing import Any

from .audit import append_event
from .integrity import run_checks
from .utils import ensure_dir, new_id, now_iso, runtime_root, write_record

FSM_DIR = runtime_root() / "fsm"
FSM_STATE_PATH = FSM_DIR / "state.yaml"
FSM_TICKS_DIR = FSM_DIR / "ticks"

DEFAULT_INTERVAL_SECONDS = 300
MIN_INTERVAL_SECONDS = 30


FSM_TRANSITIONS: dict[str, dict[str, str]] = {
    "unknown": {"tick": "checking"},
    "idle": {"tick": "checking"},
    "checking": {"ok": "idle", "fail": "needs_attention"},
    "needs_attention": {"tick": "checking", "ack": "idle"},
}


def _transition(state: str, event: str) -> str:
    return FSM_TRANSITIONS.get(state, {}).get(event, state)


def _read_state() -> dict[str, Any]:
    if not FSM_STATE_PATH.exists():
        return {
            "schema": "abyss.fsm_state.v1",
            "state": "unknown",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "last_tick_id": None,
            "last_ok": None,
            "last_messages": [],
        }
    from .utils import read_record

    return read_record(FSM_STATE_PATH)


def fsm_tick(reason: str = "manual") -> dict[str, Any]:
    ensure_dir(FSM_TICKS_DIR)
    state = _read_state()
    before = str(state.get("state", "unknown"))
    checking_state = _transition(before, "tick")
    ok, messages = run_checks()
    after = _transition(checking_state, "ok" if ok else "fail")
    tick_id = new_id("fsm_tick")
    tick = {
        "schema": "abyss.fsm_tick.v1",
        "id": tick_id,
        "created_at": now_iso(),
        "reason": reason,
        "state_before": before,
        "state_after": after,
        "integrity_ok": ok,
        "messages": messages,
    }
    write_record(FSM_TICKS_DIR / f"{tick_id}.yaml", tick)
    state.update(
        {
            "schema": "abyss.fsm_state.v1",
            "state": after,
            "updated_at": now_iso(),
            "last_tick_id": tick_id,
            "last_ok": ok,
            "last_messages": messages,
        }
    )
    write_record(FSM_STATE_PATH, state)
    append_event("fsm.tick", "FSM tick completed", {"tick_id": tick_id, "state": after, "ok": ok, "reason": reason})
    return tick


def fsm_watch(interval_seconds: int = DEFAULT_INTERVAL_SECONDS, once: bool = False) -> None:
    interval = max(MIN_INTERVAL_SECONDS, int(interval_seconds))
    while True:
        tick = fsm_tick(reason="watch")
        print(f"{tick['created_at']} {tick['id']} state={tick['state_after']} ok={tick['integrity_ok']}")
        for message in tick.get("messages", []):
            print(f"- {message}")
        if once:
            return
        time.sleep(interval)
