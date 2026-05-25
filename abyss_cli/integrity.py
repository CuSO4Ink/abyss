from __future__ import annotations

import re
from pathlib import Path

from .disclosure import audit_context_manifest
from .request_rules import validate_request_rules_config
from .schema_validator import validate_schema_file
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
    "ABYSS.md",
    "ABYSS_CONSTITUTION.md",
    "README.md",
    "SYSTEM_MAP.md",
    "rules/capabilities.yaml",
    "rules/agents.yaml",
    "rules/modules.yaml",
    "rules/context_manifest.yaml",
    "rules/architecture_cognition.yaml",
    "rules/request_types.v1.yaml",
    "rules/contracts/change_set.v1.yaml",
    "rules/contracts/context_request.v1.yaml",
    "rules/contracts/blocked_result.v1.yaml",
    "rules/contracts/harness_review.v1.yaml",
    "rules/contracts/evolution_analysis.v1.yaml",
    "rules/contracts/context_pack.v1.yaml",
    "rules/contracts/external_work_feedback_card.v1.yaml",
    "rules/contracts/request_envelope.v1.yaml",
    "rules/schemas/change_set.v1.schema.json",
    "rules/schemas/context_request.v1.schema.json",
    "rules/schemas/blocked_result.v1.schema.json",
    "rules/schemas/harness_review.v1.schema.json",
    "rules/schemas/evolution_analysis.v1.schema.json",
    "rules/schemas/context_pack.v1.schema.json",
    "rules/schemas/external_work_feedback_card.v1.schema.json",
    "rules/schemas/request_envelope.v1.schema.json",
]


SENSITIVE_NAME_PARTS = [".env", "secret", "token", "credential", "id_rsa", "id_ed25519"]

MODULE_CAPSULE_REQUIRED_FIELDS = [
    "files",
    "responsibility",
    "inputs",
    "outputs",
    "permissions",
    "dependencies",
    "risk_level",
    "validation",
    "failure_modes",
    "observability",
    "runtime_records",
    "allowed_callers",
    "forbidden_actions",
    "invariants",
]

EXPECTED_CONTRACT_IDS = {
    "rules/contracts/change_set.v1.yaml": "abyss.change_set.v1",
    "rules/contracts/context_request.v1.yaml": "abyss.context_request.v1",
    "rules/contracts/blocked_result.v1.yaml": "abyss.blocked_result.v1",
    "rules/contracts/harness_review.v1.yaml": "abyss.harness_review.v1",
    "rules/contracts/evolution_analysis.v1.yaml": "abyss.evolution_analysis.v1",
    "rules/contracts/context_pack.v1.yaml": "abyss.context_pack.v1",
    "rules/contracts/external_work_feedback_card.v1.yaml": "abyss.external_work_feedback_card.v1",
    "rules/contracts/request_envelope.v1.yaml": "abyss.request_envelope.v1",
}

