from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import ensure_dir, now_iso, runtime_root

AUDIT_FILE = runtime_root() / "audit" / "audit.md"


def append_event(event_type: str, summary: str, fields: dict[str, Any] | None = None) -> None:
    ensure_dir(AUDIT_FILE.parent)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.write_text("# Abyss Audit Log\n\n", encoding="utf-8")

    fields = fields or {}
    lines = [
        "",
        f"## {now_iso()} — {event_type}",
        "",
        f"- summary: {summary}",
    ]
    for key, value in fields.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
