from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .audit import append_event
from .llm_executor import LLM_RESULTS_DIR, _provider_response, load_provider_config
from .utils import latest_record, new_id, now_iso, read_record, relative_to_repo, repo_root, resolve_record_arg, runtime_root, write_record

EVOLUTION_DIR = runtime_root() / "evolution"
REQUESTS_DIR = EVOLUTION_DIR / "requests"
PROPOSALS_DIR = EVOLUTION_DIR / "proposals"
SMOKE_DIR = EVOLUTION_DIR / "smoke_tests"
GOVERNANCE_PATH = repo_root() / "rules" / "governance.yaml"
ROADMAP_PATH = repo_root() / "ROADMAP.md"


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


def load_governance_state() -> dict[str, Any]:
    if GOVERNANCE_PATH.exists():
        return read_record(GOVERNANCE_PATH)
    return {
        "schema": "abyss.governance.v1",
        "direct_modification_mode": "transitional",
        "ordinary_system_changes_require_evolution_chain": False,
        "finalized_at": None,
        "finalized_by": None,
        "notes": "Transitional direct modification remains available only for user-authorized concrete changes until finalized.",
    }


def save_governance_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema", "abyss.governance.v1")
    state["updated_at"] = now_iso()
    write_record(GOVERNANCE_PATH, state)
    return state


def governance_status() -> dict[str, Any]:
    return load_governance_state()


def _next_roadmap_id(text: str) -> str:
    existing = [int(match) for match in re.findall(r"^### R(\d+)\.", text, flags=re.MULTILINE)]
    return f"R{(max(existing) + 1) if existing else 1:03d}"


def _proposal_roadmap_section(proposal: dict[str, Any], roadmap_id: str) -> str:
    title = str(proposal.get("title") or proposal.get("purpose") or "Untitled self-evolution item").strip()
    purpose = str(proposal.get("purpose") or title).strip()
    details = str(proposal.get("details") or "Approved evolution proposal.").strip()
    risk_level = str(proposal.get("risk_level") or "L2")
    checks = proposal.get("acceptance_checks") if isinstance(proposal.get("acceptance_checks"), list) else []
    checks_text = "\n".join(f"- {check}" for check in checks) or "- Approved proposal can be implemented only through the governed evolution chain."
    return f"""### {roadmap_id}. {title}

Source proposal: `{proposal.get('id')}`.

Purpose: {purpose}

Why it is needed: {details}

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: {risk_level}.

Acceptance check:

{checks_text}

"""


def _append_proposal_to_roadmap(proposal: dict[str, Any]) -> tuple[str, str]:
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    proposal_id = str(proposal.get("id"))
    if f"Source proposal: `{proposal_id}`" in text:
        existing = re.search(rf"^### (R\d+)\..*?\n\nSource proposal: `{re.escape(proposal_id)}`", text, flags=re.MULTILINE | re.DOTALL)
        return (existing.group(1) if existing else "existing", "already_present")

    roadmap_id = _next_roadmap_id(text)
    section = _proposal_roadmap_section(proposal, roadmap_id)
    marker = "\n## Pending proposals\n"
    if marker not in text:
        raise SystemExit("ROADMAP.md does not contain the Pending proposals marker")
    text = text.replace(marker, "\n" + section + "## Pending proposals\n", 1)
    ROADMAP_PATH.write_text(text, encoding="utf-8")
    return roadmap_id, "added"


def approve_proposal(proposal_value: str, approver: str = "user", add_to_roadmap: bool = True) -> dict[str, Any]:
    proposal_path = _resolve_proposal(proposal_value)
    proposal = read_record(proposal_path)
    if proposal.get("status") == "rejected":
        raise SystemExit(f"Cannot approve rejected proposal: {proposal.get('id')}")

    roadmap_id = proposal.get("roadmap_entry")
    roadmap_status = "not_requested"
    if add_to_roadmap:
        roadmap_id, roadmap_status = _append_proposal_to_roadmap(proposal)

    proposal["status"] = "approved"
    proposal["approval_status"] = "approved"
    proposal["implementation_allowed"] = True
    proposal["approved_by"] = approver
    proposal["approved_at"] = now_iso()
    proposal["roadmap_entry"] = roadmap_id
    proposal["roadmap_status"] = roadmap_status
    proposal["updated_at"] = now_iso()
    write_record(proposal_path, proposal)

    request_id = proposal.get("request_id")
    if request_id:
        try:
            request_path = _resolve_request(str(request_id))
            request = read_record(request_path)
            request["status"] = "approved"
            request["approval_status"] = "approved"
            request["roadmap_entry"] = roadmap_id
            request["updated_at"] = now_iso()
            write_record(request_path, request)
        except SystemExit:
            pass

    append_event("evolution.proposal.approved", str(proposal.get("title") or proposal.get("id")), {"proposal_id": proposal.get("id"), "roadmap_entry": roadmap_id, "roadmap_status": roadmap_status})
    return proposal


