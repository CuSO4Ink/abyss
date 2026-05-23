from __future__ import annotations

import re
from pathlib import Path

from .utils import list_records, read_record, repo_root

REQUIRED_DIRS = [
    "rules",
    "prompts/system",
    "prompts/modes",
    "process/intents",
    "process/prompt_packages",
    "process/actions",
    "process/reviews",
    "process/imports",
    "audit",
    "artifacts/drafts",
    "abyss_cli",
]

SENSITIVE_NAME_PARTS = [".env", "secret", "token", "credential", "id_rsa", "id_ed25519"]


def run_checks() -> tuple[bool, list[str]]:
    root = repo_root()
    messages: list[str] = []
    ok = True

    for rel in REQUIRED_DIRS:
        if not (root / rel).exists():
            ok = False
            messages.append(f"MISSING_DIR {rel}")

    for directory in [root / "process" / "intents", root / "process" / "actions", root / "process" / "reviews"]:
        for path in list_records(directory):
            try:
                record = read_record(path)
                if "id" not in record or "schema" not in record:
                    ok = False
                    messages.append(f"INVALID_RECORD_FIELDS {path.relative_to(root)}")
            except Exception as exc:
                ok = False
                messages.append(f"INVALID_JSON_YAML {path.relative_to(root)} {exc}")

    action_ids = {read_record(p).get("id") for p in list_records(root / "process" / "actions")}
    for review_path in list_records(root / "process" / "reviews"):
        review = read_record(review_path)
        if review.get("action_id") not in action_ids:
            ok = False
            messages.append(f"BROKEN_REVIEW_REF {review_path.relative_to(root)} -> {review.get('action_id')}")

    governance_path = root / "rules" / "governance.yaml"
    if governance_path.exists():
        try:
            governance = read_record(governance_path)
            mode = governance.get("direct_modification_mode")
            if mode not in {"transitional", "disabled"}:
                ok = False
                messages.append(f"INVALID_GOVERNANCE_MODE {mode}")
            if mode == "disabled" and not governance.get("ordinary_system_changes_require_evolution_chain"):
                ok = False
                messages.append("INVALID_GOVERNANCE_FINALIZED_FLAG")
            if mode == "disabled" and not governance.get("finalized_at"):
                ok = False
                messages.append("INVALID_GOVERNANCE_FINALIZED_AT")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_GOVERNANCE_FILE {exc}")

    roadmap_path = root / "ROADMAP.md"
    if roadmap_path.exists():
        roadmap_text = roadmap_path.read_text(encoding="utf-8")
        proposal_refs = re.findall(r"Source proposal: `([^`]+)`", roadmap_text)
        for proposal_id in proposal_refs:
            if not proposal_id.startswith("evo_prop_"):
                ok = False
                messages.append(f"INVALID_ROADMAP_PROPOSAL_REF {proposal_id}")
        for proposal_id in sorted({item for item in proposal_refs if proposal_refs.count(item) > 1}):
            ok = False
            messages.append(f"DUPLICATE_ROADMAP_PROPOSAL_REF {proposal_id}")

    tracked = []
    try:
        import subprocess
        proc = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        tracked = proc.stdout.splitlines()
    except Exception:
        tracked = []

    for rel in tracked:
        lowered = rel.lower()
        if any(part in lowered for part in SENSITIVE_NAME_PARTS):
            ok = False
            messages.append(f"SENSITIVE_TRACKED_PATH {rel}")

    if ok:
        messages.append("OK")
    return ok, messages
