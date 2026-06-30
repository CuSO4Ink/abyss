from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import append_event
from .disclosure import audit_context_manifest
from .integrity import run_checks
from .summary import build_summary
from .utils import list_records, new_id, now_iso, read_record, repo_root, runtime_root, write_record, ensure_dir


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


def _build_direction_alignment() -> dict[str, Any]:
    """Deterministic, read-only direction-alignment view over Memory v0 records."""
    from .memory import list_memory_records

    records = list_memory_records()
    directions: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        provenance = record.get("provenance", {}) if isinstance(record.get("provenance"), dict) else {}
        compact = {
            "id": record.get("id"),
            "title": record.get("title"),
            "created_at": provenance.get("created_at"),
            "tags": record.get("tags", []),
            "related": record.get("related", []),
        }
        if record.get("kind") == "direction":
            directions.append(compact)
        elif record.get("kind") == "decision":
            decisions.append(compact)

    directions.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    decisions.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)

    consistency_notes: list[str] = []
    if not directions and not decisions:
        consistency_notes.append("No direction/decision memory recorded yet; Brain has no direction layer to align against.")
    else:
        if not directions:
            consistency_notes.append("Decisions exist but no explicit direction recorded; consider recording the governing direction.")
        if not decisions:
            consistency_notes.append("Directions exist but no decisions recorded yet.")
        consistency_notes.append(
            f"Read {len(directions)} direction record(s) and {len(decisions)} decision record(s) from the Memory layer."
        )

    return {
        "schema": "abyss.direction_alignment_view.v1",
        "mode": "read_only",
        "no_llm_used": True,
        "no_action_executed": True,
        "direction_count": len(directions),
        "decision_count": len(decisions),
        "recent_directions": directions[:10],
        "recent_decisions": decisions[:10],
        "consistency_notes": consistency_notes,
        "boundary": "Deterministic direction-alignment view; candidate cognition only.",
    }


def build_brain_brief() -> dict[str, Any]:
    """Build a read-only Brain Agent v0 status brief."""
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
    reliability = summary.get("self_iteration_reliability_metrics", {})
    failure_probes = summary.get("failure_probe_candidates", {})
    taxonomy = summary.get("failure_taxonomy", {})
    schema_registry = summary.get("schema_registry", {})
    smoke_fixtures = summary.get("smoke_fixture_manifest", {})

    if disclosure_audit.get("warnings"):
        next_candidates.append("Review disclosure audit warnings and reduce over-disclosure before dynamic expansion.")
    next_candidates.append("Stabilize the self-iteration substrate: keep failure taxonomy, summary, insight, and Brain brief classification language aligned.")
    next_candidates.append("Add reliability metric windows so post-R080/R084 behavior can be compared with all-time historical failures.")
    next_candidates.append("Materialize inactive failure-probe candidates into reviewable probe files without enabling them as required gates.")
    next_candidates.append("Connect context_recovery_packet to a bounded recovery runner that can prepare one retry candidate without applying or approving it.")
    next_candidates.append("Prepare Brain Agent readonly coordination interfaces only after the observation/recovery substrate remains stable.")

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
        "stabilization_context": {
            "failure_taxonomy_schema": taxonomy.get("schema"),
            "schema_registry_entry_count": schema_registry.get("entry_count"),
            "runtime_only_schema_count": (schema_registry.get("diagnostics") or {}).get("runtime_only_schema_count"),
            "smoke_fixture_count": smoke_fixtures.get("fixture_count"),
            "failure_probe_candidate_count": failure_probes.get("candidate_count"),
            "reliability_metric_names": sorted((reliability.get("metrics") or {}).keys()) if isinstance(reliability.get("metrics"), dict) else [],
            "reliability_windows": sorted((reliability.get("windows") or {}).keys()) if isinstance(reliability.get("windows"), dict) else [],
            "brain_remains_read_only": True,
        },
        "direction_alignment": _build_direction_alignment(),
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
    lines.append("Direction alignment (Memory layer, deterministic, no LLM):")
    alignment = brief.get("direction_alignment") or {}
    lines.append(f"- directions={alignment.get('direction_count', 0)} decisions={alignment.get('decision_count', 0)}")
    for record in (alignment.get("recent_directions") or [])[:5]:
        lines.append(f"  [direction] {record.get('id')} {record.get('title')}")
    for record in (alignment.get("recent_decisions") or [])[:5]:
        lines.append(f"  [decision] {record.get('id')} {record.get('title')}")
    for note in alignment.get("consistency_notes") or []:
        lines.append(f"  note: {note}")
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


