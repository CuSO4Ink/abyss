from __future__ import annotations

from pathlib import Path

from .audit import append_event
from .context_pack import build_context_pack, render_context_pack_for_prompt, render_context_pack_summary
from .harness import render_harness_markdown
from .utils import copy_to_clipboard, new_id, now_iso, read_record, repo_root, run_git, runtime_root

PROMPT_DIR = runtime_root() / "process" / "prompt_packages"
BASE_PROMPT = repo_root() / "prompts" / "system" / "base.md"
GIT_MODE_PROMPT = repo_root() / "prompts" / "modes" / "git_diff_summary.md"


def _safe_read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _git_context(include_diff: bool) -> str:
    status = run_git(["status", "--short", "--branch"], allow_fail=True)
    if not include_diff:
        return f"## Git status\n\n```text\n{status}\n```\n"
    diff = run_git(["diff", "--stat"], allow_fail=True)
    diff_text = run_git(["diff"], allow_fail=True)
    if len(diff_text) > 12000:
        diff_text = diff_text[:12000] + "\n\n[TRUNCATED BY ABYSS MVP]\n"
    return f"## Git status\n\n```text\n{status}\n```\n\n## Git diff stat\n\n```text\n{diff}\n```\n\n## Git diff\n\n```diff\n{diff_text}\n```\n"


def build_prompt(intent_path: Path, include_git_diff: bool = False, copy: bool = False) -> Path:
    intent = read_record(intent_path)
    ppkg_id = new_id("ppkg")
    mode = intent.get("mode", "assisted_prompt")
    context = _git_context(include_git_diff or mode == "git_diff_summary")
    mode_prompt = _safe_read(GIT_MODE_PROMPT) if mode == "git_diff_summary" else ""
    body = f"""# Abyss Prompt Package

- prompt_package_id: {ppkg_id}
- intent_id: {intent['id']}
- created_at: {now_iso()}
- executor: manual_client

---

## System constraints

{_safe_read(BASE_PROMPT)}

---

{render_harness_markdown()}

---

## Mode instructions

{mode_prompt or 'Use the generic assisted prompt workflow.'}

---

## User intent

{intent['goal']}

---

## Scope

Allowed:
{chr(10).join('- ' + x for x in intent.get('scope', {}).get('allowed', []))}

Denied:
{chr(10).join('- ' + x for x in intent.get('scope', {}).get('denied', []))}

---

## Local context

{context}

---

## Required output

Please respond with:

1. Direct answer or summary.
2. Risks / unknowns.
3. Suggested `abyss-action` blocks only if concrete follow-up actions are needed.

Never claim an action has been executed. Only propose actions.
"""
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPT_DIR / f"{ppkg_id}.md"
    path.write_text(body, encoding="utf-8")
    if copy:
        copy_to_clipboard(body)
    append_event("prompt_package.created", "Built prompt package", {"prompt_package_id": ppkg_id, "intent_id": intent["id"], "path": path.as_posix()})
    return path


def build_external_developer_prompt(objective: str, *, details: str = "", copy: bool = False) -> Path:
    """Build a governed task package for an external model platform.

    External platforms are temporary expert resources. The generated package is
    candidate-material-only and cannot approve, execute, mutate files, or bypass
    the Abyss governance path.
    """
    target_record = {
        "schema": "abyss.external_developer_task.v1",
        "objective": objective,
        "details": details,
        "candidate_material_only": True,
        "no_action_executed": True,
    }
    context_pack = build_context_pack(
        agent_id="external_developer",
        target_record=target_record,
        task_type="external_collaboration",
    )
    ppkg_id = new_id("ppkg_external_developer")
    context_pack_summary = render_context_pack_summary(context_pack)
    context_pack_rendered = render_context_pack_for_prompt(context_pack)
    body = f"""# Abyss External Developer Prompt Package

- prompt_package_id: {ppkg_id}
- package_type: external_developer_task
- created_at: {now_iso()}
- executor: external_model_platform
- context_pack_id: {context_pack.get("id")}
- task_type: {context_pack.get("task_type")}
- candidate_material_only: true
- no_action_executed: true

---

## Task objective

{objective}

---

## Additional details

{details or '[none]'}

---

## Authority boundary

The external model platform is a replaceable expert resource. Its output is candidate material only. It must not claim facts, approvals, execution, file mutation, state transition, scheduling, governance decisions, or ownership of Abyss memory/direction.

Any meaningful system modification must still follow the governed path: proposal, approval, workflow, changeset, validation, Harness review, Owner approval, executor apply, and report.

---

## Context Pack Summary

```text
{context_pack_summary}
```

---

{context_pack_rendered}

---

## Required output

Return a concise response with these sections:

1. Task understanding
2. Modules touched
3. Files touched
4. Proposed changes
5. Candidate ChangeSet / code approach, if applicable
6. Validation
7. Risk assessment
8. Architecture alignment
9. Open questions
10. Whether Brain Agent / Owner decision is needed
11. Recommended next step

Do not claim execution. Do not output approvals. Do not bypass Harness, Owner, workflow, or executor boundaries.
"""
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPT_DIR / f"{ppkg_id}.md"
    path.write_text(body, encoding="utf-8")
    if copy:
        copy_to_clipboard(body)
    append_event("prompt_package.external_developer.created", "Built external developer prompt package", {
        "prompt_package_id": ppkg_id,
        "context_pack_id": context_pack.get("id"),
        "task_type": context_pack.get("task_type"),
        "path": path.as_posix(),
    })
    return path
