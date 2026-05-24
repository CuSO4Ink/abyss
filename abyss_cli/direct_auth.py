from __future__ import annotations

import getpass
import hashlib
import hmac
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from .audit import append_event
from .utils import BJ_TZ, list_records, new_id, now_iso, read_record, runtime_root, write_record

DIRECT_AUTH_DIR = runtime_root() / "process" / "direct_modification_auth"
SECRET_PATH = DIRECT_AUTH_DIR / "secret.yaml"
TICKETS_DIR = DIRECT_AUTH_DIR / "tickets"

ALLOWED_SCOPES = {
    "bootstrap_fix",
    "diagnostics",
    "emergency_repair",
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_secret(prompt: str = "Direct modification authorization secret: ") -> str:
    first = getpass.getpass(prompt)
    if not first:
        raise SystemExit("Secret must not be empty")
    return first


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _ticket_path(ticket_id: str) -> Path:
    return TICKETS_DIR / f"{ticket_id}.yaml"


def init_direct_auth(*, force: bool = False, owner: str = "user") -> dict[str, Any]:
    if SECRET_PATH.exists() and not force:
        raise SystemExit("Direct modification auth secret already exists. Use --force to rotate it.")
    first = _read_secret("New direct modification authorization secret: ")
    second = getpass.getpass("Confirm secret: ")
    if first != second:
        raise SystemExit("Secret confirmation did not match")
    salt = secrets.token_hex(16)
    record = {
        "schema": "abyss.direct_modification_secret.v1",
        "id": "direct_modification_secret",
        "owner": owner,
        "salt": salt,
        "secret_hash": _sha256(salt + first),
        "hash_algorithm": "sha256(salt + secret)",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    write_record(SECRET_PATH, record)
    append_event("direct_auth.secret.initialized", "Direct modification authorization secret initialized", {"owner": owner, "rotated": force})
    public = {k: v for k, v in record.items() if k != "secret_hash"}
    public["secret_configured"] = True
    return public


def _load_secret_record() -> dict[str, Any]:
    if not SECRET_PATH.exists():
        raise SystemExit("Direct modification auth secret is not initialized. Run: abyss direct-auth init")
    return read_record(SECRET_PATH)


def _verify_secret(secret: str) -> None:
    record = _load_secret_record()
    expected = str(record.get("secret_hash") or "")
    actual = _sha256(str(record.get("salt") or "") + secret)
    if not hmac.compare_digest(expected, actual):
        append_event("direct_auth.secret.rejected", "Direct modification authorization secret rejected", {})
        raise SystemExit("Invalid direct modification authorization secret")


def authorize_direct_modification(*, scope: str, reason: str, ttl_minutes: int = 30, operator: str = "user") -> dict[str, Any]:
    if scope not in ALLOWED_SCOPES:
        raise SystemExit(f"Unsupported scope: {scope}. Allowed: {', '.join(sorted(ALLOWED_SCOPES))}")
    ttl = max(1, min(int(ttl_minutes), 120))
    if not reason.strip():
        raise SystemExit("Authorization reason is required")
    secret = _read_secret()
    _verify_secret(secret)
    now = datetime.now(BJ_TZ).replace(microsecond=0)
    expires = now.timestamp() + ttl * 60
    ticket = {
        "schema": "abyss.direct_modification_authorization.v1",
        "id": new_id("dauth"),
        "scope": scope,
        "reason": reason.strip(),
        "status": "active",
        "operator": operator,
        "created_at": now.isoformat(),
        "expires_at": datetime.fromtimestamp(expires, BJ_TZ).replace(microsecond=0).isoformat(),
        "ttl_minutes": ttl,
        "allowed_actions": [
            "manual_bootstrap_file_edits_within_reason",
            "run_local_validation_checks",
            "record_audit_evidence",
        ],
        "forbidden_actions": [
            "production_network_access",
            "external_write_interfaces_except_standard_llm_invocation",
            "git_push_or_publish",
            "secret_exfiltration",
            "broad_unscoped_refactor",
        ],
    }
    write_record(_ticket_path(str(ticket["id"])), ticket)
    append_event("direct_auth.authorized", "Direct modification authorization created", {"ticket_id": ticket["id"], "scope": scope, "expires_at": ticket["expires_at"]})
    return ticket


def list_direct_authorizations(*, include_expired: bool = False) -> list[dict[str, Any]]:
    now = datetime.now(BJ_TZ).replace(microsecond=0)
    records: list[dict[str, Any]] = []
    for path in list_records(TICKETS_DIR, "dauth"):
        record = read_record(path)
        try:
            expired = _parse_iso(str(record.get("expires_at"))) <= now
        except Exception:
            expired = True
        if expired and record.get("status") == "active":
            record["status"] = "expired"
            record["updated_at"] = now_iso()
            write_record(path, record)
        if include_expired or record.get("status") == "active":
            records.append(record)
    return records


def direct_auth_status() -> dict[str, Any]:
    active = list_direct_authorizations(include_expired=False)
    return {
        "schema": "abyss.direct_modification_auth_status.v1",
        "secret_configured": SECRET_PATH.exists(),
        "active_authorizations": active,
        "created_at": now_iso(),
    }
