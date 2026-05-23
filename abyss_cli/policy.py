from __future__ import annotations

from .utils import normalize_rel_path

SENSITIVE_PATTERNS = [
    ".env",
    "secret",
    "secrets",
    "token",
    "credential",
    "credentials",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".key",
]

SAFE_CREATE_PREFIXES = [
    "artifacts/drafts/",
    "process/imports/",
]

REVIEW_CAPABILITIES = {
    "fs.modify",
    "fs.overwrite",
    "git.commit",
    "git.push",
    "outbound.message",
    "policy.change",
    "prompt.change",
    "memory.write",
}

DENY_CAPABILITIES = {
    "secret.read",
    "credential.export",
    "fs.delete.system",
    "network.untrusted_write",
}


def classify_action(action: dict) -> tuple[str, str, str]:
    capability = str(action.get("capability", "")).strip()
    operation = str(action.get("operation", "")).strip().lower()
    path = normalize_rel_path(str(action.get("path", "")))
    path_lower = path.lower()

    if capability in DENY_CAPABILITIES:
        return "L5", "deny", f"Denied capability: {capability}"

    if any(pattern in path_lower for pattern in SENSITIVE_PATTERNS):
        return "L5", "deny", "Target path appears sensitive"

    if path.startswith("../") or ":/" in path or ":\\" in path:
        return "L5", "deny", "Target path escapes repository or is absolute"

    if capability in {"git.push", "git.commit", "outbound.message"}:
        return "L4", "review", "External or publication side effect requires review"

    if capability in REVIEW_CAPABILITIES:
        return "L3", "review", f"Capability requires review: {capability}"

    if capability == "fs.write" and operation in {"create", "append"}:
        if any(path.startswith(prefix) for prefix in SAFE_CREATE_PREFIXES):
            return "L2", "allow", "Create/append inside safe artifact path"
        return "L3", "review", "Write outside safe create prefixes requires review"

    if capability in {"summarize", "reason", "prompt.build"}:
        return "L0", "allow", "No state-changing side effect"

    if capability in {"fs.read", "git.diff", "git.status"}:
        return "L1", "allow", "Read-only action"

    return "L3", "review", "Unknown capability defaults to review"
