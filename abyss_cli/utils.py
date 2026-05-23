from __future__ import annotations

import json
import os
import secrets
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BJ_TZ = timezone(timedelta(hours=8))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(BJ_TZ).replace(microsecond=0).isoformat()


def stamp() -> str:
    return datetime.now(BJ_TZ).strftime("%Y%m%d_%H%M%S")


def new_id(prefix: str) -> str:
    return f"{prefix}_{stamp()}_{secrets.token_hex(3)}"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_record(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_records(directory: Path, prefix: str | None = None) -> list[Path]:
    if not directory.exists():
        return []
    files = [p for p in directory.glob("*.yaml") if p.is_file()]
    if prefix:
        files = [p for p in files if p.name.startswith(prefix)]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def latest_record(directory: Path, prefix: str | None = None) -> Path | None:
    files = list_records(directory, prefix)
    return files[-1] if files else None


def resolve_record_arg(directory: Path, value: str, prefix: str | None = None) -> Path:
    if value == "latest":
        latest = latest_record(directory, prefix)
        if not latest:
            raise SystemExit(f"No records found in {directory}")
        return latest

    candidate = directory / value
    if candidate.exists():
        return candidate

    if not value.endswith(".yaml"):
        candidate = directory / f"{value}.yaml"
        if candidate.exists():
            return candidate

    matches = [p for p in list_records(directory, prefix) if p.stem == value or p.stem.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit(f"Ambiguous record id {value}: " + ", ".join(p.stem for p in matches))
    raise SystemExit(f"Record not found: {value}")


def run_git(args: list[str], allow_fail: bool = False) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root()), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 and not allow_fail:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"git failed: {' '.join(args)}")
    return (proc.stdout or proc.stderr).strip()


def relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return str(path)


def normalize_rel_path(raw: str) -> str:
    return raw.replace("\\", "/").lstrip("/")


def copy_to_clipboard(text: str) -> bool:
    if os.name != "nt":
        return False
    proc = subprocess.run("clip", input=text, text=True, shell=True)
    return proc.returncode == 0
