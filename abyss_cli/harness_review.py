from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import new_id, now_iso, runtime_root, write_record

HARNESS_REVIEWS_DIR = runtime_root() / "process" / "harness_reviews"
HARNESS_REVIEW_BLOCK_RE = re.compile(r"```abyss-harness-review\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _parse_simple_yaml(block: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _normalize_verdict(value: str) -> str:
    verdict = value.strip().lower()
    return verdict if verdict in {"ok", "warning", "violation"} else "warning"


def _normalize_risk(value: str) -> str:
    risk = value.strip().upper()
    return risk if risk in {"L0", "L1", "L2", "L3", "L4", "L5"} else "L3"


def parse_harness_review(text: str, *, target_id: str | None, agent_run_id: str | None, result_path: Path) -> dict[str, Any]:
    matches = HARNESS_REVIEW_BLOCK_RE.findall(text)
    if matches:
        raw = _parse_simple_yaml(matches[0])
        verdict = _normalize_verdict(raw.get("verdict", "warning"))
        risk_level = _normalize_risk(raw.get("risk_level", "L3"))
        no_action_executed = raw.get("no_action_executed", "").strip().lower() == "true"
        findings = [
            {
                "type": raw.get("finding_1_type", "none"),
                "severity": raw.get("finding_1_severity", "info"),
                "message": raw.get("finding_1_message", ""),
            }
        ]
        review = {
            "schema": "abyss.harness_review.v1",
            "id": new_id("hrev"),
            "agent_id": "harness",
            "agent_run_id": agent_run_id,
            "target_id": target_id,
            "result_path": result_path.as_posix(),
            "verdict": verdict,
            "risk_level": risk_level,
            "summary": raw.get("summary", ""),
            "findings": findings,
            "recommendation": raw.get("recommendation", "none"),
            "no_action_executed": no_action_executed,
            "created_at": now_iso(),
        }
    else:
        review = {
            "schema": "abyss.harness_review.v1",
            "id": new_id("hrev"),
            "agent_id": "harness",
            "agent_run_id": agent_run_id,
            "target_id": target_id,
            "result_path": result_path.as_posix(),
            "verdict": "warning",
            "risk_level": "L3",
            "summary": "HarnessAgent output did not contain an abyss-harness-review block.",
            "findings": [
                {
                    "type": "output_contract_violation",
                    "severity": "warning",
                    "message": "Missing required fenced abyss-harness-review block.",
                }
            ],
            "recommendation": "require_human_review",
            "no_action_executed": True,
            "created_at": now_iso(),
        }

    path = HARNESS_REVIEWS_DIR / f"{review['id']}.yaml"
    write_record(path, review)
    append_event(
        "harness.review.created",
        "HarnessAgent review created",
        {
            "harness_review_id": review["id"],
            "target_id": target_id,
            "verdict": review["verdict"],
            "risk_level": review["risk_level"],
            "recommendation": review["recommendation"],
        },
    )
    return review