EXPECTED_SCHEMA_IDS = {
    "rules/schemas/change_set.v1.schema.json": "abyss.change_set.v1",
    "rules/schemas/context_request.v1.schema.json": "abyss.context_request.v1",
    "rules/schemas/blocked_result.v1.schema.json": "abyss.blocked_result.v1",
    "rules/schemas/harness_review.v1.schema.json": "abyss.harness_review.v1",
    "rules/schemas/evolution_analysis.v1.schema.json": "abyss.evolution_analysis.v1",
    "rules/schemas/context_pack.v1.schema.json": "abyss.context_pack.v1",
    "rules/schemas/external_work_feedback_card.v1.schema.json": "abyss.external_work_feedback_card.v1",
    "rules/schemas/request_envelope.v1.schema.json": "abyss.request_envelope.v1",
}


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
        if status not in {"implementation_pending", "implementation_running", "changeset_proposed", "dry_run_passed", "harness_review_running", "waiting_owner_approval", "approved_for_execution", "executing", "checking", "done", "failed", "blocked", "rejected", "superseded"}:
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

    # Cognition layer and minimum-disclosure checks
    readme_path = root / "README.md"
    if readme_path.exists():
        try:
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")[:1000]
            if "ABYSS.md" not in readme_text:
                ok = False
                messages.append("README_DOES_NOT_POINT_TO_ABYSS_ENTRYPOINT")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_README_FILE {exc}")

    architecture_path = root / "rules" / "architecture_cognition.yaml"
    if architecture_path.exists():
        try:
            architecture_text = architecture_path.read_text(encoding="utf-8", errors="replace")
            for required_text in [
                "entrypoint: ABYSS.md",
                "rules/contracts/",
                ".local/knot_provider_workspace",
                "authoritative_runtime_process_path: .local/runtime/process/",
                "non_authoritative_process_skeleton: process/",
            ]:
                if required_text not in architecture_text:
                    ok = False
                    messages.append(f"ARCHITECTURE_COGNITION_MISSING_TEXT {required_text}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_ARCHITECTURE_COGNITION_FILE {exc}")

    for rel, contract_id in EXPECTED_CONTRACT_IDS.items():
        path = root / rel
        if path.exists():
            try:
                contract = read_record(path)
                if contract.get("schema") != "abyss.contract.v1":
                    ok = False
                    messages.append(f"INVALID_CONTRACT_SCHEMA {rel} {contract.get('schema')}")
                if contract.get("contract_id") != contract_id:
                    ok = False
                    messages.append(f"INVALID_CONTRACT_ID {rel} {contract.get('contract_id')}")
                if not contract.get("hard_boundaries"):
                    ok = False
                    messages.append(f"CONTRACT_MISSING_HARD_BOUNDARIES {rel}")
            except Exception as exc:
                ok = False
                messages.append(f"INVALID_CONTRACT_FILE {rel} {exc}")

    for rel, schema_id in EXPECTED_SCHEMA_IDS.items():
        path = root / rel
        if path.exists():
            for schema_error in validate_schema_file(path):
                ok = False
                messages.append(f"INVALID_JSON_SCHEMA {rel} {schema_error}")
            try:
                schema = read_record(path)
                if schema.get("$id") != schema_id:
                    ok = False
                    messages.append(f"INVALID_JSON_SCHEMA_ID {rel} {schema.get('$id')}")
            except Exception as exc:
                ok = False
                messages.append(f"INVALID_JSON_SCHEMA_FILE {rel} {exc}")

    for request_rule_error in validate_request_rules_config():
        ok = False
        messages.append(request_rule_error)

    modules_path = root / "rules" / "modules.yaml"

    if modules_path.exists():
        try:
            modules_config = read_record(modules_path)
            if modules_config.get("schema") not in {"abyss.module_manifest.v1", "abyss.module_manifest.v2"}:
                ok = False
                messages.append(f"INVALID_MODULES_SCHEMA {modules_config.get('schema')}")
            modules = modules_config.get("modules", {})
            if not isinstance(modules, dict):
                ok = False
                messages.append("INVALID_MODULES_MAP")
            else:
                for module_name, module_spec in modules.items():
                    if not isinstance(module_spec, dict):
                        ok = False
                        messages.append(f"INVALID_MODULE_SPEC {module_name}")
                        continue
                    for field in MODULE_CAPSULE_REQUIRED_FIELDS:
                        if field not in module_spec:
                            ok = False
                            messages.append(f"MODULE_CAPSULE_MISSING_FIELD {module_name}.{field}")
                    for file_rel in module_spec.get("files", []) if isinstance(module_spec.get("files"), list) else []:
                        if not (root / str(file_rel)).exists():
                            ok = False
                            messages.append(f"MODULE_FILE_MISSING {module_name} {file_rel}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_MODULES_FILE {exc}")

    context_manifest_path = root / "rules" / "context_manifest.yaml"
    if context_manifest_path.exists():
        try:
            context_manifest = read_record(context_manifest_path)
            task_types = context_manifest.get("task_types", {})
            if not isinstance(task_types, dict):
                ok = False
                messages.append("INVALID_CONTEXT_TASK_TYPES")
            else:
                for task_type, spec in task_types.items():
                    if not isinstance(spec, dict):
                        ok = False
                        messages.append(f"INVALID_CONTEXT_TASK_SPEC {task_type}")
                        continue
                    for key in ["required_files", "required_rules"]:
                        values = spec.get(key, [])
                        if not isinstance(values, list):
                            ok = False
                            messages.append(f"INVALID_CONTEXT_{key.upper()} {task_type}")
                            continue
                        for rel in values:
                            rel_str = str(rel)
                            if "*" in rel_str or rel_str.endswith("/"):
                                continue
                            candidate = (root / rel_str).resolve()
                            if not candidate.exists():
                                ok = False
                                messages.append(f"CONTEXT_REF_MISSING {task_type}.{key} {rel_str}")
                            normalized = rel_str.replace("\\", "/")
                            if normalized.startswith(".local/knot_provider_workspace"):
                                ok = False
                                messages.append(f"CONTEXT_REF_PROVIDER_WORKSPACE_DEFAULT {task_type}.{key} {rel_str}")
                            if normalized.startswith(".local/runtime") and task_type not in {"runtime_investigation", "debug", "audit"}:
                                ok = False
                                messages.append(f"CONTEXT_REF_RUNTIME_DEFAULT {task_type}.{key} {rel_str}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_CONTEXT_MANIFEST_FILE {exc}")

    try:
        disclosure_audit = audit_context_manifest()
        for warning in disclosure_audit.get("warnings", []):
            ok = False
            messages.append(f"DISCLOSURE_AUDIT_WARNING {warning}")
    except Exception as exc:
        ok = False
        messages.append(f"DISCLOSURE_AUDIT_FAILED {exc}")

    # Validate task_coverage_manifest schema in context_manifest if present
    if context_manifest_path.exists():
        try:
            cm = read_record(context_manifest_path)
            coverage_schema = cm.get("task_coverage_manifest_schema")
            if coverage_schema and isinstance(coverage_schema, dict):
                required_schema_fields = coverage_schema.get("required_fields", [])
                if not isinstance(required_schema_fields, list) or not required_schema_fields:
                    pass  # Schema is optional; no error if absent
                # Validate that the schema declaration is structurally sound
                allowed_field_types = {"expected_files", "expected_domains"}
                declared_fields = set(required_schema_fields)
                unknown_fields = declared_fields - allowed_field_types - {"schema"}
                for uf in sorted(unknown_fields):
                    messages.append(f"COVERAGE_MANIFEST_SCHEMA_UNKNOWN_FIELD {uf}")
        except Exception:
            pass  # Coverage manifest schema is optional; parse errors handled above

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
            brain = agents.get("brain") if isinstance(agents, dict) else None
            if not isinstance(brain, dict):
                ok = False
                messages.append("MISSING_BRAIN_AGENT_CONTRACT")
            else:
                if brain.get("enabled") is not False:
                    ok = False
                    messages.append("BRAIN_AGENT_MUST_REMAIN_DISABLED_IN_V0")
                forbidden = set(brain.get("forbidden", [])) if isinstance(brain.get("forbidden"), list) else set()
                for required_forbidden in ["approve_roadmap_item", "approve_changeset", "apply_changeset", "modify_files", "bypass_harness", "replace_owner", "run_commands"]:
                    if required_forbidden not in forbidden:
                        ok = False
                        messages.append(f"BRAIN_AGENT_MISSING_FORBIDDEN {required_forbidden}")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_AGENTS_FILE {exc}")

    llm_providers_path = root / "rules" / "llm_providers.yaml"
    if llm_providers_path.exists():
        try:
            llm_providers = read_record(llm_providers_path)
            if llm_providers.get("schema") != "abyss.llm_providers.v2":
                ok = False
                messages.append(f"INVALID_LLM_PROVIDERS_SCHEMA {llm_providers.get('schema')}")
            providers = llm_providers.get("providers", {})
            cli_provider = providers.get("cli") if isinstance(providers, dict) else None
            if not isinstance(cli_provider, dict):
                ok = False
                messages.append("MISSING_CLI_PROVIDER")
            else:
                if not isinstance(cli_provider.get("model", ""), str):
                    ok = False
                    messages.append("INVALID_CLI_PROVIDER_MODEL")
                if not isinstance(cli_provider.get("model_argument", "--model"), str):
                    ok = False
                    messages.append("INVALID_CLI_PROVIDER_MODEL_ARGUMENT")
        except Exception as exc:
            ok = False
            messages.append(f"INVALID_LLM_PROVIDERS_FILE {exc}")

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