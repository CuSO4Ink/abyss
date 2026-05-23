from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import new_id, now_iso, runtime_root, write_record

EVOLUTION_ANALYSES_DIR = runtime_root() / "process" / "evolution_analyses"
EVOLUTION_ANALYSIS_BLOCK_RE = re.compile(r"```abyss-evolution-analysis\s*(.*?)```", re.DOTALL | re.IGNORECASE)
JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)

VALID_VERDICTS = {"proposal_only", "ready_for_user_decision", "needs_user_decision", "blocked", "already_approved"}
VALID_STATES = {"inbox", "normalized", "proposed", "needs_user_decision", "approved", "planned", "deferred", "rejected"}
VALID_ROADMAP_STATUS = {"not_in_roadmap", "approved", "related_to_approved", "unknown"}


def _fallback_analysis(*, target_id: str | None, agent_run_id: str | None, result_path: Path, summary: str) -> dict[str, Any]:
    return {
        "schema": "abyss.evolution_analysis.v1",
        "id": new_id("evo_analysis"),
        "agent_id": "self_evolution",
        "agent_run_id": agent_run_id,
        "target_id": target_id,
        "result_path": result_path.as_posix(),
        "verdict": "blocked",
        "summary": summary,
        "recommended_state": "deferred",
        "roadmap_status": "unknown",
        "implementation_allowed_now": False,
        "minimal_slice": "",
        "risks": ["Self-evolution Agent output did not satisfy the required schema."],
        "acceptance_checks": [],
        "contract_valid": False,
        "contract_warnings": [summary],
        "no_action_executed": True,
        "created_at": now_iso(),
    }


def _extract_analysis_block(text: str) -> tuple[str | None, list[str]]:
    matches = EVOLUTION_ANALYSIS_BLOCK_RE.findall(text)
    if matches:
        return matches[0], []
    json_matches = JSON_BLOCK_RE.findall(text)
    for block in json_matches:
        try:
            candidate = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        if candidate.get("schema") == "abyss.evolution_analysis.v1":
            return block, ["Used json fenced block fallback because abyss-evolution-analysis fence was missing."]
    return None, []


def parse_evolution_analysis(text: str, *, target_id: str | None, agent_run_id: str | None, result_path: Path) -> dict[str, Any]:
    block, extraction_warnings = _extract_analysis_block(text)
    if block is None:
        analysis = _fallback_analysis(
            target_id=target_id,
            agent_run_id=agent_run_id,
            result_path=result_path,
            summary="Self-evolution Agent output did not contain an abyss-evolution-analysis block or compatible schema JSON block.",
        )
    else:
        warnings: list[str] = list(extraction_warnings)
        try:
            raw = json.loads(block.strip())
        except json.JSONDecodeError:
            analysis = _fallback_analysis(
                target_id=target_id,
                agent_run_id=agent_run_id,
                result_path=result_path,
                summary="Self-evolution Agent output contained invalid JSON.",
            )
        else:
            verdict = str(raw.get("verdict") or "blocked")
            if verdict not in VALID_VERDICTS:
                warnings.append(f"Invalid verdict: {verdict}")
                verdict = "blocked"

            recommended_state = str(raw.get("recommended_state") or "deferred")
            if recommended_state not in VALID_STATES:
                warnings.append(f"Invalid recommended_state: {recommended_state}")
                recommended_state = "deferred"

            roadmap_status = str(raw.get("roadmap_status") or "unknown")
            if roadmap_status not in VALID_ROADMAP_STATUS:
                warnings.append(f"Invalid roadmap_status: {roadmap_status}")
                roadmap_status = "unknown"

            implementation_allowed_now = bool(raw.get("implementation_allowed_now", False))
            if implementation_allowed_now:
                warnings.append("Self-evolution analysis is not allowed to grant implementation authority.")
                implementation_allowed_now = False

            no_action_executed = bool(raw.get("no_action_executed", False))
            if not no_action_executed:
                warnings.append("no_action_executed must be true.")

            analysis = {
                "schema": "abyss.evolution_analysis.v1",
                "id": new_id("evo_analysis"),
                "agent_id": "self_evolution",
                "agent_run_id": agent_run_id,
                "target_id": target_id,
                "result_path": result_path.as_posix(),
                "verdict": verdict,
                "summary": str(raw.get("summary") or ""),
                "recommended_state": recommended_state,
                "roadmap_status": roadmap_status,
                "implementation_allowed_now": implementation_allowed_now,
                "minimal_slice": str(raw.get("minimal_slice") or ""),
                "risks": raw.get("risks") if isinstance(raw.get("risks"), list) else [],
                "acceptance_checks": raw.get("acceptance_checks") if isinstance(raw.get("acceptance_checks"), list) else [],
                "contract_valid": not warnings,
                "contract_warnings": warnings,
                "no_action_executed": True,
                "created_at": now_iso(),
            }

    path = EVOLUTION_ANALYSES_DIR / f"{analysis['id']}.yaml"
    write_record(path, analysis)
    append_event(
        "evolution.analysis.created",
        "Self-evolution analysis created",
        {
            "analysis_id": analysis["id"],
            "target_id": target_id,
            "verdict": analysis["verdict"],
            "contract_valid": analysis["contract_valid"],
        },
    )
    return analysis
