from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import append_event
from .llm_executor import LLM_RESULTS_DIR, _provider_response, load_provider_config
from .utils import latest_record, new_id, now_iso, read_record, relative_to_repo, repo_root, resolve_record_arg, runtime_root, write_record

EVOLUTION_DIR = runtime_root() / "evolution"
REQUESTS_DIR = EVOLUTION_DIR / "requests"
PROPOSALS_DIR = EVOLUTION_DIR / "proposals"
SMOKE_DIR = EVOLUTION_DIR / "smoke_tests"


REQUEST_STATES = {
    "inbox",
    "normalized",
    "proposed",
    "needs_user_decision",
    "approved",
    "planned",
    "implementing",
    "reviewing",
    "done",
    "rejected",
    "deferred",
}


def create_change_request(summary: str, details: str = "", source: str = "user") -> dict[str, Any]:
    request_id = new_id("evo_req")
    record = {
        "schema": "abyss.evolution_request.v1",
        "id": request_id,
        "type": "evolution_request",
        "summary": summary,
        "details": details,
        "source": source,
        "status": "inbox",
        "approval_status": "not_requested",
        "roadmap_entry": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "no_action_executed": True,
    }
    write_record(REQUESTS_DIR / f"{request_id}.yaml", record)
    append_event("evolution.request.created", summary, {"request_id": request_id})
    return record


def list_evolution_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(REQUESTS_DIR.glob("*.yaml")) if REQUESTS_DIR.exists() else []:
        record = read_record(path)
        records.append({
            "kind": "request",
            "id": record.get("id"),
            "status": record.get("status"),
            "summary": record.get("summary"),
            "path": relative_to_repo(path),
        })
    for path in sorted(PROPOSALS_DIR.glob("*.yaml")) if PROPOSALS_DIR.exists() else []:
        record = read_record(path)
        records.append({
            "kind": "proposal",
            "id": record.get("id"),
            "status": record.get("status"),
            "summary": record.get("title") or record.get("summary"),
            "path": relative_to_repo(path),
        })
    return records


def _resolve_request(value: str) -> Path:
    return resolve_record_arg(REQUESTS_DIR, value, "evo_req")


def _resolve_proposal(value: str) -> Path:
    return resolve_record_arg(PROPOSALS_DIR, value, "evo_prop")


def resolve_evolution_target(value: str) -> Path:
    if value == "latest":
        latest_proposal = latest_record(PROPOSALS_DIR, "evo_prop")
        if latest_proposal:
            return latest_proposal
        latest_request = latest_record(REQUESTS_DIR, "evo_req")
        if latest_request:
            return latest_request
        raise SystemExit(f"No evolution records found in {EVOLUTION_DIR}")

    for resolver in (_resolve_proposal, _resolve_request):
        try:
            return resolver(value)
        except SystemExit:
            pass
    raise SystemExit(f"Evolution record not found: {value}")


def show_evolution_record(value: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_evolution_target(value)
    return path, read_record(path)


def create_proposal_from_request(request_value: str) -> dict[str, Any]:
    request_path = _resolve_request(request_value)
    request = read_record(request_path)
    proposal_id = new_id("evo_prop")
    title = str(request.get("summary") or "Untitled evolution request")[:120]
    proposal = {
        "schema": "abyss.evolution_proposal.v1",
        "id": proposal_id,
        "type": "evolution_proposal",
        "request_id": request.get("id"),
        "title": title,
        "purpose": request.get("summary"),
        "details": request.get("details", ""),
        "status": "needs_user_decision",
        "approval_required": True,
        "approval_status": "pending",
        "implementation_allowed": False,
        "recommended_chain": [
            "record_raw_request",
            "normalize_to_proposal",
            "wait_for_user_approval",
            "add_to_approved_roadmap_only_after_approval",
            "plan_bounded_slice",
            "run_checks_and_review",
        ],
        "risk_level": "L2",
        "acceptance_checks": [
            "The request remains non-executable until explicit user approval.",
            "The proposal can be inspected independently of ROADMAP.md.",
            "No external interface is used for anything other than standard LLM invocation.",
        ],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "no_action_executed": True,
    }
    write_record(PROPOSALS_DIR / f"{proposal_id}.yaml", proposal)
    request["status"] = "proposed"
    request["updated_at"] = now_iso()
    write_record(request_path, request)
    append_event("evolution.proposal.created", title, {"proposal_id": proposal_id, "request_id": request.get("id")})
    return proposal


def build_smoke_prompt() -> tuple[Path, str]:
    prompt_id = new_id("evo_smoke_ppkg")
    body = f"""# Abyss Self-Evolution Smoke Prompt Package

- prompt_package_id: {prompt_id}
- created_at: {now_iso()}
- executor: standard_llm_provider

---

## Purpose

This is a smoke test for the Abyss standard LLM invocation interface used by the governed self-iteration chain.

## Hard constraints

- You are only a model text provider.
- Do not claim to inspect files.
- Do not claim to execute commands.
- Do not approve, reject, schedule, notify, mutate files, change Git state, or perform any side effect.
- Do not output any `abyss-action` block.

## Required output

Return a short Markdown response containing exactly this token on its own line:

SMOKE_OK

Also include one sentence explaining that no action was executed.
"""
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    path = SMOKE_DIR / f"{prompt_id}.md"
    path.write_text(body, encoding="utf-8")
    return path, body


def run_evolution_smoke(provider: str) -> dict[str, Any]:
    config = load_provider_config()
    providers = config.get("providers", {})
    provider_config = providers.get(provider)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider}")

    prompt_path, prompt_text = build_smoke_prompt()
    response_text = _provider_response(provider, provider_config, prompt_path, prompt_text)

    LLM_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    result_path.write_text(response_text, encoding="utf-8")

    passed = bool(response_text.strip()) and "SMOKE_OK" in response_text and "```abyss-action" not in response_text
    record = {
        "schema": "abyss.evolution_smoke_test.v1",
        "id": new_id("evo_smoke"),
        "provider": provider,
        "prompt_path": prompt_path.as_posix(),
        "result_path": result_path.as_posix(),
        "status": "passed" if passed else "failed",
        "checks": {
            "non_empty_response": bool(response_text.strip()),
            "contains_smoke_ok": "SMOKE_OK" in response_text,
            "no_abyss_action_block": "```abyss-action" not in response_text,
        },
        "no_action_executed": True,
        "created_at": now_iso(),
    }
    write_record(SMOKE_DIR / f"{record['id']}.yaml", record)
    append_event("evolution.smoke.completed", "Self-evolution LLM smoke test completed", {"provider": provider, "status": record["status"], "result_path": result_path.as_posix()})
    return record


def record_to_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2)
