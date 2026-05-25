from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import append_event
from .changeset import dry_run_changeset, import_changeset_from_agent_output, load_changeset, resolve_changeset, validate_changeset
from .context_pack import build_context_pack, render_context_pack_for_prompt, render_context_pack_summary
from .harness import render_harness_json
from .harness_review import parse_harness_review
from .llm_executor import LLM_RESULTS_DIR, _provider_response, load_provider_config
from .evolution import resolve_evolution_target
from .evolution_analysis import parse_evolution_analysis
from .patch_compiler import compile_edit_plan_from_agent_output
from .result import ACTIONS_DIR
from .utils import latest_record, list_records, new_id, now_iso, read_record, relative_to_repo, repo_root, resolve_record_arg, runtime_root, write_record


AGENTS_FILE = repo_root() / "rules" / "agents.yaml"
AGENT_PROMPT_DIR = runtime_root() / "process" / "prompt_packages"
AGENT_RUNS_DIR = runtime_root() / "process" / "agent_runs"


def load_agents_config() -> dict[str, Any]:
    if not AGENTS_FILE.exists():
        raise SystemExit(f"Agent registry not found: {AGENTS_FILE}")
    return read_record(AGENTS_FILE)


def _agent_spec(agent_id: str) -> dict[str, Any]:
    config = load_agents_config()
    agents = config.get("agents", {})
    spec = agents.get(agent_id)
    if not isinstance(spec, dict) or not spec.get("enabled", False):
        raise SystemExit(f"Agent is not enabled or configured: {agent_id}")
    return spec


def _latest_llm_result() -> Path | None:
    if not LLM_RESULTS_DIR.exists():
        return None
    files = [p for p in LLM_RESULTS_DIR.glob("llm_result_*.md") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime)[-1] if files else None


