from __future__ import annotations

import re
from pathlib import Path

from .utils import list_records, read_record, repo_root, runtime_root

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

REQUIRED_FILES = [
    "rules/capabilities.yaml",
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

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            ok = False
            messages.append(f"MISSING_FILE {rel}")

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

    runtime = runtime_root()
    for directory in [
        runtime / "process" / "changesets",
        runtime / "process" / "executions",
        runtime / "process" / "workflows",
        runtime / "process" / "owner_inbox",
        runtime / "process" / "reports",
    ]:
        for path in list_records(directory):
            try:
                record = read_record(path)
                if "id" not in record or "schema" not in record:
                    ok = False
                    messages.append(f"INVALID_RUNTIME_RECORD_FIELDS {path.relative_to(root)}")
            except Exception as exc:
                ok = False
                messages.append(f"INVALID_RUNTIME_JSON_YAML {path.relative_to(root)} {exc}")

    changeset_ids = {read_record(p).get("id") for p in list_records(runtime / "process" / "changesets", "chg")}
    execution_ids = {read_record(p).get("id") for p in list_records(runtime / "process" / "executions", "exec")}
    workflow_ids = {read_record(p).get("id") for p in list_records(runtime / "process" / "workflows", "wf")}
    owner_ids = {read_record(p).get("id") for p in list_records(runtime / "process" / "owner_inbox", "owner")}
    for execution_path in list_records(runtime / "process" / "executions", "exec"):
        execution = read_record(execution_path)
        if execution.get("changeset_id") not in changeset_ids:
            ok = False
            messages.append(f"BROKEN_EXECUTION_REF {execution_path.relative_to(root)} -> {execution.get('changeset_id')}")

    for workflow_path in list_records(runtime / "process" / "workflows", "wf"):
        workflow = read_record(workflow_path)
        status = workflow.get("status")
        if status not in {"implementation_pending", "implementation_running", "changeset_proposed", "dry_run_passed", "harness_review_running", "waiting_owner_approval", "approved_for_execution", "executing", "checking", "done", "failed", "blocked", "rejected"}:
            ok = False
            messages.append(f"INVALID_WORKFLOW_STATUS {workflow_path.relative_to(root)} {status}")
        if workflow.get("changeset_id") and workflow.get("changeset_id") not in changeset_ids:
            ok = False
            messages.append(f"BROKEN_WORKFLOW_CHANGESET_REF {workflow_path.relative_to(root)} -> {workflow.get('changeset_id')}")
        if workflow.get("owner_item_id") and workflow.get("owner_item_id") not in owner_ids:
            ok = False
            messages.append(f"BROKEN_WORKFLOW_OWNER_REF {workflow_path.relative_to(root)} -> {workflow.get('owner_item_id')}")
        if workflow.get("execution_id") and workflow.get("execution_id") not in execution_ids:
            ok = False
            messages.append(f"BROKEN_WORKFLOW_EXECUTION_REF {workflow_path.relative_to(root)} -> {workflow.get('execution_id')}")

    for owner_path in list_records(runtime / "process" / "owner_inbox", "owner"):
        owner_item = read_record(owner_path)
        if owner_item.get("workflow_id") not in workflow_ids:
            ok = False
            messages.append(f"BROKEN_OWNER_WORKFLOW_REF {owner_path.relative_to(root)} -> {owner_item.get('workflow_id')}")
        if owner_item.get("target_id") and owner_item.get("target_id") not in changeset_ids:
            ok = False
            messages.append(f"BROKEN_OWNER_CHANGESET_REF {owner_path.relative_to(root)} -> {owner_item.get('target_id')}")

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

    capabilities_path = root / "rules" / "capabilities.yaml"
    if capabilities_path.exists():
        try:
            capabilities = read_record(capabilities_path)
            if capabilities.get("schema") != "abyss.capabilities.v1":
                ok = False
                messages.append(f"INVALID_CAPABILITIES_SCHEMA {capabilities.get('schema')}")
            executor = capabilities.get("executor_capabilities", {})
            blocked = set(executor.get("blocked_now", [])) if isinstance(executor, dict) else set()
            for required_block in ["shell.command", "browser.automation", "git.push", "policy.modify", "prompt.modify", "governance.modify"]:
                if required_block not in blocked:
                    ok = False
                    messages.append(f"MISSING_BLOCKED_CAPABILITY {required_block}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_CAPABILITIES_FILE {exc}")

    agents_path = root / "rules" / "agents.yaml"
    if agents_path.exists():
        try:
            agents_config = read_record(agents_path)
            if agents_config.get("schema") != "abyss.agents.v1":
                ok = False
                messages.append(f"INVALID_AGENTS_SCHEMA {agents_config.get('schema')}")
            agents = agents_config.get("agents", {})
            for required_agent in ["harness", "self_evolution", "implementation"]:
                spec = agents.get(required_agent) if isinstance(agents, dict) else None
                if not isinstance(spec, dict) or not spec.get("enabled"):
                    ok = False
                    messages.append(f"MISSING_ENABLED_AGENT {required_agent}")
                    continue
                role_prompt = root / str(spec.get("role_prompt") or "")
                if not role_prompt.exists():
                    ok = False
                    messages.append(f"MISSING_AGENT_ROLE_PROMPT {required_agent} {role_prompt.relative_to(root) if role_prompt.is_relative_to(root) else role_prompt}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_AGENTS_FILE {exc}")

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
