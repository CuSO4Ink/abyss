from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .audit import append_event
from .utils import ensure_dir, repo_root

CONFIG_PATH = repo_root() / ".local" / "data_sync.json"
DEFAULT_DATA_REPO_PATH = Path.home() / "Documents" / "abyss-data"
DEFAULT_DATA_REPO_URL = "git@github-personal:CuSO4Ink/abyss-data.git"


def _run_git(repo: Path, args: list[str], allow_fail: bool = False) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 and not allow_fail:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"git failed: {' '.join(args)}")
    return (proc.stdout or proc.stderr).strip()


def _run_git_global(args: list[str], allow_fail: bool = False) -> str:
    proc = subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 and not allow_fail:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"git failed: {' '.join(args)}")
    return (proc.stdout or proc.stderr).strip()


def _remote_branch_exists(repo_url: str, branch: str) -> bool:
    proc = subprocess.run(
        ["git", "ls-remote", "--heads", repo_url, branch],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"git ls-remote failed: {repo_url}")
    return bool(proc.stdout.strip())


def _has_any_commit(repo: Path) -> bool:
    _run_git(repo, ["rev-parse", "--verify", "HEAD"], allow_fail=True)
    output = _run_git(repo, ["rev-list", "--count", "--all"], allow_fail=True)
    return output.strip() not in {"", "0"}


def _ensure_data_structure(data_path: Path) -> None:
    ensure_dir(data_path / "user_data")
    ensure_dir(data_path / "storage" / "archive")

    files = {
        "README.md": "# Abyss Data\n\nPrivate user data repository for Abyss.\n\n- `user_data/`: active Obsidian-facing knowledge surface.\n- `storage/archive/`: dormant archived material, hidden from default retrieval.\n",
        "user_data/README.md": "# User Data\n\nActive Obsidian-facing notes, current directions, working summaries, and decision records.\n",
        "storage/README.md": "# Storage\n\nHidden-by-default storage layer for inactive or bulky material.\n",
        "storage/archive/README.md": "# Archive\n\nLong-term archived material. Promote focused excerpts into `user_data/` when needed.\n",
    }
    for rel, content in files.items():
        path = data_path / rel
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def _ensure_initial_commit(data_path: Path, branch: str) -> str | None:
    _run_git(data_path, ["checkout", "-B", branch])
    _ensure_data_structure(data_path)
    _run_git(data_path, ["add", "README.md", "user_data", "storage"])
    staged = _run_git(data_path, ["diff", "--cached", "--name-only"], allow_fail=True)
    if staged:
        _run_git(data_path, ["commit", "-m", "initialize abyss data repository"])
    if _has_any_commit(data_path):
        return _run_git(data_path, ["push", "-u", "origin", branch])
    return None


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit("Data sync is not configured. Run: abyss data init")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    ensure_dir(CONFIG_PATH.parent)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configured_data_path() -> Path:
    config = load_config()
    return Path(config["data_repo_path"]).expanduser().resolve()


def init_data_repo(repo_url: str | None = None, path: str | None = None, branch: str = "main") -> dict:
    repo_url = repo_url or DEFAULT_DATA_REPO_URL
    data_path = Path(path).expanduser().resolve() if path else DEFAULT_DATA_REPO_PATH
    config = {
        "schema": "abyss.data_sync_config.v1",
        "data_repo_url": repo_url,
        "data_repo_path": str(data_path),
        "branch": branch,
        "auto_pull_on_bootstrap": True,
    }

    if data_path.exists() and (data_path / ".git").exists():
        _run_git(data_path, ["fetch", "--all", "--prune"], allow_fail=True)
        _run_git(data_path, ["checkout", branch], allow_fail=True)
        _run_git(data_path, ["pull", "--ff-only"], allow_fail=True)
        if not _has_any_commit(data_path):
            _ensure_initial_commit(data_path, branch)
        else:
            _ensure_data_structure(data_path)
        action = "configured_existing_repo"
    elif data_path.exists() and any(data_path.iterdir()):
        raise SystemExit(f"Data path exists and is not empty: {data_path}")
    else:
        ensure_dir(data_path.parent)
        if _remote_branch_exists(repo_url, branch):
            _run_git_global(["clone", "--branch", branch, repo_url, str(data_path)])
            _ensure_data_structure(data_path)
            action = "cloned_repo"
        else:
            _run_git_global(["clone", repo_url, str(data_path)])
            _ensure_initial_commit(data_path, branch)
            action = "initialized_empty_remote_repo"

    save_config(config)
    append_event("data_sync.init", "Configured external data repository", {"path": str(data_path), "action": action})
    return config


def data_status() -> str:
    data_path = configured_data_path()
    if not (data_path / ".git").exists():
        raise SystemExit(f"Configured data path is not a Git repository: {data_path}")
    status = _run_git(data_path, ["status", "--short", "--branch"], allow_fail=True)
    return f"data_repo: {data_path}\n{status}"


def data_pull() -> str:
    data_path = configured_data_path()
    output = _run_git(data_path, ["pull", "--ff-only"])
    append_event("data_sync.pull", "Pulled external data repository", {"path": str(data_path)})
    return output


def data_push(message: str) -> str:
    data_path = configured_data_path()
    if not (data_path / ".git").exists():
        raise SystemExit(f"Configured data path is not a Git repository: {data_path}")

    status = _run_git(data_path, ["status", "--porcelain"], allow_fail=True)
    if not status:
        return "no data changes to push"

    _run_git(data_path, ["add", "user_data", "storage"])
    staged = _run_git(data_path, ["diff", "--cached", "--name-only"], allow_fail=True)
    if not staged:
        return "no tracked data changes to push"

    _run_git(data_path, ["commit", "-m", message])
    output = _run_git(data_path, ["push"])
    append_event("data_sync.push", "Committed and pushed external data repository", {"path": str(data_path), "message": message})
    return output or "pushed data repository"
