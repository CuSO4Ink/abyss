"""Brain Agent R098: LLM-drafted candidate evolution proposals.

This module implements the R098 requirement: Brain Agent uses LLM to draft
candidate evolution proposals. Brain never approves its own proposals —
the Owner reviews and decides whether to enter the governance chain.

Flow:
  1. Assemble context (deterministic, reuses build_brain_context)
  2. Load working memory for continuity
  3. Build proposal-drafting prompt with anti-entropy constraints
  4. Call LLM provider
  5. Parse abyss-brain-proposal fenced JSON block
  6. Validate structure and anti-entropy check
  7. Write proposal record to evolution/proposals/
  8. Return candidate proposal (advisory only, no governance chain entry)

Hard boundaries:
  - Output is candidate material only, not approval or execution.
  - Brain never auto-enters the governance chain.
  - Proposals must include anti_entropy_check (减法优先 constraint).
  - Proposals touching governance core are flagged high risk.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import append_event
from .brain import build_brain_context, load_working_memory
from .fenced_blocks import parse_named_json_block
from .llm_executor import LLM_RESULTS_DIR, _provider_response, get_default_provider, load_provider_config
from .utils import ensure_dir, new_id, now_iso, read_record, repo_root, runtime_root, write_record


PROPOSAL_PROMPT_PATH = repo_root() / "prompts" / "agents" / "brain_propose.md"
AGENT_PROMPT_DIR = runtime_root() / "process" / "prompt_packages"
LLM_RESPONSES_DIR = runtime_root() / "process" / "brain_proposals"
AGENTS_FILE = repo_root() / "rules" / "agents.yaml"


def _safe_read(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text if len(text) <= limit else text[:limit] + "\n\n[TRUNCATED BY ABYSS]\n"


def _load_agents_config() -> dict[str, Any]:
    if not AGENTS_FILE.exists():
        raise SystemExit(f"Agent registry not found: {AGENTS_FILE}")
    return read_record(AGENTS_FILE)


def _build_proposal_prompt(
    brain_context: dict[str, Any],
    working_memory: list[dict[str, Any]] | None,
    question: str | None = None,
) -> tuple[Path, str]:
    """Build the LLM prompt for proposal drafting."""
    config = _load_agents_config()
    brain_spec = config.get("agents", {}).get("brain", {})
    agents_text = json.dumps(brain_spec, ensure_ascii=False, indent=2)
    role_prompt = _safe_read(PROPOSAL_PROMPT_PATH)
    if not role_prompt.strip():
        raise SystemExit(f"Brain propose role prompt not found or empty: {PROPOSAL_PROMPT_PATH}")

    roadmap_text = _safe_read(repo_root() / "ROADMAP.md", limit=6000)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=4000)

    # Working memory section
    memory_section = ""
    if working_memory:
        memory_lines = []
        for entry in working_memory[-10:]:
            ts = entry.get("timestamp", "")
            kind = entry.get("kind", "")
            text = entry.get("text", "")
            memory_lines.append(f"- [{ts}] {kind}: {text}")
        memory_section = f"""---

## Working memory (recent Brain cognition, for continuity)

The following are your recent cognitive outputs. Use them for continuity and
progressive understanding — do not merely repeat them.

{chr(10).join(memory_lines)}

"""

    # Optional question section
    question_section = ""
    if question and question.strip():
        question_section = f"""---

## Owner question

The Owner has asked a specific question. Address it in your proposal rationale.

**Question:** {question.strip()}

"""

    ppkg_id = new_id("ppkg_brain_propose")
    body = f"""# Abyss Brain Agent — Proposal Drafting Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: brain_propose
- target_type: proposal_drafting
- target_id: current_state
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec (brain agent)

```json
{agents_text}
```

---

## Proposal drafter role prompt

{role_prompt}

---

## Deterministic brain context snapshot

This snapshot was assembled deterministically (no LLM). Your job is to reason
over it and produce a candidate proposal. Do not re-emit this data verbatim;
synthesize it into a concrete, actionable proposal.

```json
{json.dumps(brain_context, ensure_ascii=False, indent=2)}
```

---

## Roadmap snapshot

