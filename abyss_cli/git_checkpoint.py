"""Read-only git checkpoint status.

Provides structured JSON output of local git working tree status
using only read-only git commands: git status --porcelain,
git diff --stat, and git diff --staged --stat.

Non-goals (explicitly forbidden):
- No git add, commit, push, pull, fetch, rebase, reset, config, or any write operation.
- No remote operations.
- No history rewrite.
- No staging mutations.
- No scheduling.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .utils import repo_root


def _run_git_readonly(args: list[str]) -> str:
    """Run a read-only git command and return stdout.

    Only allows the exact read-only commands needed for checkpoint status.
    Raises SystemExit with structured JSON error on failure.
    """
    allowed_prefixes = [
        ["status", "--porcelain"],
        ["diff", "--stat"],
        ["diff", "--staged", "--stat"],
    ]
    is_allowed = any(
        args[: len(prefix)] == prefix for prefix in allowed_prefixes
    )
    if not is_allowed:
        raise SystemExit(
            json.dumps(
                {"error": "forbidden_git_command", "command": args, "message": "Only read-only git commands are permitted"},
                ensure_ascii=False,
            )
        )
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root())] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        raise SystemExit(
            json.dumps(
                {"error": "git_not_found", "message": "git executable not found on PATH"},
                ensure_ascii=False,
            )
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(
            json.dumps(
                {"error": "git_timeout", "message": "git command timed out after 30 seconds"},
                ensure_ascii=False,
            )
        )
    if proc.returncode != 0:
        raise SystemExit(
            json.dumps(
                {
                    "error": "git_command_failed",
                    "command": args,
                    "returncode": proc.returncode,
                    "stderr": (proc.stderr or "").strip()[:500],
                    "message": "git command returned non-zero exit code",
                },
                ensure_ascii=False,
            )
        )
    return proc.stdout


def _parse_porcelain_status(raw: str) -> dict[str, Any]:
    """Parse git status --porcelain output into categorized file lists."""
    files_modified: list[str] = []
    files_added: list[str] = []
    files_deleted: list[str] = []
    files_untracked: list[str] = []

    for line in raw.splitlines():
        if len(line) < 3:
            continue
        xy = line[:2]
        filepath = line[3:].strip()
        if not filepath:
            continue

        # Untracked
        if xy == "??":
            files_untracked.append(filepath)
            continue

        index_status = xy[0]
        worktree_status = xy[1]

        # Added (new file in index or worktree)
        if index_status == "A" or worktree_status == "A":
            files_added.append(filepath)
        # Deleted
        elif index_status == "D" or worktree_status == "D":
            files_deleted.append(filepath)
        # Modified (includes renamed, copied as modified for simplicity)
        elif index_status in ("M", "R", "C") or worktree_status in ("M", "R", "C"):
            files_modified.append(filepath)
        else:
            # Any other non-empty status counts as modified
            if index_status.strip() or worktree_status.strip():
                files_modified.append(filepath)

    return {
        "files_modified": sorted(set(files_modified)),
        "files_added": sorted(set(files_added)),
        "files_deleted": sorted(set(files_deleted)),
        "files_untracked": sorted(set(files_untracked)),
    }


def checkpoint_status() -> dict[str, Any]:
    """Return read-only git checkpoint status as a structured dict.

    Keys:
        clean: bool - True if working tree is clean
        files_modified: list[str]
        files_added: list[str]
        files_deleted: list[str]
        files_untracked: list[str]
        diff_stat: str - output of git diff --stat
        diff_staged_stat: str - output of git diff --staged --stat
    """
    porcelain_output = _run_git_readonly(["status", "--porcelain"])
    diff_stat_output = _run_git_readonly(["diff", "--stat"])
    diff_staged_stat_output = _run_git_readonly(["diff", "--staged", "--stat"])

    parsed = _parse_porcelain_status(porcelain_output)

    is_clean = (
        not parsed["files_modified"]
        and not parsed["files_added"]
        and not parsed["files_deleted"]
        and not parsed["files_untracked"]
    )

    return {
        "schema": "abyss.checkpoint_status.v1",
        "clean": is_clean,
        "files_modified": parsed["files_modified"],
        "files_added": parsed["files_added"],
        "files_deleted": parsed["files_deleted"],
        "files_untracked": parsed["files_untracked"],
        "diff_stat": diff_stat_output.strip(),
        "diff_staged_stat": diff_staged_stat_output.strip(),
    }


def render_checkpoint_status_json() -> str:
    """Return checkpoint status as a JSON string."""
    return json.dumps(checkpoint_status(), ensure_ascii=False, indent=2)