def reject_proposal(proposal_value: str, reason: str = "") -> dict[str, Any]:
    proposal_path = _resolve_proposal(proposal_value)
    proposal = read_record(proposal_path)
    if proposal.get("status") == "approved":
        raise SystemExit(f"Cannot reject approved proposal: {proposal.get('id')}")
    proposal["status"] = "rejected"
    proposal["approval_status"] = "rejected"
    proposal["implementation_allowed"] = False
    proposal["rejected_at"] = now_iso()
    proposal["rejection_reason"] = reason
    proposal["updated_at"] = now_iso()
    write_record(proposal_path, proposal)

    request_id = proposal.get("request_id")
    if request_id:
        try:
            request_path = _resolve_request(str(request_id))
            request = read_record(request_path)
            request["status"] = "rejected"
            request["approval_status"] = "rejected"
            request["updated_at"] = now_iso()
            write_record(request_path, request)
        except SystemExit:
            pass

    append_event("evolution.proposal.rejected", str(proposal.get("title") or proposal.get("id")), {"proposal_id": proposal.get("id"), "reason": reason})
    return proposal


def finalize_direct_modification_mode(confirmed_by: str = "user") -> dict[str, Any]:
    state = load_governance_state()
    state["direct_modification_mode"] = "disabled"
    state["ordinary_system_changes_require_evolution_chain"] = True
    state["finalized_at"] = now_iso()
    state["finalized_by"] = confirmed_by
    state["notes"] = "Ordinary system changes must enter through the governed evolution request/proposal/approval/roadmap chain."
    state = save_governance_state(state)
    append_event("governance.direct_modification_mode.disabled", "Direct modification mode disabled for ordinary system changes", {"confirmed_by": confirmed_by})
    return state


def create_proposal_from_request(request_value: str) -> dict[str, Any]:
    request_path = _resolve_request(request_value)
    request = read_record(request_path)
    proposal_id = new_id("evo_prop")
    title = str(request.get("summary") or "Untitled evolution request")[:120]
    
    # Load latest self-evolution analysis if available
    analysis_summary = ""
    minimal_slice = ""
    risks = []
    roadmap_status = "not_in_roadmap"
    implementation_allowed_now = False
    acceptance_checks = []
    
    try:
        from .evolution_analysis import EVOLUTION_ANALYSES_DIR
        if EVOLUTION_ANALYSES_DIR.exists():
            analysis_files = sorted(EVOLUTION_ANALYSES_DIR.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
            if analysis_files:
                latest_analysis = read_record(analysis_files[0])
                if latest_analysis.get("target_id") == request.get("id"):
                    analysis_summary = str(latest_analysis.get("summary") or "")
                    minimal_slice = str(latest_analysis.get("minimal_slice") or "")
                    risks = latest_analysis.get("risks") if isinstance(latest_analysis.get("risks"), list) else []
                    roadmap_status = str(latest_analysis.get("roadmap_status") or "not_in_roadmap")
                    implementation_allowed_now = bool(latest_analysis.get("implementation_allowed_now", False))
                    acceptance_checks = latest_analysis.get("acceptance_checks") if isinstance(latest_analysis.get("acceptance_checks"), list) else []
    except Exception:
        pass  # Fall back to generic proposal if analysis loading fails
    
    # If no analysis found, invoke self-evolution agent to generate one
    if not analysis_summary and not minimal_slice:
        try:
            from .agent_runner import run_agent
            agent_run, analysis_result = run_agent("self_evolution", target=request.get("id"))
            if analysis_result and analysis_result.get("schema") == "abyss.evolution_analysis.v1":
                analysis_summary = str(analysis_result.get("summary") or "")
                minimal_slice = str(analysis_result.get("minimal_slice") or "")
                risks = analysis_result.get("risks") if isinstance(analysis_result.get("risks"), list) else []
                roadmap_status = str(analysis_result.get("roadmap_status") or "not_in_roadmap")
                implementation_allowed_now = bool(analysis_result.get("implementation_allowed_now", False))
                acceptance_checks = analysis_result.get("acceptance_checks") if isinstance(analysis_result.get("acceptance_checks"), list) else []
        except Exception as e:
            # If self-evolution agent fails, raise exception instead of silent fallback
            raise SystemExit(f"Self-evolution analysis failed for request {request.get('id')}: {e}")
    
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
        "self_evolution_analysis": {
            "summary": analysis_summary,
            "minimal_slice": minimal_slice,
            "risks": risks,
            "roadmap_status": roadmap_status,
            "implementation_allowed_now": implementation_allowed_now,
            "acceptance_checks": acceptance_checks
        },
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