```markdown
{roadmap_text}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

{memory_section}{question_section}
## Hard boundaries (reiterated)

- You may not execute, approve, reject, or mutate anything.
- You may not create evolution requests, changesets, or workflow items directly.
- Your output is **candidate material**, not truth, approval, or execution.
- You may not make outbound calls or schedule work.
- If you believe an evolution is warranted, phrase it as a candidate proposal for the
  Owner, not as a directive.
- **Before suggesting any new command, feature, or module**, you MUST first check the
  `cli_commands` field in the brain context snapshot and the system map. If a similar
  capability already exists, acknowledge it and refine your suggestion accordingly.
  Do not propose creating something that already exists.
- **Anti-entropy constraint**: Before drafting any add/expand proposal, evaluate whether
  a simplify alternative exists. Brain defaults to subtraction.

Return exactly one `abyss-brain-proposal` fenced JSON block. Do not produce any other
output format. Do not produce `abyss-action` blocks.
"""

    ensure_dir(AGENT_PROMPT_DIR)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("brain.propose.prompt_built", "Built brain proposal prompt package", {
        "prompt_package_id": ppkg_id,
        "path": prompt_path.as_posix(),
        "has_question": bool(question),
        "has_memory": bool(working_memory),
    })
    return prompt_path, body


def _validate_proposal(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a parsed brain proposal record.

    Returns (ok, messages). Checks:
    - Required fields present
    - schema == abyss.brain_proposal.v1
    - proposal_type is valid enum
    - anti_entropy_check has required subfields
    - chosen_approach matches proposal_type (consistency)
    - risk_level is valid enum
    """
    messages: list[str] = []
    required = [
        "schema", "summary", "proposal_type", "anti_entropy_check",
        "rationale", "proposed_changes", "risk_level", "boundary",
    ]
    for field in required:
        if field not in record:
            messages.append(f"Missing required field: {field}")

    if record.get("schema") != "abyss.brain_proposal.v1":
        messages.append(f"schema must be 'abyss.brain_proposal.v1', got: {record.get('schema')}")

    valid_types = {"simplify", "add", "expand", "fix", "maintain", "no_action"}
    if record.get("proposal_type") not in valid_types:
        messages.append(f"proposal_type must be one of {valid_types}, got: {record.get('proposal_type')}")

    valid_risks = {"low", "medium", "high"}
    if record.get("risk_level") not in valid_risks:
        messages.append(f"risk_level must be one of {valid_risks}, got: {record.get('risk_level')}")

    aec = record.get("anti_entropy_check")
    if not isinstance(aec, dict):
        messages.append("anti_entropy_check must be an object")
    else:
        aec_required = ["evaluated_simplify_alternative", "chosen_approach", "justification"]
        for field in aec_required:
            if field not in aec:
                messages.append(f"anti_entropy_check missing: {field}")
        valid_approaches = {"simplify", "add", "expand", "fix", "no_action"}
        if aec.get("chosen_approach") not in valid_approaches:
            messages.append(f"anti_entropy_check.chosen_approach invalid: {aec.get('chosen_approach')}")

        # Consistency: if proposal_type is add/expand but chosen_approach is simplify, flag inconsistency
        pt = record.get("proposal_type")
        ca = aec.get("chosen_approach")
        if pt in {"add", "expand"} and ca == "simplify":
            messages.append(f"Inconsistency: proposal_type={pt} but anti_entropy_check.chosen_approach=simplify")
        if pt == "simplify" and ca in {"add", "expand"}:
            messages.append(f"Inconsistency: proposal_type=simplify but anti_entropy_check.chosen_approach={ca}")

        # If add/expand was chosen, justification must be non-empty
        if ca in {"add", "expand"} and not str(aec.get("justification", "")).strip():
            messages.append("anti_entropy_check.justification required when chosen_approach is add/expand (must explain why simplify was insufficient)")

    # no_action proposals can have empty proposed_changes
    if record.get("proposal_type") != "no_action":
        changes = record.get("proposed_changes")
        if not isinstance(changes, list) or len(changes) == 0:
            messages.append("proposed_changes must be a non-empty array for non-no_action proposals")

    return len(messages) == 0, messages


def draft_brain_proposal(
    provider: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    """Run the full Brain proposal drafting pipeline.

    1. Assemble deterministic context
    2. Load working memory
    3. Build prompt
    4. Call LLM
    5. Parse + validate
    6. Write record
    7. Return candidate proposal
    """
    # Step 1: Assemble context
    brain_context = build_brain_context()

    # Step 2: Load working memory
    working_memory = load_working_memory(limit=10)

    # Step 3: Build prompt
    prompt_path, prompt_text = _build_proposal_prompt(
        brain_context, working_memory, question=question
    )

    # Step 4: Resolve provider and call LLM
    provider_name = provider or get_default_provider()
    provider_config_root = load_provider_config()
    providers = provider_config_root.get("providers", {})
    provider_config = providers.get(provider_name)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider_name}")

    response_text, _usage_diagnostics = _provider_response(
        provider_name, provider_config, prompt_path, prompt_text
    )

    # Save raw LLM result
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    ensure_dir(result_path.parent)
    result_path.write_text(response_text, encoding="utf-8")

    append_event("brain.propose.llm_completed", "Brain proposal LLM call completed", {
        "provider": provider_name,
        "result_path": result_path.as_posix(),
        "response_length": len(response_text),
    })

    # Step 5: Parse response
    parsed, parse_error, saw_block = parse_named_json_block(
        response_text, "abyss-brain-proposal"
    )

    if parsed is None:
        error_msg = parse_error or ("block not found" if not saw_block else "unknown parse error")
        append_event("brain.propose.parse_failed", "Failed to parse brain proposal from LLM response", {
            "error": error_msg,
            "saw_block": saw_block,
            "result_path": result_path.as_posix(),
        })
        return {
            "schema": "abyss.brain_propose_error.v1",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": "coordinator_propose_bounded",
            "error": error_msg,
            "saw_block": saw_block,
            "result_path": result_path.as_posix(),
            "boundary": "Brain propose is advisory only; parse failure does not execute or approve anything.",
        }

    # Normalize LLM output: map verbose enum fields to known values
    _approach_aliases = {
        "simplify": {"simplify", "subtra", "remove", "delete", "consolidat", "reduce"},
        "add": {"add", "new", "create", "introduc"},
        "expand": {"expand", "extend", "enhance", "augment", "grow"},
        "fix": {"fix", "repair", "patch", "correct", "resolv"},
        "no_action": {"no_action", "no action", "maintain", "stable", "none", "noop", "no-op"},
    }

    def _normalize_enum(raw_value: str, aliases: dict[str, set[str]]) -> str | None:
        raw = str(raw_value).strip().lower()
        if not raw:
            return None
        for canonical, keywords in aliases.items():
            if raw == canonical:
                return canonical
            for kw in keywords:
                if kw in raw:
                    return canonical
        return None

    aec = parsed.get("anti_entropy_check")
    if isinstance(aec, dict) and "chosen_approach" in aec:
        normalized = _normalize_enum(aec["chosen_approach"], _approach_aliases)
        if normalized:
            aec["chosen_approach"] = normalized
        elif "proposal_type" in parsed:
            # Fallback: derive chosen_approach from proposal_type if LLM produced a sentence
            pt_norm = _normalize_enum(parsed["proposal_type"], _approach_aliases)
            if pt_norm:
                aec["chosen_approach"] = pt_norm

    if "proposal_type" in parsed:
        _type_aliases = {k: v for k, v in _approach_aliases.items() if k != "no_action"}
        _type_aliases["maintain"] = {"maintain", "upkeep", "health"}
        _type_aliases["no_action"] = {"no_action", "no action", "stable", "none", "noop", "no-op"}
        normalized_pt = _normalize_enum(parsed["proposal_type"], _type_aliases)
        if normalized_pt:
            parsed["proposal_type"] = normalized_pt

    # Step 6: Validate
    ok, validation_messages = _validate_proposal(parsed)
    parsed["validation"] = {
        "ok": ok,
        "messages": validation_messages,
        "validated_at": now_iso(),
    }

    # Step 7: Write proposal record
    proposal_id = new_id("brain_proposal")
    parsed["id"] = proposal_id
    parsed["agent_run_type"] = "brain_propose_llm"
    parsed["provider"] = provider_name
    parsed["prompt_package"] = prompt_path.as_posix()
    parsed["result_path"] = result_path.as_posix()
    parsed["created_at"] = now_iso()
    parsed["no_approval_granted"] = True
    parsed["no_action_executed"] = True
    parsed["candidate_material_only"] = True
    parsed["next_step"] = parsed.get("next_step") or (
        "If the Owner agrees with this candidate proposal, run: "
        "abyss evolution request '<summary>' --details '<details>' to create a formal request. "
        "Brain does not create the request automatically."
    )

    ensure_dir(LLM_RESPONSES_DIR)
    record_path = LLM_RESPONSES_DIR / f"{proposal_id}.yaml"
    write_record(record_path, parsed)

    append_event("brain.propose.completed", "Brain proposal drafted and saved", {
        "proposal_id": proposal_id,
        "proposal_type": parsed.get("proposal_type"),
        "risk_level": parsed.get("risk_level"),
        "validation_ok": ok,
        "validation_messages": validation_messages,
        "record_path": record_path.as_posix(),
    })

    return parsed


def render_brain_proposal_json(proposal: dict[str, Any] | None = None) -> str:
    """Render a brain proposal as JSON. If no proposal is passed, draft a new one."""
    if proposal is None:
        proposal = draft_brain_proposal()
    return json.dumps(proposal, ensure_ascii=False, indent=2)