# -- Brain Agent v1: Coordinator functions (R091) --

def _read_fsm_state() -> dict[str, Any]:
    """Read current FSM state for Brain context inclusion."""
    from .fsm import FSM_STATE_PATH, FSM_TICKS_DIR
    from .utils import read_record, list_records

    if not FSM_STATE_PATH.exists():
        return {"available": False, "state": "unknown", "note": "FSM has not been ticked yet."}
    try:
        state = read_record(FSM_STATE_PATH)
        # Get last tick summary
        last_tick_summary = None
        ticks = list_records(FSM_TICKS_DIR, "fsm_tick")
        if ticks:
            last_tick = read_record(ticks[-1])
            last_tick_summary = {
                "tick_id": last_tick.get("id"),
                "created_at": last_tick.get("created_at"),
                "reason": last_tick.get("reason"),
                "state_before": last_tick.get("state_before"),
                "state_after": last_tick.get("state_after"),
                "integrity_ok": last_tick.get("integrity_ok"),
            }
        return {
            "available": True,
            "state": state.get("state", "unknown"),
            "last_tick_id": state.get("last_tick_id"),
            "last_ok": state.get("last_ok"),
            "updated_at": state.get("updated_at"),
            "last_tick": last_tick_summary,
        }
    except Exception as exc:
        return {"available": False, "state": "unknown", "error": str(exc)}


def _build_cli_commands_summary() -> list[dict[str, Any]]:
    """Extract a compact CLI command summary from the argparse parser.

    This gives Brain Agent awareness of available commands without
    having to execute anything — purely deterministic, read-only.
    """
    try:
        from .__main__ import build_parser
        parser = build_parser()
        commands: list[dict[str, Any]] = []
        for action in parser._actions:
            if isinstance(action, type(parser._subparsers._group_actions[0]) if hasattr(parser, '_subparsers') else type(None)):
                continue
        # Walk subparsers to extract command tree
        for sub_action in parser._subparsers._group_actions:
            if not hasattr(sub_action, 'choices') or not sub_action.choices:
                continue
            for cmd_name, sub_parser in sub_action.choices.items():
                sub_commands: list[str] = []
                for sub_sub_action in getattr(sub_parser, '_subparsers', None) and sub_parser._subparsers._group_actions or []:
                    if hasattr(sub_sub_action, 'choices') and sub_sub_action.choices:
                        sub_commands.extend(sub_sub_action.choices.keys())
                commands.append({
                    "command": cmd_name,
                    "subcommands": sorted(sub_commands) if sub_commands else [],
                })
        return commands
    except Exception:
        return []


