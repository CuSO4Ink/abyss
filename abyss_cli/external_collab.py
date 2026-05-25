from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import new_id, now_iso, repo_root, runtime_root, write_record

EXTERNAL_RESULTS_DIR = runtime_root() / "process" / "external_results"
FEEDBACK_CARDS_DIR = runtime_root() / "process" / "feedback_cards"

EXPECTED_SECTIONS = [
    "task understanding",
    "modules touched",
    "files touched",
    "proposed changes",
    "candidate changeset / code approach",
    "validation",
    "risk assessment",
    "architecture alignment",
    "open questions",
    "whether brain agent / owner decision is needed",
    "recommended next step",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _section_key(title: str) -> str:
    key = title.strip().lower()
    key = re.sub(r"^\d+[.)]\s*", "", key)
    return key


def _extract_markdown_sections(text: str) -> dict[str, str]:
    """Best-effort extraction of markdown heading sections from external output."""
    matches = list(re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = _section_key(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def create_external_feedback_card(source: Path, *, task_id: str = "", source_platform: str = "external_model") -> dict[str, Any]:
    """Store an external model result as candidate feedback for governed intake.

    The feedback card is an intake artifact only. It does not create proposals,
    approve work, mutate files, execute commands, or change workflow state.
    """
    source = source.resolve()
    if not source.exists():
        raise SystemExit(f"External result file not found: {source}")

    text = _read_text(source)
    sections = _extract_markdown_sections(text)
    missing_sections = [name for name in EXPECTED_SECTIONS if name not in sections]
    card_id = new_id("fbcard")
    result_id = new_id("ext_result")

    EXTERNAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_CARDS_DIR.mkdir(parents=True, exist_ok=True)

    stored_result_path = EXTERNAL_RESULTS_DIR / f"{result_id}.md"
    stored_result_path.write_text(text, encoding="utf-8")

    card = {
        "schema": "abyss.external_work_feedback_card.v1",
        "id": card_id,
        "task_id": task_id,
        "source_platform": source_platform,
        "source_path": source.as_posix(),
        "stored_result_path": stored_result_path.as_posix(),
        "created_at": now_iso(),
        "candidate_material_only": True,
        "no_action_executed": True,
        "does_not_create_proposal": True,
        "does_not_approve_or_apply": True,
        "sections_detected": sorted(sections.keys()),
        "missing_expected_sections": missing_sections,
        "content_length": len(text),
        "sections": sections,
        "recommended_intake_path": [
            "Brain Agent or human reviews this feedback card",
            "If useful, create an Abyss evolution request/proposal through governed commands",
            "Approved work enters workflow, changeset validation, Harness review, Owner approval, executor apply, and report",
        ],
    }
    write_record(FEEDBACK_CARDS_DIR / f"{card_id}.yaml", card)
    append_event("external.feedback_card.created", "Imported external model result as candidate feedback card", {
        "feedback_card_id": card_id,
        "external_result_id": result_id,
        "source_platform": source_platform,
        "missing_expected_sections": missing_sections,
        "path": (FEEDBACK_CARDS_DIR / f"{card_id}.yaml").as_posix(),
    })
    return card


def render_feedback_card_summary(card: dict[str, Any]) -> str:
    rel_path = Path(card.get("stored_result_path", ""))
    try:
        result_display = rel_path.resolve().relative_to(repo_root().resolve()).as_posix()
    except Exception:
        result_display = str(rel_path)
    lines = [
        f"feedback_card={card.get('id')}",
        f"schema={card.get('schema')}",
        f"source_platform={card.get('source_platform')}",
        f"candidate_material_only={card.get('candidate_material_only')}",
        f"no_action_executed={card.get('no_action_executed')}",
        f"stored_result={result_display}",
        f"sections_detected={len(card.get('sections_detected') or [])}",
        f"missing_expected_sections={len(card.get('missing_expected_sections') or [])}",
    ]
    return "\n".join(lines)
