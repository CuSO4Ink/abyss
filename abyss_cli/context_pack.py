"""Context Broker V0: Context Pack generation for Abyss agents.

Responsible for:
- Building context packs based on task type and module manifest
- Providing system brief to all governance agents
- Recording context pack metadata for audit
- Detecting task type from proposal/request text
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from .utils import new_id, now_iso, read_record, repo_root, runtime_root, write_record
from .disclosure import build_disclosure_plan

CONTEXT_PACKS_DIR = runtime_root() / "process" / "context_packs"

# Rule file paths
SYSTEM_BRIEF_FILE = repo_root() / "rules" / "system_brief.yaml"
MODULES_FILE = repo_root() / "rules" / "modules.yaml"
CONTEXT_MANIFEST_FILE = repo_root() / "rules" / "context_manifest.yaml"
ARCHITECTURE_COGNITION_FILE = repo_root() / "rules" / "architecture_cognition.yaml"
CONTEXT_CONTENT_BUDGET_WARN = 120000


def validate_task_coverage_manifest(
    target_record: dict[str, Any],
    context_pack: dict[str, Any],
) -> dict[str, Any]:
    """Validate declared coverage manifest against the built context pack.

    If the target record declares a `task_coverage_manifest` field, this function
    checks that every declared expected file/domain is present in the context pack's
    files_included list. Returns a structured coverage report.

    This validator is deterministic and conservative:
    - It does not perform semantic retrieval.
    - It does not grant execution or approval authority.
    - It only compares declared targets against included files.
    """
    manifest = target_record.get("task_coverage_manifest")
    if not manifest or not isinstance(manifest, dict):
        return {"schema": "abyss.coverage_check.v1", "has_manifest": False, "ok": True, "missing": [], "warnings": []}

    allowed_fields = {
        "expected_files",
        "expected_domains",
        "inferred_task_type",
        "inference_method",
    }
    required_fields = {"expected_files", "expected_domains"}

    warnings: list[str] = []
    unknown_fields = sorted(set(manifest.keys()) - allowed_fields)
    for field in unknown_fields:
        warnings.append(f"COVERAGE_MANIFEST_UNKNOWN_FIELD {field}")

    missing_required_fields = sorted(field for field in required_fields if field not in manifest)
    for field in missing_required_fields:
        warnings.append(f"COVERAGE_MANIFEST_MISSING_REQUIRED_FIELD {field}")

    expected_files_raw = manifest.get("expected_files", [])
    expected_domains_raw = manifest.get("expected_domains", [])

    if isinstance(expected_files_raw, list):
        expected_files: list[str] = []
        for index, item in enumerate(expected_files_raw):
            if isinstance(item, str):
                expected_files.append(item)
            else:
                warnings.append(f"COVERAGE_MANIFEST_INVALID_EXPECTED_FILE index={index} type={type(item).__name__}")
    else:
        expected_files = []
        warnings.append(f"COVERAGE_MANIFEST_INVALID_FIELD_TYPE expected_files type={type(expected_files_raw).__name__}")

    if isinstance(expected_domains_raw, list):
        expected_domains: list[str] = []
        for index, item in enumerate(expected_domains_raw):
            if isinstance(item, str):
                expected_domains.append(item)
            else:
                warnings.append(f"COVERAGE_MANIFEST_INVALID_EXPECTED_DOMAIN index={index} type={type(item).__name__}")
    else:
        expected_domains = []
        warnings.append(f"COVERAGE_MANIFEST_INVALID_FIELD_TYPE expected_domains type={type(expected_domains_raw).__name__}")

    for optional_text_field in ("inferred_task_type", "inference_method"):
        if optional_text_field in manifest and not isinstance(manifest.get(optional_text_field), str):
            warnings.append(f"COVERAGE_MANIFEST_INVALID_FIELD_TYPE {optional_text_field} type={type(manifest.get(optional_text_field)).__name__}")

    included_files: set[str] = set(context_pack.get("files_included", []))
    modules_included: list[str] = context_pack.get("modules_included", [])

    missing_files: list[str] = [f for f in expected_files if f not in included_files]

    # Domain coverage: a domain is considered covered if at least one module
    # from that domain is included in the context pack's modules_included list.
    # Domain names map to module names in the module manifest.
    missing_domains: list[str] = [d for d in expected_domains if d not in modules_included]

    for f in missing_files:
        warnings.append(f"COVERAGE_MANIFEST_MISSING_FILE {f}")
    for d in missing_domains:
        warnings.append(f"COVERAGE_MANIFEST_MISSING_DOMAIN {d}")

    ok = not warnings

    return {
        "schema": "abyss.coverage_check.v1",
        "has_manifest": True,
        "ok": ok,
        "expected_files": expected_files,
        "expected_domains": expected_domains,
        "missing_files": missing_files,
        "missing_domains": missing_domains,
        "warnings": warnings,
    }



def load_system_brief() -> dict[str, Any]:
    """Load the system brief that all governance agents receive."""
    if not SYSTEM_BRIEF_FILE.exists():
        return {"error": "system_brief.yaml not found"}
    return read_record(SYSTEM_BRIEF_FILE)


def load_module_manifest() -> dict[str, Any]:
    """Load the module manifest (module cards/map)."""
    if not MODULES_FILE.exists():
        return {"modules": {}}
    return read_record(MODULES_FILE)


def load_context_manifest() -> dict[str, Any]:
    """Load the context manifest (task type → required context mapping)."""
    if not CONTEXT_MANIFEST_FILE.exists():
        return {"task_types": {}}
    return read_record(CONTEXT_MANIFEST_FILE)


def load_architecture_cognition() -> dict[str, Any]:
    """Load the progressive disclosure cognition protocol as raw evidence.

    The cognition protocol is authored as human-readable YAML and may contain
    fields that are not JSON-compatible. Keep the loader dependency-free by
    preserving the canonical file content instead of trying to interpret it as
    policy truth. Downstream agents receive it as cognition guidance only.
    """
    if not ARCHITECTURE_COGNITION_FILE.exists():
        return {"path": "rules/architecture_cognition.yaml", "exists": False}
    text = ARCHITECTURE_COGNITION_FILE.read_text(encoding="utf-8", errors="replace")
    return {
        "path": "rules/architecture_cognition.yaml",
        "exists": True,
        "size": len(text),
        "content": text,
        "truncated": False,
    }


def detect_task_type(text: str) -> str:
    """Detect task type from proposal/request text using keyword heuristics.

    Specific context/task keywords must win over broad governance words such as
    "evolution".  The score therefore combines match count, keyword length, and
    an optional manifest priority map.
    
    Enhanced for progressive disclosure: prioritize context-related keywords
    and ensure context_broker_feature detection accuracy.
    """
    manifest = load_context_manifest()
    detection = manifest.get("task_type_detection", {})
    keywords_map: dict[str, list[str]] = detection.get("keywords", {})
    priority_map: dict[str, int] = detection.get("priority", {})

    text_lower = text.lower()
    scores: dict[str, tuple[int, int, int]] = {}

    # Brain brief / disclosure-plan / external onboarding readiness tasks need
    # the Brain and Disclosure surfaces in addition to external-collaboration
    # contracts. Detect these before broad context-broker or agent terms so the
    # Implementation Agent receives the exact files it must update.
    brain_onboarding_terms = [
        "brain brief next candidate",
        "brain brief next candidates",
        "disclosure_plan",
        "disclosure plan schema",
        "external_model_onboarding",
        "external model onboarding",
        "canonical direction",
        "global direction internalization",
    ]
    if any(term in text_lower for term in brain_onboarding_terms):
        return "brain_onboarding_readiness"

    # Provider reliability tasks need llm_executor.py. Detect them before Context
    # Broker terms because stabilization proposals may mention "do not continue
    # changing Context Broker coverage" as a boundary rather than as the target.
    provider_reliability_terms = [
        "cli provider",
        "llm provider",
        "provider timeout",
        "provider timed out",
        "timeout or empty-response",
        "empty-response",
        "empty response",
        "empty stdout",
        "_provider_response",
        "llm_executor",
    ]
    if any(term in text_lower for term in provider_reliability_terms):
        return "agent_feature"

    # Workflow list display tasks need workflow.py and __main__.py grounding.
    # Detect these before context_broker_terms because proposals about fixing
    # context coverage for workflow display mention "context broker" as context
    # rather than as the implementation target.
    workflow_display_terms = [
        "workflow list display",
        "workflow status presentation",
        "workflow CLI display",
        "cmd_workflow_list",
    ]
    workflow_display_matches = [term for term in workflow_display_terms if term in text_lower]
    if workflow_display_matches:
        # Check if the proposal is actually about fixing context broker coverage
        # FOR workflow display (R020-type), vs actually changing workflow display (R019-type).
        # If context broker is the implementation target, let context_broker detection win.
        context_is_target = any(term in text_lower for term in [
            "expand context broker coverage",
            "context broker logic",
            "update context broker",
        ])
        if not context_is_target:
            return "summary_feature"

    # Enhanced detection: check for context broker specific terms first, unless the
    # context-broker mention is explicitly a non-goal/boundary for another task.
    context_broker_terms = ["context broker", "context governance", "context sufficiency", 
                           "context request", "context pack", "module manifest", 
                           "task type manifest", "progressive disclosure"]
    context_broker_non_goal_terms = [
        "do not continue changing context broker",
        "preserve context broker behavior",
        "unless a concrete regression is proven",
    ]
    context_broker_matches = [term for term in context_broker_terms if term in text_lower]
    context_broker_is_non_goal = any(term in text_lower for term in context_broker_non_goal_terms)
    if context_broker_matches and not context_broker_is_non_goal:
        return "context_broker_feature"

    # CLI help/text tasks must be detected before broad summary/probe words such as
    # "display" or "already_satisfied" so Implementation receives __main__.py.
    cli_help_terms = [
        "cli help",
        "help text",
        "help output",
        "argparse",
        "subcommand",
        "command routing",
        "command output",
    ]
    if any(term in text_lower for term in cli_help_terms):
        return "cli_feature"

    # Robustness probes are intentionally worded like real requests, so route the
    # common display/status/governance-adjacent probe forms to summary/workflow
    # grounding instead of generic evolution/governance context.
    # Also detect proposals whose *purpose* is to fix context coverage for probes,
    # unless the context_broker_feature detector already matched above.
    probe_summary_terms = [
        "robustness probe",
        "probe/smoke",
        "probe task",
        "probe p",
        "tiny display",
        "display change",
        "recent workflow summary",
        "workflow/summary",
        "status display",
        "governance-adjacent",
        "governance adjacent",
        "probe/robustness",
        "robustness task",
        "smoke/robustness",
        "probe coverage",
    ]
    if any(term in text_lower for term in probe_summary_terms):
        return "summary_feature"

    # Implementation Agent / ChangeSet stability tasks can mention workflow list,
    # summary, status, or already_satisfied in their failure evidence. The concrete
    # target is still ChangeSet generation/validation, so detect these terms before
    # summary/status rendering terms to avoid under-grounding agent_runner.py and
    # changeset.py fixes.
    implementation_stability_terms = [
        "implementation agent",
        "changeset生成稳定性",
        "changeset generation stability",
        "old_content",
        "noop_replace",
        "missing_operations",
        "invalid changeset",
        "implementation_agent_produced_invalid_changeset",
    ]
    if any(term in text_lower for term in implementation_stability_terms):
        return "changeset_validation_feature"

    # Summary/status rendering tasks appear inside evolution proposal records, which

    # naturally contain broad governance words like "evolution", "proposal", and
    # "request". Detect concrete summary/state-debt terms before evolution-analysis
    # terms so records containing the generic self_evolution_analysis field still
    # receive summary.py/workflow.py grounding context when the actual task is about
    # summary or no-op workflow semantics. Do not treat "summary --check" alone as a
    # summary feature: it is a common acceptance check used by many unrelated tasks.
    summary_terms = [
        "recent_completed_workflows",
        "summary output",
        "summary rendering",
        "summary field",
        "summary state",
        "summary status",
        "state debt",
        "status debt",
        "already_satisfied",
        "no-op",
        "noop",
        "satisfied-without-changes",
        "unresolved failure",
        "状态债",
        "workflow list display",
        "workflow status presentation",
        "workflow CLI display",
    ]
    summary_matches = [term for term in summary_terms if term in text_lower]
    if summary_matches:
        return "summary_feature"

    # CLI/report display tasks often appear inside evolution proposal records, which
    # naturally contain broad words like "evolution", "proposal", and "request".
    # Detect concrete command/report/list terms before evolution-analysis terms so
    # Implementation receives abyss_cli/__main__.py instead of evolution.py only.
    cli_display_terms = [
        "report list",
        "cmd_report_list",
        "workflow list",
        "cmd_workflow_list",
        "cli display",
        "command output",
    ]
    cli_display_matches = [term for term in cli_display_terms if term in text_lower]
    if cli_display_matches:
        return "cli_feature"

    # Evolution-propose tasks may mention the self-evolution Agent, but their
    # concrete target is the evolution request/proposal chain. Detect these terms
    # before generic agent/prompt scoring so the Context Pack includes
    # abyss_cli/evolution.py and evolution_analysis.py. Avoid treating the generic
    # proposal field name self_evolution_analysis as sufficient by itself.
    evolution_propose_terms = [
        "evolution propose",
        "create_proposal_from_request",
        "self-evolution analysis",
        "evolution analysis",
        "empty deterministic wrapping",
        "analysis-empty proposal",
    ]
    evolution_propose_matches = [term for term in evolution_propose_terms if term in text_lower]
    if evolution_propose_matches:
        return "evolution_feature"

    # Agent prompt tasks often appear inside evolution proposal records, which
    # naturally contain broad governance words like "evolution", "proposal", and
    # "request". Detect concrete prompt-file terms before generic scoring so
    # prompt-edit tasks receive the actual prompt files in the Context Pack.
    agent_prompt_terms = [
        "agent prompt",
        "agent提示",
        "prompts/agents",
        "prompt clarity",
    ]
    agent_prompt_matches = [term for term in agent_prompt_terms if term in text_lower]
    if agent_prompt_matches:
        return "agent_feature"

    for task_type, keywords in keywords_map.items():
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        if not matched:
            continue
        match_count = len(matched)
        specificity = sum(len(kw) for kw in matched)
        priority = int(priority_map.get(task_type, 0))
        scores[task_type] = (match_count, specificity, priority)

    if not scores:
        return "unknown"

    return max(scores, key=lambda k: scores[k])


def _resolve_context_spec(task_type: str) -> dict[str, Any]:
    """Resolve the context specification for a given task type.

    Falls back to the fallback spec if task type is unknown or not found.
    """
    manifest = load_context_manifest()
    task_types = manifest.get("task_types", {})

    if task_type in task_types:
        return task_types[task_type]

    return manifest.get("fallback", {})


def _read_file_content(rel_path: str, *, limit: int = 50000) -> dict[str, Any]:
    """Read a file from the repo and return its content with metadata.

    Returns a dict with: path, exists, size, content (possibly truncated), truncated flag.
    The default limit is intentionally large enough to include current core
    Abyss modules such as workflow.py and agent_runner.py without truncation.

    Content is validated for UTF-8 integrity; any replacement characters are
    flagged so the Implementation Agent knows the grounding text may be lossy.
    """
    requested_path = Path(rel_path)
    full_path = requested_path if requested_path.is_absolute() else (repo_root() / rel_path).resolve()
    result: dict[str, Any] = {"path": rel_path, "exists": full_path.exists()}

    if not full_path.exists():
        result["content"] = None
        result["error"] = "FILE_NOT_FOUND"
        return result

    try:
        raw_bytes = full_path.read_bytes()
        text = raw_bytes.decode("utf-8", errors="replace")
        has_replacement_chars = "\ufffd" in text
        result["size"] = len(text)
        if has_replacement_chars:
            result["encoding_warning"] = "File contains replacement characters (possible encoding issue); old_content copied from this file may not match disk exactly."
        if len(text) > limit:
            result["content"] = text[:limit] + "\n\n[TRUNCATED BY CONTEXT BROKER]\n"
            result["truncated"] = True
        else:
            result["content"] = text
            result["truncated"] = False
    except Exception as exc:
        result["content"] = None
        result["error"] = str(exc)

    return result


def _get_module_files(module_names: list[str]) -> list[str]:
    """Get all files associated with the given module names from the module manifest."""
    manifest = load_module_manifest()
    modules = manifest.get("modules", {})
    files: list[str] = []
    seen: set[str] = set()

    for name in module_names:
        module = modules.get(name, {})
        for f in module.get("files", []):
            if f not in seen:
                seen.add(f)
                files.append(f)

    return files


def _get_module_info(module_names: list[str]) -> dict[str, Any]:
    """Get module cards for the given module names."""
    manifest = load_module_manifest()
    modules = manifest.get("modules", {})
    result: dict[str, Any] = {}

    for name in module_names:
        if name in modules:
            result[name] = modules[name]

    return result


def _build_python_symbol_index(rel_paths: list[str]) -> list[dict[str, Any]]:
    """Build a compact top-level import/export index for Python files."""
    index: list[dict[str, Any]] = []
    for rel_path in rel_paths:
        full_path = repo_root() / rel_path
        item: dict[str, Any] = {"path": rel_path, "exists": full_path.exists()}
        if not full_path.exists():
            item["error"] = "FILE_NOT_FOUND"
            index.append(item)
            continue
        try:
            tree = ast.parse(full_path.read_text(encoding="utf-8", errors="replace"), filename=str(full_path))
        except SyntaxError as exc:
            item["error"] = f"SYNTAX_ERROR: {exc}"
            index.append(item)
            continue
        except Exception as exc:
            item["error"] = str(exc)
            index.append(item)
            continue

        exports: list[str] = []
        imports: list[str] = []
        all_exports: list[str] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                exports.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                            all_exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
                        elif target.id.isupper() or not target.id.startswith("_"):
                            exports.append(target.id)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                names = ", ".join(alias.name for alias in node.names)
                imports.append(f"from {module} import {names}")

        item["exports"] = sorted(dict.fromkeys(all_exports or exports))
        item["imports"] = imports
        index.append(item)
    return index


def build_context_pack(
    *,
    agent_id: str,
    target_record: dict[str, Any],
    roadmap_id: str = "",
    proposal_id: str = "",
    task_type: str | None = None,
) -> dict[str, Any]:
    """Build a context pack for an agent run.

    This is the main entry point for the Context Broker.

    Args:
        agent_id: Which agent is being invoked (implementation, self_evolution, harness)
        target_record: The target record (proposal, request, changeset, etc.)
        roadmap_id: Associated roadmap ID if any
        proposal_id: Associated proposal ID if any
        task_type: Explicit task type override; if None, auto-detected from target_record

    Returns:
        A context pack dict with all resolved context.
    """
    # Auto-detect task type if not provided
    if task_type is None:
        target_text = json.dumps(target_record, ensure_ascii=False)
        task_type = detect_task_type(target_text)

    # Resolve context specification
    context_spec = _resolve_context_spec(task_type)
    disclosure_plan = build_disclosure_plan(task_type, context_spec)

    # Get required modules and files
    required_modules = context_spec.get("required_modules", [])
    required_files = context_spec.get("required_files", [])
    symbol_index_files = context_spec.get("symbol_index_files", [])
    required_rules = context_spec.get("required_rules", [])
    required_prompts = context_spec.get("required_prompts", [])

    # Get module-derived files
    module_files = _get_module_files(required_modules)

    # Merge all required files (deduplicated, preserving order)
    all_files: list[str] = []
    seen: set[str] = set()
    for f in required_files + module_files + required_rules + required_prompts:
        if f not in seen:
            seen.add(f)
            all_files.append(f)

    # Read file contents
    file_contents: list[dict[str, Any]] = []
    missing_files: list[str] = []
    for rel_path in all_files:
        file_info = _read_file_content(rel_path)
        file_contents.append(file_info)
        if not file_info.get("exists"):
            missing_files.append(rel_path)

    # Build compact package-level symbol index without injecting full source.
    symbol_index = _build_python_symbol_index(symbol_index_files)

    # Load system brief
    system_brief = load_system_brief()

    # Load progressive disclosure cognition protocol
    architecture_cognition = load_architecture_cognition()

    # Get module info for included modules
    module_info = _get_module_info(required_modules)

    total_content_size = sum(len(f.get("content") or "") for f in file_contents)
    context_budget = {
        "total_content_size": total_content_size,
        "warn_threshold": CONTEXT_CONTENT_BUDGET_WARN,
        "over_warn_threshold": total_content_size > CONTEXT_CONTENT_BUDGET_WARN,
    }

    # Build the context pack
    pack_id = new_id("ctx")
    context_pack: dict[str, Any] = {
        "schema": "abyss.context_pack.v1",
        "id": pack_id,
        "agent_id": agent_id,
        "roadmap_id": roadmap_id,
        "proposal_id": proposal_id,
        "task_type": task_type,
        "created_at": now_iso(),

        "system_brief_included": True,
        "system_brief": system_brief,

        "architecture_cognition_included": architecture_cognition.get("exists", False),
        "architecture_cognition": architecture_cognition,

        "modules_included": required_modules,
        "module_info": module_info,

        "files_included": [f["path"] for f in file_contents if f.get("exists")],
        "files_missing": missing_files,
        "file_contents": file_contents,
        "symbol_index_files": symbol_index_files,
        "python_symbol_index": symbol_index,

        "constraints": system_brief.get("hard_constraints", []),
        "acceptance_criteria": context_spec.get("required_checks", []),
        "context_budget": context_budget,
        "disclosure_plan": disclosure_plan,
    }

    # Run coverage manifest validation if target declares one
    coverage_check = validate_task_coverage_manifest(target_record, context_pack)
    context_pack["coverage_check"] = coverage_check

    # Persist the context pack record (without file contents to save space)
    pack_record = {
        "schema": "abyss.context_pack.v1",
        "id": pack_id,
        "agent_id": agent_id,
        "roadmap_id": roadmap_id,
        "proposal_id": proposal_id,
        "task_type": task_type,
        "created_at": now_iso(),
        "system_brief_included": True,
        "modules_included": required_modules,
        "architecture_cognition_included": architecture_cognition.get("exists", False),
        "files_included": [f["path"] for f in file_contents if f.get("exists")],
        "files_missing": missing_files,
        "file_count": len([f for f in file_contents if f.get("exists")]),
        "symbol_index_file_count": len([f for f in symbol_index if f.get("exists")]),
        "total_content_size": total_content_size,
        "context_budget": context_budget,
        "coverage_check": {
            "has_manifest": coverage_check.get("has_manifest"),
            "ok": coverage_check.get("ok"),
            "missing_files": coverage_check.get("missing_files", []),
            "missing_domains": coverage_check.get("missing_domains", []),
            "warnings": coverage_check.get("warnings", []),
        },
        "disclosure_plan": {
            "schema": disclosure_plan.get("schema"),
            "ok": disclosure_plan.get("ok"),
            "task_type": disclosure_plan.get("task_type"),
            "default_disclosure_level": disclosure_plan.get("default_disclosure_level"),
            "max_disclosure_level": disclosure_plan.get("max_disclosure_level"),
            "max_seen_level": disclosure_plan.get("max_seen_level"),
            "recommended_action": disclosure_plan.get("recommended_action"),
            "warnings": disclosure_plan.get("warnings", []),
            "no_action_executed": True,
            "no_approval_granted": True,
        },
    }
    CONTEXT_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    write_record(CONTEXT_PACKS_DIR / f"{pack_id}.yaml", pack_record)

    return context_pack


def render_context_pack_for_prompt(context_pack: dict[str, Any]) -> str:
    """Render a context pack into a Markdown section suitable for inclusion in a prompt package.

    This produces the text that gets injected into the agent's prompt.
    """
    sections: list[str] = []

    # Architecture Cognition section
    cognition = context_pack.get("architecture_cognition", {})
    if cognition.get("exists"):
        sections.append("## Architecture Cognition Protocol\n")
        sections.append("This is the progressive disclosure protocol for understanding Abyss. Treat it as cognition guidance; it does not grant approval or execution authority.\n\n")
        sections.append(f"```yaml\n{cognition.get('content', '')}\n```\n")

    # Context budget section
    context_budget = context_pack.get("context_budget", {})
    if context_budget:
        sections.append("## Context Budget\n")
        sections.append(f"- total_content_size: {context_budget.get('total_content_size')}\n")
        sections.append(f"- warn_threshold: {context_budget.get('warn_threshold')}\n")
        sections.append(f"- over_warn_threshold: {context_budget.get('over_warn_threshold')}\n")
        if context_budget.get("over_warn_threshold"):
            sections.append("- warning: Context pack is large. Prefer narrow edit plans and request more specific context instead of guessing.\n")
        sections.append("\n")

    # Disclosure plan section
    disclosure_plan = context_pack.get("disclosure_plan", {})
    if disclosure_plan:
        sections.append("## Disclosure Plan (read-only)\n")
        sections.append("This plan explains the declared disclosure boundary for this task. It does not grant approval, execution authority, source access beyond included files, or runtime access.\n\n")
        sections.append(f"```json\n{json.dumps(disclosure_plan, ensure_ascii=False, indent=2)}\n```\n")

    # System Brief section
    sections.append("## System Brief\n")
    brief = context_pack.get("system_brief", {})
    sections.append(f"```json\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n```\n")

    # Module Map section
    sections.append("## Module Map (relevant modules)\n")
    module_info = context_pack.get("module_info", {})
    if module_info:
        sections.append(f"```json\n{json.dumps(module_info, ensure_ascii=False, indent=2)}\n```\n")
    else:
        sections.append("[no module info available]\n")

    # Repository Files section
    sections.append("## Repository Files (grounding context)\n")
    sections.append("The following are deterministic reads from the local repository. ")
    sections.append("For every `fs.replace_exact` operation, `input.old_content` MUST be copied exactly from one of these files. ")
    sections.append("If the required target code is not present here, output `abyss.context_request.v1` instead of guessing.\n\n")

    file_contents = context_pack.get("file_contents", [])
    for file_info in file_contents:
        path = file_info.get("path", "unknown")
        if not file_info.get("exists"):
            sections.append(f"### {path}\n\n[FILE NOT FOUND]\n\n")
            continue
        content = file_info.get("content", "")
        truncated = file_info.get("truncated", False)
        size = file_info.get("size", 0)
        meta = f"({size} bytes"
        if truncated:
            meta += ", truncated"
        meta += ")"
        sections.append(f"### {path} {meta}\n\n```text\n{content}\n```\n\n")

    # Compact Python symbol index section
    symbol_index = context_pack.get("python_symbol_index", [])
    if symbol_index:
        sections.append("## Python Module Symbol Index\n\n")
        sections.append("Compact top-level import/export index for package-wide symbol validation. ")
        sections.append("Use this for package structure and symbol existence checks; use Repository Files above for exact replacement content.\n\n")
        sections.append(f"```json\n{json.dumps(symbol_index, ensure_ascii=False, indent=2)}\n```\n\n")

    # Encoding warnings
    encoding_warnings = [f for f in file_contents if f.get("encoding_warning")]
    if encoding_warnings:
        sections.append("## \u26a0\ufe0f Encoding Warnings\n\n")
        sections.append("The following files have encoding issues. Do NOT use `fs.replace_exact` with content from these files; use `abyss-context-request` instead:\n")
        for f in encoding_warnings:
            sections.append(f"- `{f.get('path')}`: {f.get('encoding_warning')}\n")
        sections.append("\n")

    # Coverage manifest check section
    coverage_check = context_pack.get("coverage_check", {})
    if coverage_check.get("has_manifest") and not coverage_check.get("ok"):
        sections.append("## Coverage Manifest Warnings\n\n")
        sections.append("The target record declares a `task_coverage_manifest` but the following declared targets are not covered by the current context pack:\n\n")
        for warning in coverage_check.get("warnings", []):
            sections.append(f"- {warning}\n")
        sections.append("\nConsider requesting additional context or updating the manifest.\n\n")

    # Missing files warning
    missing = context_pack.get("files_missing", [])
    if missing:
        sections.append("## ⚠️ Missing Files\n\n")
        sections.append("The following files were expected but not found:\n")
        for f in missing:
            sections.append(f"- `{f}`\n")
        sections.append("\nIf your implementation requires these files, output `abyss.context_request.v1`.\n\n")

    # Constraints section
    constraints = context_pack.get("constraints", [])
    if constraints:
        sections.append("## Hard Constraints\n\n")
        for c in constraints:
            sections.append(f"- {c}\n")
        sections.append("\n")

    return "\n".join(sections)


def render_context_pack_summary(context_pack: dict[str, Any]) -> str:
    """Render a short summary of a context pack for display/logging."""
    pack_id = context_pack.get("id", "unknown")
    agent_id = context_pack.get("agent_id", "unknown")
    task_type = context_pack.get("task_type", "unknown")
    files_included = context_pack.get("files_included", [])
    files_missing = context_pack.get("files_missing", [])
    modules = context_pack.get("modules_included", [])
    context_budget = context_pack.get("context_budget", {})
    disclosure_plan = context_pack.get("disclosure_plan", {})

    lines = [
        f"Context Pack: {pack_id}",
        f"  Agent: {agent_id}",
        f"  Task Type: {task_type}",
        f"  Modules: {', '.join(modules)}",
        f"  Files included: {len(files_included)}",
    ]
    if context_budget:
        lines.append(f"  Content size: {context_budget.get('total_content_size')} / warn {context_budget.get('warn_threshold')}")
    if disclosure_plan:
        lines.append(f"  Disclosure: ok={disclosure_plan.get('ok')} max={disclosure_plan.get('max_disclosure_level')} seen={disclosure_plan.get('max_seen_level')} action={disclosure_plan.get('recommended_action')}")
    if files_missing:
        lines.append(f"  ⚠️ Files missing: {', '.join(files_missing)}")

    return "\n".join(lines)
