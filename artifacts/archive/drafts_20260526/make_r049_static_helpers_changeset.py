from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRITY = ROOT / "abyss_cli" / "integrity.py"
OUT = ROOT / "artifacts" / "drafts" / "chg_r049_corrected_integrity_static_helpers.json"

text = INTEGRITY.read_text(encoding="utf-8")

helpers = '''
def _check_governance_and_capabilities(root: Path, messages: list[str]) -> bool:
    ok = True
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

    return ok


def _check_cognition_surface(root: Path, messages: list[str]) -> bool:
    ok = True
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

    return ok


def _check_contracts_and_rule_sources(root: Path, messages: list[str]) -> bool:
    ok = True
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

    from .rule_registry import validate_rule_sources as _validate_rule_sources
    rule_registry_result = _validate_rule_sources()
    if not rule_registry_result.get("ok"):
        for error in rule_registry_result.get("errors", []):
            ok = False
            messages.append(f"RULE_REGISTRY {error}")

    return ok


def _check_modules_context_and_disclosure(root: Path, messages: list[str]) -> bool:
    ok = True
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

    if context_manifest_path.exists():
        try:
            cm = read_record(context_manifest_path)
            coverage_schema = cm.get("task_coverage_manifest_schema")
            if coverage_schema and isinstance(coverage_schema, dict):
                required_schema_fields = coverage_schema.get("required_fields", [])
                if not isinstance(required_schema_fields, list) or not required_schema_fields:
                    pass
                allowed_field_types = {"expected_files", "expected_domains"}
                declared_fields = set(required_schema_fields)
                unknown_fields = declared_fields - allowed_field_types - {"schema"}
                for uf in sorted(unknown_fields):
                    messages.append(f"COVERAGE_MANIFEST_SCHEMA_UNKNOWN_FIELD {uf}")
        except Exception:
            pass

    return ok


def _check_agents_and_llm_providers(root: Path, messages: list[str]) -> bool:
    ok = True
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

    return ok


def _check_roadmap_refs(root: Path, messages: list[str]) -> bool:
    ok = True
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

    return ok


def _check_sensitive_tracked_paths(root: Path, messages: list[str]) -> bool:
    ok = True
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

    return ok

'''

marker = "def run_checks() -> tuple[bool, list[str]]:"
old_marker = marker
new_marker = helpers + marker
if text.count(old_marker) != 1:
    raise SystemExit(f"marker count mismatch: {text.count(old_marker)}")

start = text.index('    governance_path = root / "rules" / "governance.yaml"')
end = text.index('    if ok:\n        messages.append("OK")', start)
old_tail = text[start:end]
new_tail = '''    if not _check_governance_and_capabilities(root, messages):
        ok = False

    if not _check_cognition_surface(root, messages):
        ok = False

    if not _check_contracts_and_rule_sources(root, messages):
        ok = False

    if not _check_modules_context_and_disclosure(root, messages):
        ok = False

    if not _check_agents_and_llm_providers(root, messages):
        ok = False

    if not _check_roadmap_refs(root, messages):
        ok = False

    if not _check_sensitive_tracked_paths(root, messages):
        ok = False

'''

changeset = {
    "schema": "abyss.change_set.v1",
    "id": "chg_r049_corrected_integrity_static_helpers",
    "roadmap_id": "R049",
    "summary": "Extract static governance, contract, context, agent, roadmap, and sensitive path integrity checks into focused helpers",
    "risk_level": "L2",
    "status": "proposed",
    "operations": [
        {
            "id": "op_001",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/integrity.py"},
            "input": {"old_content": old_marker, "new_content": new_marker},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "op_002",
            "kind": "fs.replace_exact",
            "capability": "fs.write",
            "target": {"path": "abyss_cli/integrity.py"},
            "input": {"old_content": old_tail, "new_content": new_tail},
            "preconditions": ["old_content_matches_once"],
            "rollback": {"strategy": "manual_revert_from_git_diff"},
        },
        {
            "id": "check_001",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": "python -m compileall -q abyss_cli"},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        },
        {
            "id": "check_002",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": "python -m abyss_cli check"},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        },
        {
            "id": "check_003",
            "kind": "check.command",
            "capability": "process.check",
            "target": {"path": "system"},
            "input": {"command": "python -m abyss_cli summary --check"},
            "preconditions": ["changes_applied_before_check"],
            "rollback": {"strategy": "not_applicable"},
        },
    ],
    "created_at": "2026-05-26T09:05:00+08:00",
    "no_action_executed": True,
}

OUT.write_text(json.dumps(changeset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUT)
print(f"old_tail_chars={len(old_tail)} helper_chars={len(helpers)}")