def build_brain_context() -> dict[str, Any]:
    """Assemble a compact system-understanding snapshot for Brain Agent v1."""
    from .external_adapter import list_needs, list_pending_needs, read_fulfillment

    ok, integrity_messages = run_checks()
    summary = build_summary(include_check=False)
    alignment = _build_direction_alignment()
    health = summary.get("operations_health_counts", {})
    fsm_state = _read_fsm_state()
    cli_commands = _build_cli_commands_summary()

    needs = list_needs()
    pending = list_pending_needs()
    fulfilled_summaries: list[dict[str, Any]] = []
    for need in needs:
        lc = need.get("lifecycle", {})
        if lc.get("status") == "fulfilled":
            fulfillment = read_fulfillment(need.get("id", ""))
            if fulfillment:
                fulfilled_summaries.append({
                    "need_id": need.get("id"),
                    "need_type": need.get("type"),
                    "fulfilled_by": fulfillment.get("fulfilled_by"),
                    "fulfilled_at": fulfillment.get("fulfilled_at"),
                    "result_summary": str(fulfillment.get("result", ""))[:200],
                })

    try:
        from .roadmap_current import render_roadmap_current_json
        roadmap_json = render_roadmap_current_json()
        roadmap = json.loads(roadmap_json) if isinstance(roadmap_json, str) else roadmap_json
    except Exception:
        roadmap = {"error": "roadmap unavailable"}

    assessment: list[str] = []
    if not ok:
        assessment.append("Integrity check failed; Brain should write a notify need for the Owner.")
    if health.get("true_failures", 0) > 0:
        assessment.append(f"{health.get('true_failures', 0)} true failure(s) detected; consider investigation.")
    if health.get("true_blocked", 0) > 0:
        assessment.append(f"{health.get('true_blocked', 0)} blocked workflow(s); consider Owner notification or evolution proposal.")
    if health.get("pending_owner_items", 0) > 0:
        assessment.append(f"{health.get('pending_owner_items', 0)} pending Owner item(s); Owner action required.")
    if len(pending) > 0:
        assessment.append(f"{len(pending)} pending need(s) in outbox; awaiting external fulfillment.")
    if len(fulfilled_summaries) > 0:
        assessment.append(f"{len(fulfilled_summaries)} fulfilled need(s); Brain should run intake to integrate results.")
    if fsm_state.get("state") == "needs_attention":
        assessment.append("FSM is in needs_attention state; integrity issue requires Owner acknowledgment.")
    if not assessment:
        assessment.append("System stable; no immediate coordinator action needed.")

    return {
        "schema": "abyss.brain_context.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "read_only_coordinator",
        "no_llm_used": True,
        "no_action_executed": True,
        "no_approval_granted": True,
        "integrity": {"ok": ok, "messages": integrity_messages},
        "fsm_state": fsm_state,
        "system_health": health,
        "direction_alignment": {
            "direction_count": alignment.get("direction_count", 0),
            "decision_count": alignment.get("decision_count", 0),
            "recent_directions": (alignment.get("recent_directions") or [])[:3],
            "recent_decisions": (alignment.get("recent_decisions") or [])[:3],
            "consistency_notes": alignment.get("consistency_notes", []),
        },
        "outbox_state": {
            "total_needs": len(needs),
            "pending": len(pending),
            "fulfilled": len(fulfilled_summaries),
            "fulfilled_summaries": fulfilled_summaries[:10],
        },
        "cli_commands": cli_commands,
        "roadmap_window": roadmap,
        "assessment": assessment,
        "boundary": "Brain context is a read-only coordinator snapshot; no execution, no approval, no mutation.",
    }


def render_brain_context_json() -> str:
    return json.dumps(build_brain_context(), ensure_ascii=False, indent=2)