def _safe_read(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text if len(text) <= limit else text[:limit] + "\n\n[TRUNCATED BY ABYSS]\n"


def _recent_implementation_evidence(limit: int = 8) -> dict[str, Any]:
    """Return concise recent evidence that helps Implementation Agent avoid false already_satisfied results."""
    process_root = runtime_root() / "process"
    evidence: dict[str, Any] = {
        "failed_or_blocked_workflows": [],
        "invalid_changesets": [],
        "recent_blocked_results": [],
    }
    workflows_dir = process_root / "workflows"
    if workflows_dir.exists():
        workflows = [read_record(path) for path in list_records(workflows_dir, "wf")]
        interesting = [wf for wf in workflows if wf.get("status") in {"failed", "blocked", "rejected"}]
        for wf in sorted(interesting, key=lambda item: item.get("updated_at", ""), reverse=True)[:limit]:
            last_event = (wf.get("history") or [{}])[-1]
            history_messages: list[str] = []
            for event in wf.get("history") or []:
                details = event.get("details") if isinstance(event, dict) else {}
                if isinstance(details, dict):
                    for message in details.get("messages") or []:
                        history_messages.append(str(message))
            evidence["failed_or_blocked_workflows"].append({
                "id": wf.get("id"),
                "roadmap_id": wf.get("roadmap_id"),
                "status": wf.get("status"),
                "last_error": wf.get("last_error"),
                "last_event": last_event.get("event"),
                "last_event_details": last_event.get("details", {}),
                "failure_messages": history_messages[-5:],
                "updated_at": wf.get("updated_at"),
            })

    changesets_dir = process_root / "changesets"
    if changesets_dir.exists():
        changesets = [read_record(path) for path in list_records(changesets_dir, "chg")]
        invalid = [cs for cs in changesets if cs.get("status") == "invalid" or str(cs.get("id", "")).startswith("chg_invalid")]
        for cs in sorted(invalid, key=lambda item: item.get("updated_at", item.get("created_at", "")), reverse=True)[:limit]:
            evidence["invalid_changesets"].append({
                "id": cs.get("id"),
                "roadmap_id": cs.get("roadmap_id"),
                "status": cs.get("status"),
                "summary": cs.get("summary"),
                "validation_errors": cs.get("validation_errors") or cs.get("errors"),
                "created_at": cs.get("created_at"),
                "updated_at": cs.get("updated_at"),
            })
    blocked_dir = process_root / "blocked_results"
    if blocked_dir.exists():
        blocked_results = [read_record(path) for path in list_records(blocked_dir, "blk")]
        for blocked in sorted(blocked_results, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]:
            evidence["recent_blocked_results"].append({
                "id": blocked.get("id"),
                "roadmap_id": blocked.get("roadmap_id"),
                "proposal_id": blocked.get("proposal_id"),
                "category": blocked.get("category"),
                "blocked_reason": blocked.get("blocked_reason"),
                "created_at": blocked.get("created_at"),
            })
    return evidence


def _resolve_action_target(target: str) -> Path:
    return resolve_record_arg(ACTIONS_DIR, target, "act")



def _build_harness_agent_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str | None]:
    target_path = _resolve_action_target(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"HarnessAgent role prompt not found or empty: {role_prompt_path}")

    latest_result = _latest_llm_result()
    latest_result_text = _safe_read(latest_result) if latest_result else "[no llm_result found]"
    policy_text = json.dumps(read_record(repo_root() / "rules" / "policy.yaml"), ensure_ascii=False, indent=2)
    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=6000)

    ppkg_id = new_id("ppkg_agent_harness")
    body = f"""# Abyss Agent Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: harness
- target_type: action_proposal
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target action proposal

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Latest related LLM result

```markdown
{latest_result_text}
```

---

## Policy snapshot

```json
{policy_text}
```

---

## Harness snapshot

```json
{render_harness_json()}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

---

## Required output

Return exactly one `abyss-harness-review` fenced block. Do not produce `abyss-action` blocks. Do not claim that any action was executed.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("agent.prompt_package.created", "Built agent prompt package", {"agent_id": "harness", "target_id": target_id, "path": prompt_path.as_posix()})
    return prompt_path, target_path, target_id


def _build_harness_changeset_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str, dict[str, Any]]:
    target_path = resolve_changeset(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"HarnessAgent role prompt not found or empty: {role_prompt_path}")

    validation_ok, validation_messages = validate_changeset(target_record, for_apply=False)
    dry_run_report = dry_run_changeset(target_id)
    deterministic_context = {
        "validation_ok": validation_ok,
        "validation_messages": validation_messages,
        "dry_run": dry_run_report,
        "target_changeset": target_record,
    }
    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    capabilities_text = _safe_read(repo_root() / "rules" / "capabilities.yaml", limit=8000)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=7000)

    ppkg_id = new_id("ppkg_agent_harness_changeset")
    body = f"""# Abyss Agent Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: harness
- target_type: changeset
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target ChangeSet

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Deterministic validation and dry-run context

```json
{json.dumps(deterministic_context, ensure_ascii=False, indent=2)}
```

---

## Capability registry

```json
{capabilities_text}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

---

## Required output

Return exactly one `abyss-harness-review` fenced block. Evaluate whether the ChangeSet should require human review, be denied, or is within the current executor boundary. Do not approve, reject, apply, or claim execution.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("agent.prompt_package.created", "Built harness changeset prompt package", {"agent_id": "harness", "target_id": target_id, "path": prompt_path.as_posix()})
    return prompt_path, target_path, target_id, deterministic_context


def _build_self_evolution_agent_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str]:
    target_path = resolve_evolution_target(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"Self-evolution agent role prompt not found or empty: {role_prompt_path}")

    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    roadmap_text = _safe_read(repo_root() / "ROADMAP.md", limit=8000)
    constitution_text = _safe_read(repo_root() / "ABYSS_CONSTITUTION.md", limit=8000)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=6000)

    ppkg_id = new_id("ppkg_agent_self_evolution")
    body = f"""# Abyss Agent Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: self_evolution
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target evolution record

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Roadmap snapshot

```markdown
{roadmap_text}
```

---

## Constitution excerpt

```markdown
{constitution_text}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

---

## Required output

