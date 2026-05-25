from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .disclosure import audit_context_manifest
from .integrity import run_checks
from .summary import build_summary
from .utils import list_records, read_record, repo_root, runtime_root


def _safe_text_excerpt(path: Path, limit: int = 1200) -> dict[str, Any]:
    if not path.exists():
        return {"path": path.as_posix(), "exists": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": path.resolve().relative_to(repo_root().resolve()).as_posix() if path.is_relative_to(repo_root()) else path.as_posix(),
        "exists": True,
        "size": len(text),
        "excerpt": text[:limit],
        "truncated": len(text) > limit,
    }


def _load_recent_feedback_cards(limit: int = 5) -> list[dict[str, Any]]:
    directory = runtime_root() / "process" / "feedback_cards"
    cards: list[dict[str, Any]] = []
    for path in list_records(directory, "fbcard")[-limit:]:
        try:
            card = read_record(path)
        except Exception as exc:
            cards.append({"path": path.as_posix(), "error": str(exc)})
            continue
        cards.append({
            "id": card.get("id"),
            "task_id": card.get("task_id"),
            "source_platform": card.get("source_platform"),
            "created_at": card.get("created_at"),
            "candidate_material_only": card.get("candidate_material_only"),
            "no_action_executed": card.get("no_action_executed"),
            "missing_expected_sections": card.get("missing_expected_sections", []),
            "sections_detected_count": len(card.get("sections_detected") or []),
            "stored_result_path": card.get("stored_result_path"),
        })
    return cards


def _load_recent_reports(limit: int = 5) -> list[dict[str, Any]]:
    directory = runtime_root() / "process" / "reports"
    reports: list[dict[str, Any]] = []
    for path in list_records(directory, "report")[-limit:]:
        try:
            report = read_record(path)
        except Exception as exc:
            reports.append({"path": path.as_posix(), "error": str(exc)})
            continue
        reports.append({
            "id": report.get("id"),
            "workflow_id": report.get("workflow_id"),
            "roadmap_id": report.get("roadmap_id"),
            "status": report.get("status"),
            "changeset_id": report.get("changeset_id"),
            "created_at": report.get("created_at"),
        })
    return reports


def build_brain_brief() -> dict[str, Any]:
    """Build a read-only Brain Agent v0 status brief.

    This command is intentionally side-effect-free: it does not execute,
    approve, mutate files, create workflows, or schedule work.
    """
    root = repo_root()
    ok, messages = run_checks()
    summary = build_summary(include_check=False)
    disclosure_audit = audit_context_manifest()

    operations_counts = summary.get("operations_health_counts", {})
    phase = "stable_read_only_cognition_base" if ok and operations_counts.get("active_workflows", 0) == 0 else "needs_attention"

    next_candidates: list[str] = []
    owner_decisions_needed: list[str] = []
    not_recommended: list[str] = [
        "Do not enable Brain Agent execution or approval authority in v0.",
        "Do not replace Owner or Harness decisions with model output.",
        "Do not convert context_manifest to a full dynamic engine in one step.",
    ]

    if not ok:
        owner_decisions_needed.append("Review integrity failures before expanding Brain Agent behavior.")
    if disclosure_audit.get("warnings"):
        next_candidates.append("Review disclosure audit warnings and reduce over-disclosure before dynamic expansion.")
    else:
        next_candidates.append("Proceed with cautious disclosure planner integration after disclosure_plan.v1 schema validation is stable.")
    next_candidates.append("Global Direction internalization: ensure Brain brief and external packages reflect current strategic direction.")
    next_candidates.append("External model onboarding: validate EXTERNAL_MODEL_ONBOARDING.md as standalone import path for external platforms.")
    next_candidates.append("Disclosure plan schema: stabilize disclosure_plan contract and JSON Schema for context governance.")
    next_candidates.append("Implementation Agent output hardening: further constrain edit-plan/ChangeSet generation within R003 scope.")
    next_candidates.append("Keep Brain Agent as disabled/read-only while iterating brief quality and feedback-card summaries.")

    return {
        "schema": "abyss.brain_brief.v1",
        "mode": "read_only",
        "no_action_executed": True,
        "no_approval_granted": True,
        "no_files_modified_by_command": True,
        "phase": phase,
        "entrypoint": _safe_text_excerpt(root / "ABYSS.md", limit=800),
        "cognition_protocol": {
            "path": "rules/architecture_cognition.yaml",
            "exists": (root / "rules" / "architecture_cognition.yaml").exists(),
        },
        "integrity": {"ok": ok, "messages": messages},
        "summary": summary,
        "disclosure_audit": {
            "ok": disclosure_audit.get("ok"),
            "warnings": disclosure_audit.get("warnings", []),
            "task_count": len(disclosure_audit.get("tasks") or []),
        },
        "recent_feedback_cards": _load_recent_feedback_cards(),
        "recent_reports": _load_recent_reports(),
        "next_candidates": next_candidates,
        "owner_decisions_needed": owner_decisions_needed,
        "not_recommended": not_recommended,
        "hard_boundary": "Brain Agent v0 may explain and propose next steps only; it must not approve, execute, mutate files, bypass Harness, or replace Owner.",
    }


def render_brain_brief(*, as_json: bool = False) -> str:
    brief = build_brain_brief()
    if as_json:
        return json.dumps(brief, ensure_ascii=False, indent=2)

    counts = brief.get("summary", {}).get("operations_health_counts", {})
    lines = [
        "Brain Agent v0 Read-only Brief",
        "================================",
        f"mode: {brief.get('mode')}",
        f"phase: {brief.get('phase')}",
        f"integrity_ok: {brief.get('integrity', {}).get('ok')}",
        f"disclosure_audit_ok: {brief.get('disclosure_audit', {}).get('ok')}",
        f"active_workflows: {counts.get('active_workflows', 0)}",
        f"pending_owner_items: {counts.get('pending_owner_items', 0)}",
        f"true_failures: {counts.get('true_failures', 0)}",
        f"true_blocked: {counts.get('true_blocked', 0)}",
        "",
        "Boundaries:",
        f"- {brief.get('hard_boundary')}",
        "- no_action_executed=True",
        "- no_approval_granted=True",
        "",
        "Next candidates:",
    ]
    for item in brief.get("next_candidates") or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Owner decisions needed:")
    owner_items = brief.get("owner_decisions_needed") or []
    if owner_items:
        for item in owner_items:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Recent external feedback cards:")
    cards = brief.get("recent_feedback_cards") or []
    if cards:
        for card in cards:
            lines.append(f"- {card.get('id')} platform={card.get('source_platform')} missing_sections={len(card.get('missing_expected_sections') or [])}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Not recommended:")
    for item in brief.get("not_recommended") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)
