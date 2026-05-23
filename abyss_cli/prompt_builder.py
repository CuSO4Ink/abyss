from __future__ import annotations

from pathlib import Path

from .audit import append_event
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