Return exactly one `abyss-evolution-analysis` fenced block. Do not produce `abyss-action` blocks. Do not claim that any action was executed.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("agent.prompt_package.created", "Built self-evolution agent prompt package", {"agent_id": "self_evolution", "target_id": target_id, "path": prompt_path.as_posix()})
    return prompt_path, target_path, target_id


def _build_implementation_agent_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str, dict[str, Any]]:
    target_path = resolve_evolution_target(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"ImplementationAgent role prompt not found or empty: {role_prompt_path}")

    # Build Context Pack via Context Broker
    roadmap_id = str(target_record.get("roadmap_entry") or target_record.get("roadmap_id") or "")
    proposal_id = str(target_record.get("id") or "")
    context_pack = build_context_pack(
        agent_id="implementation",
        target_record=target_record,
        roadmap_id=roadmap_id,
        proposal_id=proposal_id,
    )
    context_pack_rendered = render_context_pack_for_prompt(context_pack)
    context_pack_summary = render_context_pack_summary(context_pack)

    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    roadmap_text = _safe_read(repo_root() / "ROADMAP.md", limit=6000)
    capabilities_text = _safe_read(repo_root() / "rules" / "capabilities.yaml", limit=6000)
    implementation_evidence = _recent_implementation_evidence()

    ppkg_id = new_id("ppkg_agent_implementation")
    body = f"""# Abyss Agent Prompt Package


- prompt_package_id: {ppkg_id}
- agent_id: implementation
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- context_pack_id: {context_pack.get("id")}
- task_type: {context_pack.get("task_type")}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Context Pack Summary

```
{context_pack_summary}
```

Important: If a file is listed under `Files included`, it is available in the Repository Files section below. Do not request a file that is already included; use an `abyss-edit-plan` if the included file contains the target symbol or unique anchor.

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target approved evolution / roadmap record

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Roadmap snapshot

```markdown
{roadmap_text}
```

---

## Capability registry

```json
{capabilities_text}
```

---

## Recent implementation failure evidence

This evidence is provided to prevent false `already_satisfied` conclusions. If recent failed, blocked, rejected, placeholder, or invalid ChangeSet evidence is relevant to the target roadmap item, do not output `already_satisfied`; produce a concrete corrective ChangeSet or a specific context request instead.

```json
{json.dumps(implementation_evidence, ensure_ascii=False, indent=2)}
```

---

{context_pack_rendered}

---

## Required output


Return exactly one fenced block: `abyss-edit-plan`, `abyss-changeset`, `abyss-context-request`, or `abyss-blocked-result`.

Preferred output: `abyss-edit-plan` with valid JSON for schema `abyss.edit_plan.v1`. Use it when you can describe the intended edit by file path plus a Python symbol or unique anchor, so Abyss can deterministically compile exact `old_content` from the local repository. Example:

```abyss-edit-plan
{{"schema":"abyss.edit_plan.v1","id":"chg_short_descriptive_id","roadmap_id":"R000","summary":"short implementation summary","risk_level":"L2","edits":[{{"id":"op_001","kind":"replace_symbol","target":{{"path":"abyss_cli/example.py"}},"symbol":"function_name","symbol_type":"function","new_content":"def function_name():\n    return True\n"}}],"checks":["python -m compileall -q abyss_cli","python -m abyss_cli check"]}}
```

Supported edit kinds: `replace_symbol`, `replace_anchor`, `append_after_anchor`, and `create_file`.

Edit-plan edit-size requirements:
- Use `replace_symbol` for small Python functions/classes only. Do not use it for large orchestration/rendering functions, long CLI command handlers, or any symbol whose replacement would exceed about 120 lines.
- For large functions, use `replace_anchor` or `append_after_anchor` around a small unique snippet instead of replacing the whole symbol.
- If the only safe edit would require replacing a large symbol and no unique small anchor is visible, output `abyss-context-request` instead of a large `replace_symbol` edit.

Edit-plan JSON requirements:

- The fenced block must be strictly valid JSON parseable by `json.loads`.
- Every JSON string value, especially `new_content`, `content`, and `anchor`, must be a single JSON string with escaped newlines as `\\n` and escaped inner double quotes as `\\"`. Never place raw multi-line source code directly inside a JSON string.
- Before finalizing, mentally run `json.loads` against the fenced block; if it would fail, output `abyss-context-request` instead of malformed JSON.

- If you have sufficient context to implement safely but cannot express the edit as an edit plan: output `abyss-changeset` with valid JSON for schema `abyss.change_set.v1`.

- If context is insufficient: output `abyss-context-request` with valid JSON for schema `abyss.context_request.v1`.
- If the task is fundamentally blocked by governance or infeasibility: output `abyss-blocked-result` with valid JSON for schema `abyss.blocked_result.v1`.

Do not produce `abyss-action` blocks. Do not approve, reject, apply, run commands, or claim execution. Never invent exact `old_content`; prefer `abyss-edit-plan` so the deterministic Patch Compiler can read exact file content.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    context_metadata = {
        "context_pack_id": context_pack.get("id"),
        "task_type": context_pack.get("task_type"),
        "files_included": context_pack.get("files_included", []),
        "files_missing": context_pack.get("files_missing", []),
        "modules_included": context_pack.get("modules_included", []),
    }
    append_event("agent.prompt_package.created", "Built implementation agent prompt package", {
        "agent_id": "implementation",
        "target_id": target_id,
        "context_pack_id": context_pack.get("id"),
        "task_type": context_pack.get("task_type"),
        "files_included": len(context_pack.get("files_included", [])),
        "files_missing": context_pack.get("files_missing", []),
        "path": prompt_path.as_posix(),
    })
    return prompt_path, target_path, target_id, context_metadata


def _parse_context_request(text: str) -> dict[str, Any] | None:
    """Parse an abyss-context-request fenced block from agent output."""
    import re
    pattern = r"```abyss-context-request\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _parse_blocked_result(text: str) -> dict[str, Any] | None:
    """Parse an abyss-blocked-result fenced block from agent output."""
    import re
    pattern = r"```abyss-blocked-result\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def _has_relevant_recent_implementation_failures(target_record: dict[str, Any]) -> bool:
    """Conservatively detect whether already_satisfied would contradict recent implementation evidence."""
    roadmap_id = str(target_record.get("roadmap_entry") or target_record.get("roadmap_id") or "")
    title = str(target_record.get("title") or target_record.get("purpose") or target_record.get("details") or "").lower()
    evidence = _recent_implementation_evidence(limit=12)
    for workflow in evidence.get("failed_or_blocked_workflows", []):
        wf_roadmap = str(workflow.get("roadmap_id") or "")
        if roadmap_id and wf_roadmap == roadmap_id:
            return True
        error_text = json.dumps(workflow, ensure_ascii=False).lower()
        if "implementation agent" in title and any(marker in error_text for marker in ["placeholder", "invalid", "already_satisfied", "missing_operations", "implementation_agent_failed"]):
            return True
    for changeset in evidence.get("invalid_changesets", []):
        error_text = json.dumps(changeset, ensure_ascii=False).lower()
        if "implementation agent" in title and any(marker in error_text for marker in ["missing_operations", "invalid", "placeholder"]):
            return True
    for blocked in evidence.get("recent_blocked_results", []):
        blocked_roadmap = str(blocked.get("roadmap_id") or "")
        if roadmap_id and blocked_roadmap == roadmap_id:
            return True
        blocked_text = json.dumps(blocked, ensure_ascii=False).lower()
        if "implementation agent" in title and "already_satisfied" in blocked_text:
            return True
    return False


def _parse_implementation_output(response_text: str, *, agent_run_id: str, result_path: Path, target_record: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Parse implementation agent output, supporting three output types:

    1. abyss.change_set.v1 (normal changeset)
    2. abyss.context_request.v1 (missing context)
    3. abyss.blocked_result.v1 (fundamentally blocked)

    Returns a dict with an 'output_type' field indicating which type was parsed.
    """
    if not response_text or not response_text.strip():
        append_event("agent.output.empty", "Implementation agent returned empty response", {
            "agent_run_id": agent_run_id,
            "result_path": str(result_path),
        })
        return None

    # Try context_request first (higher priority — if agent says it needs more context, respect that)
    context_request = _parse_context_request(response_text)
    if context_request:
        record = {
            "schema": "abyss.context_request.v1",
            "output_type": "context_request",
            "agent_run_id": agent_run_id,
            "result_path": str(result_path),
            "created_at": now_iso(),
            **context_request,
        }
        # Persist the context request
        ctx_req_dir = runtime_root() / "process" / "context_requests"
        ctx_req_dir.mkdir(parents=True, exist_ok=True)
        req_id = new_id("ctx_req")
        record["id"] = req_id
        write_record(ctx_req_dir / f"{req_id}.yaml", record)
        append_event("agent.output.context_request", "Implementation agent requested more context", {
            "agent_run_id": agent_run_id,
            "context_request_id": req_id,
            "missing_files": [m.get("file") for m in record.get("missing", [])],
        })
        return record

    # Try blocked_result
    blocked_result = _parse_blocked_result(response_text)
    if blocked_result:
        if blocked_result.get("category") == "already_satisfied" and target_record and _has_relevant_recent_implementation_failures(target_record):
            roadmap_id = target_record.get("roadmap_entry") or target_record.get("roadmap_id") or "unknown"
            proposal_id = target_record.get("id") or "unknown"
            raise SystemExit(f"Implementation agent returned already_satisfied despite relevant recent implementation failure evidence for roadmap={roadmap_id} proposal={proposal_id}")
        record = {
            "schema": "abyss.blocked_result.v1",
            "output_type": "blocked_result",
            "agent_run_id": agent_run_id,
            "result_path": str(result_path),
            "created_at": now_iso(),
            **blocked_result,
        }

        # Persist the blocked result
        blocked_dir = runtime_root() / "process" / "blocked_results"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        blk_id = new_id("blk")
        record["id"] = blk_id
        write_record(blocked_dir / f"{blk_id}.yaml", record)
        append_event("agent.output.blocked_result", "Implementation agent reported task blocked", {
            "agent_run_id": agent_run_id,
            "blocked_result_id": blk_id,
            "category": record.get("category"),
            "reason": record.get("blocked_reason", "")[:200],
        })
        return record

    # Validate for NOOP patterns before attempting compilation.
    # A response that contains only whitespace-equivalent changes or repeated content
    # is likely a generation error.

    # Prefer deterministic edit-plan compilation before raw ChangeSet parsing. This keeps
    # the LLM in a planner role and lets Abyss read exact old_content from the repo.
    compiled_changeset = compile_edit_plan_from_agent_output(response_text, agent_run_id=agent_run_id, result_path=result_path)
    if compiled_changeset:
        # Surface structured parse diagnostics in audit for workflow observability
        if compiled_changeset.get("status") == "invalid":
            append_event("agent.output.invalid_edit_plan", "Implementation agent produced invalid edit plan", {
                "agent_run_id": agent_run_id,
                "changeset_id": compiled_changeset.get("id"),
                "parse_diagnostics": compiled_changeset.get("parse_diagnostics"),
                "validation_messages": (compiled_changeset.get("validation") or {}).get("messages", []),
            })
        return compiled_changeset

    # Fall back to legacy ChangeSet parsing for backward compatibility.
    changeset = import_changeset_from_agent_output(response_text, agent_run_id=agent_run_id, result_path=result_path)
    if changeset:
        ok, messages = validate_changeset(changeset, for_apply=True)
        changeset["validation"] = {"ok": ok, "messages": messages, "validated_at": now_iso()}
        changeset["output_type"] = "changeset"
        write_record(runtime_root() / "process" / "changesets" / f"{changeset['id']}.yaml", changeset)
    else:
        # No recognized output format found
        append_event("agent.output.unrecognized", "Implementation agent output did not match any recognized format", {
            "agent_run_id": agent_run_id,
            "result_path": str(result_path),
            "response_length": len(response_text),
            "response_preview": response_text[:300],
        })
    return changeset