def _evaluate_triggers(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate trigger conditions from the registry against current system state."""
    from .external_adapter import _load_registry

    registry = _load_registry()
    templates = registry.get("need_templates", {})
    integrity_ok = context.get("integrity", {}).get("ok", True)
    health = context.get("system_health", {})

    fired: list[dict[str, Any]] = []

    if not integrity_ok:
        tmpl = templates.get("notify_owner_on_integrity_failure", {})
        if tmpl:
            fired.append({
                "template_id": "notify_owner_on_integrity_failure",
                "need_type": tmpl.get("type", "notify"),
                "trigger_reason": "integrity check failed",
                "payload": {
                    "event_type": "integrity_failure",
                    "severity": "high",
                    "summary": "Abyss integrity check failed; Owner review required.",
                    "failed_checks": context.get("integrity", {}).get("messages", []),
                },
            })

    if health.get("true_blocked", 0) > 0:
        tmpl = templates.get("notify_owner_on_workflow_blocked", {})
        if tmpl:
            fired.append({
                "template_id": "notify_owner_on_workflow_blocked",
                "need_type": tmpl.get("type", "notify"),
                "trigger_reason": f"{health.get('true_blocked', 0)} workflow(s) blocked",
                "payload": {
                    "workflow_id": "",
                    "block_reason": "unknown",
                    "blocked_stage": "",
                },
            })

    # FSM needs_attention trigger
    fsm_state = context.get("fsm_state", {})
    if fsm_state.get("state") == "needs_attention":
        tmpl = templates.get("notify_owner_on_integrity_failure", {})
        if tmpl:
            fired.append({
                "template_id": "notify_owner_on_fsm_needs_attention",
                "need_type": tmpl.get("type", "notify"),
                "trigger_reason": "FSM is in needs_attention state",
                "payload": {
                    "event_type": "fsm_needs_attention",
                    "severity": "medium",
                    "summary": "FSM transitioned to needs_attention; integrity issue may require Owner acknowledgment.",
                    "fsm_state": fsm_state.get("state"),
                    "last_ok": fsm_state.get("last_ok"),
                    "updated_at": fsm_state.get("updated_at"),
                },
            })

    return fired


def brain_tick() -> dict[str, Any]:
    """Evaluate system state and write needs to the outbox when triggers fire."""
    from .external_adapter import write_need as adapter_write_need
    from .external_adapter import list_pending_needs

    context = build_brain_context()
    fired = _evaluate_triggers(context)
    needs_written: list[dict[str, Any]] = []
    needs_skipped: list[dict[str, Any]] = []

    existing_pending = list_pending_needs()
    existing_types = {n.get("type", "") for n in existing_pending}

    for trigger in fired:
        if trigger["need_type"] in existing_types:
            needs_skipped.append({
                "template_id": trigger["template_id"],
                "reason": "pending need of same type already exists",
            })
            continue
        need = adapter_write_need(
            trigger["need_type"],
            trigger["payload"],
            created_by="brain_tick",
            template_id=trigger["template_id"],
        )
        needs_written.append({
            "need_id": need.get("id"),
            "type": need.get("type"),
            "template_id": trigger["template_id"],
            "trigger_reason": trigger["trigger_reason"],
        })

    append_event("brain.tick", f"Brain tick: {len(fired)} trigger(s) fired, {len(needs_written)} need(s) written", {
        "triggers_fired": len(fired),
        "needs_written": len(needs_written),
        "needs_skipped": len(needs_skipped),
    })

    return {
        "schema": "abyss.brain_tick.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "coordinator_write_bounded",
        "no_approval_granted": True,
        "triggers_evaluated": len(fired),
        "triggers_fired": [
            {"template_id": t["template_id"], "reason": t["trigger_reason"]}
            for t in fired
        ],
        "needs_written": needs_written,
        "needs_skipped": needs_skipped,
        "boundary": "Brain may write needs to outbox only; it does not fulfill, execute, approve, or make outbound calls.",
    }


def render_brain_tick_json() -> str:
    return json.dumps(brain_tick(), ensure_ascii=False, indent=2)


def brain_intake() -> dict[str, Any]:
    """Read fulfilled needs from the outbox and produce an integration view."""
    from .external_adapter import list_needs, read_fulfillment

    needs = list_needs()
    fulfilled_items: list[dict[str, Any]] = []
    pending_items: list[dict[str, Any]] = []
    failed_items: list[dict[str, Any]] = []

    for need in needs:
        lc = need.get("lifecycle", {})
        status = lc.get("status", "")
        compact = {
            "need_id": need.get("id"),
            "type": need.get("type"),
            "created_at": lc.get("created_at"),
            "template_id": need.get("template_id", ""),
        }
        if status == "fulfilled":
            fulfillment = read_fulfillment(need.get("id", ""))
            compact["fulfilled_by"] = (fulfillment or {}).get("fulfilled_by", "")
            compact["fulfilled_at"] = (fulfillment or {}).get("fulfilled_at", "")
            result = (fulfillment or {}).get("result", "")
            compact["result_excerpt"] = str(result)[:500]
            compact["result_type"] = type(result).__name__ if result else "none"
            fulfilled_items.append(compact)
        elif status == "pending":
            pending_items.append(compact)
        elif status == "failed":
            error = lc.get("error", "")
            compact["error"] = error
            failed_items.append(compact)

    integration_notes: list[str] = []
    if fulfilled_items:
        integration_notes.append(f"{len(fulfilled_items)} fulfilled need(s) to integrate; review results and decide if memory or evolution action is warranted.")
    if pending_items:
        integration_notes.append(f"{len(pending_items)} pending need(s) still awaiting external fulfillment.")
    if failed_items:
        integration_notes.append(f"{len(failed_items)} failed need(s); consider retry or manual intervention.")
    if not integration_notes:
        integration_notes.append("Outbox empty or fully processed; no integration action needed.")

    recommendations: list[str] = []
    for item in fulfilled_items:
        if item.get("type", "").startswith("notify"):
            recommendations.append(f"Need {item['need_id']} was a notification; verify Owner received it.")
        if item.get("type", "").startswith("execute.git"):
            recommendations.append(f"Need {item['need_id']} was a git operation; verify repo state.")
        if item.get("type", "").startswith("store.kb"):
            recommendations.append(f"Need {item['need_id']} was a knowledge store; verify data persisted.")
    if not recommendations and fulfilled_items:
        recommendations.append("Review fulfilled results and consider recording relevant outcomes to Memory.")

    append_event("brain.intake", f"Brain intake: {len(fulfilled_items)} fulfilled, {len(pending_items)} pending, {len(failed_items)} failed", {
        "fulfilled_count": len(fulfilled_items),
        "pending_count": len(pending_items),
        "failed_count": len(failed_items),
    })

    return {
        "schema": "abyss.brain_intake.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "read_only_integration",
        "no_llm_used": True,
        "no_action_executed": True,
        "no_approval_granted": True,
        "fulfilled": fulfilled_items,
        "pending": pending_items,
        "failed": failed_items,
        "integration_notes": integration_notes,
        "recommendations": recommendations,
        "boundary": "Brain intake is read-only; it does not execute, approve, mutate, or make outbound calls.",
    }


def render_brain_intake_json() -> str:
    return json.dumps(brain_intake(), ensure_ascii=False, indent=2)


def brain_propose() -> dict[str, Any]:
    """Draft a candidate evolution proposal based on current system state."""
    context = build_brain_context()
    intake = brain_intake()
    assessment = context.get("assessment", [])
    integration_notes = intake.get("integration_notes", [])

    candidate_reasons: list[str] = []
    candidate_summary = ""
    candidate_details_parts: list[str] = []

    if not context.get("integrity", {}).get("ok", True):
        candidate_reasons.append("Integrity check is failing; a maintenance evolution request may be warranted.")
    if context.get("system_health", {}).get("true_blocked", 0) > 0:
        candidate_reasons.append(f"{context['system_health']['true_blocked']} blocked workflow(s) need resolution.")
    if len(intake.get("fulfilled", [])) > 0:
        candidate_reasons.append(f"{len(intake['fulfilled'])} fulfilled external need(s) may require follow-up action.")
    pending_count = context.get("outbox_state", {}).get("pending", 0)
    if pending_count > 0:
        candidate_reasons.append(f"{pending_count} pending need(s) in outbox; consider whether escalation is needed.")

    if candidate_reasons:
        candidate_summary = "Brain Agent coordinator assessment: system requires attention"
        candidate_details_parts.append("## Brain Agent v1 Coordinator Assessment")
        candidate_details_parts.append("")
        candidate_details_parts.append("### Assessment findings")
        for reason in candidate_reasons:
            candidate_details_parts.append(f"- {reason}")
        candidate_details_parts.append("")
        candidate_details_parts.append("### Full system assessment")
        for item in assessment:
            candidate_details_parts.append(f"- {item}")
        candidate_details_parts.append("")
        candidate_details_parts.append("### Integration notes")
        for note in integration_notes:
            candidate_details_parts.append(f"- {note}")
        candidate_details_parts.append("")
        candidate_details_parts.append("### Boundary")
        candidate_details_parts.append("This is a candidate proposal drafted by Brain Agent v1. It must go through the normal evolution chain: request -> proposal -> Owner approval. Brain does not approve its own proposals.")
    else:
        candidate_summary = "Brain Agent coordinator assessment: system stable, no immediate evolution needed"
        candidate_details_parts.append("System is stable. No candidate evolution proposal warranted at this time.")
        candidate_details_parts.append("")
        candidate_details_parts.append("### Assessment")
        for item in assessment:
            candidate_details_parts.append(f"- {item}")

    append_event("brain.propose", f"Brain propose: {len(candidate_reasons)} reason(s) found", {
        "candidate_reasons": len(candidate_reasons),
        "summary": candidate_summary,
    })

    return {
        "schema": "abyss.brain_propose.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "coordinator_propose_bounded",
        "no_approval_granted": True,
        "no_action_executed": True,
        "candidate_summary": candidate_summary,
        "candidate_details": "\n".join(candidate_details_parts),
        "candidate_reasons": candidate_reasons,
        "system_assessment": assessment,
        "integration_notes": integration_notes,
        "next_step": "If the Owner agrees with the candidate proposal, run: abyss evolution request '<summary>' --details '<details>' to create a formal request. Brain does not create the request automatically.",
        "boundary": "Brain propose is advisory only; it does not create evolution requests, approve items, or execute actions.",
    }


def render_brain_propose_json() -> str:
    return json.dumps(brain_propose(), ensure_ascii=False, indent=2)


# -- Brain Working Memory (R094) --

WORKING_MEMORY_DIR = runtime_root() / "memory" / "working_memory"


def save_working_memory_entry(agent_run_id: str, response_text: str, question: str | None = None) -> dict[str, Any]:
    """Persist a Brain Agent cognitive output as a working-memory entry.

    Entries are compact: a timestamp, the question (if any), and a truncated
    excerpt of the response. Full responses remain in brain_responses/ —
    working memory is the index/continuity layer, not the storage layer.
    """
    ensure_dir(WORKING_MEMORY_DIR)
    entry_id = new_id("wm")
    excerpt = response_text.strip()
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000] + "\n[...truncated for working memory...]"
    entry = {
        "schema": "abyss.brain_working_memory.v1",
        "id": entry_id,
        "agent_run_id": agent_run_id,
        "timestamp": now_iso(),
        "kind": "question_answer" if question else "periodic_assessment",
        "question": (question or "").strip() or None,
        "excerpt": excerpt,
    }
    write_record(WORKING_MEMORY_DIR / f"{entry_id}.yaml", entry)
    append_event("brain.working_memory.saved", "Saved working memory entry", {
        "entry_id": entry_id,
        "agent_run_id": agent_run_id,
        "kind": entry["kind"],
    })
    return entry


def load_working_memory(limit: int = 10) -> list[dict[str, Any]]:
    """Load recent working-memory entries for prompt injection.

    Returns entries in chronological order (oldest first, newest last) so
    the LLM sees them as a coherent timeline.
    """
    if not WORKING_MEMORY_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in list_records(WORKING_MEMORY_DIR, "wm")[-limit:]:
        try:
            entry = read_record(path)
            entries.append({
                "timestamp": entry.get("timestamp", ""),
                "kind": entry.get("kind", ""),
                "question": entry.get("question"),
                "text": entry.get("excerpt", "")[:500],  # truncate further for prompt
            })
        except Exception:
            continue
    return entries


def render_working_memory_json() -> str:
    return json.dumps(load_working_memory(limit=50), ensure_ascii=False, indent=2)
