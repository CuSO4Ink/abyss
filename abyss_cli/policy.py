from __future__ import annotations

from functools import lru_cache
from typing import Any

from .utils import normalize_rel_path, read_record, repo_root

POLICY_FILE = repo_root() / "rules" / "policy.yaml"


@lru_cache(maxsize=1)
def load_policy() -> dict[str, Any]:
    return read_record(POLICY_FILE)


def _decision(policy: dict[str, Any], risk: str) -> str:
    return str(policy.get("decisions", {}).get(risk, "review"))


def _result(policy: dict[str, Any], risk: str, reason: str) -> tuple[str, str, str]:
    return risk, _decision(policy, risk), reason


def _capability_risk(policy: dict[str, Any], capability: str) -> tuple[str, str] | None:
    capabilities = policy.get("capabilities", {})
    mapping = [
        ("deny", "L5", "Denied capability"),
        ("review_l4", "L4", "External or publication side effect requires review"),
        ("review_l3", "L3", "Capability requires review"),
        ("allow_l0", "L0", "No state-changing side effect"),
        ("allow_l1", "L1", "Read-only action"),
    ]
    for group, risk, reason in mapping:
        if capability in set(capabilities.get(group, [])):
            if group in {"deny", "review_l3"}:
                reason = f"{reason}: {capability}"
            return risk, reason
    return None


def _path_escapes_repo(path: str) -> bool:
    return path.startswith("../") or ":/" in path or ":\\" in path


def classify_action(action: dict) -> tuple[str, str, str]:
    policy = load_policy()
    capability = str(action.get("capability", "")).strip()
    operation = str(action.get("operation", "")).strip().lower()
    path = normalize_rel_path(str(action.get("path", "")))
    path_lower = path.lower()

    path_constraints = policy.get("path_constraints", {})
    sensitive_patterns = path_constraints.get("sensitive_patterns", [])
    if any(str(pattern).lower() in path_lower for pattern in sensitive_patterns):
        return _result(policy, "L5", "Target path appears sensitive")

    if path_constraints.get("deny_absolute_or_repo_escape", True) and _path_escapes_repo(path):
        return _result(policy, "L5", "Target path escapes repository or is absolute")

    cap_match = _capability_risk(policy, capability)
    if cap_match:
        risk, reason = cap_match
        return _result(policy, risk, reason)

    write_rule = policy.get("write_rules", {}).get(capability)
    if write_rule and operation in set(write_rule.get("safe_operations", [])):
        safe_prefixes = path_constraints.get("safe_create_prefixes", [])
        if any(path.startswith(prefix) for prefix in safe_prefixes):
            return _result(policy, str(write_rule.get("safe_prefix_risk", "L2")), "Create/append inside safe artifact path")
        return _result(policy, str(write_rule.get("outside_safe_prefix_risk", "L3")), "Write outside safe create prefixes requires review")

    default_risk = str(policy.get("default_risk", "L3"))
    return _result(policy, default_risk, "Unknown capability defaults to review")