def run_agent(agent_id: str, target: str = "latest", provider: str | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    spec = _agent_spec(agent_id)
    provider_name = provider or str(spec.get("provider") or "cli")
    deterministic_context = None
    target_type = "action_proposal"
    context_metadata: dict[str, Any] = {}
    target_record_for_validation: dict[str, Any] | None = None
    if agent_id == "harness":
        prompt_path, _target_path, target_id = _build_harness_agent_prompt(spec, target)
    elif agent_id == "self_evolution":
        prompt_path, _target_path, target_id = _build_self_evolution_agent_prompt(spec, target)
    elif agent_id == "implementation":
        prompt_path, _target_path, target_id, context_metadata = _build_implementation_agent_prompt(spec, target)
        target_record_for_validation = read_record(_target_path)

    else:
        raise SystemExit(f"Agent is configured but not implemented: {agent_id}")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    provider_config_root = load_provider_config()
    providers = provider_config_root.get("providers", {})
    provider_config = providers.get(provider_name)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider_name}")

    response_text = _provider_response(provider_name, provider_config, prompt_path, prompt_text)
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(response_text, encoding="utf-8")

    agent_run = {
        "schema": "abyss.agent_run.v1",
        "id": new_id("agent_run"),
        "agent_id": agent_id,
        "target_id": target_id,
        "provider": provider_name,
        "prompt_package": prompt_path.as_posix(),
        "result_path": result_path.as_posix(),
        "status": "completed",
        "no_action_executed": True,
        "created_at": now_iso(),
    }
    if context_metadata:
        agent_run["context"] = context_metadata
    write_record(AGENT_RUNS_DIR / f"{agent_run['id']}.yaml", agent_run)
    append_event("agent.run.completed", "Agent run completed", {"agent_run_id": agent_run["id"], "agent_id": agent_id, "target_id": target_id, "result_path": result_path.as_posix()})

    specialized_record = None
    if agent_id == "harness":
        specialized_record = parse_harness_review(response_text, target_id=target_id, agent_run_id=agent_run["id"], result_path=result_path)
    elif agent_id == "self_evolution":
        specialized_record = parse_evolution_analysis(response_text, target_id=target_id, agent_run_id=agent_run["id"], result_path=result_path)
    elif agent_id == "implementation":
        specialized_record = _parse_implementation_output(response_text, agent_run_id=agent_run["id"], result_path=result_path, target_record=target_record_for_validation)

    return agent_run, specialized_record



def run_harness_review(target: str = "latest", provider: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    agent_run, review = run_agent("harness", target=target, provider=provider)
    if review is None:
        raise SystemExit("Harness review was not created")
    return agent_run, review


def run_harness_changeset_review(target: str = "latest", provider: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = _agent_spec("harness")
    provider_name = provider or str(spec.get("provider") or "cli")
    prompt_path, _target_path, target_id, deterministic_context = _build_harness_changeset_prompt(spec, target)
    prompt_text = prompt_path.read_text(encoding="utf-8")

    provider_config_root = load_provider_config()
    providers = provider_config_root.get("providers", {})
    provider_config = providers.get(provider_name)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider_name}")

    response_text = _provider_response(provider_name, provider_config, prompt_path, prompt_text)
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(response_text, encoding="utf-8")

    agent_run = {
        "schema": "abyss.agent_run.v1",
        "id": new_id("agent_run"),
        "agent_id": "harness",
        "target_id": target_id,
        "target_type": "changeset",
        "provider": provider_name,
        "prompt_package": prompt_path.as_posix(),
        "result_path": result_path.as_posix(),
        "status": "completed",
        "no_action_executed": True,
        "created_at": now_iso(),
    }
    write_record(AGENT_RUNS_DIR / f"{agent_run['id']}.yaml", agent_run)
    append_event("agent.run.completed", "HarnessAgent ChangeSet review run completed", {"agent_run_id": agent_run["id"], "agent_id": "harness", "target_id": target_id, "target_type": "changeset", "result_path": result_path.as_posix()})
    review = parse_harness_review(response_text, target_id=target_id, agent_run_id=agent_run["id"], result_path=result_path, target_type="changeset", deterministic_context=deterministic_context)
    return agent_run, review
