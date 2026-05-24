"""Context Broker V0: Context Pack generation for Abyss agents.

Responsible for:
- Building context packs based on task type and module manifest
- Providing system brief to all governance agents
- Recording context pack metadata for audit
- Detecting task type from proposal/request text
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import new_id, now_iso, read_record, repo_root, runtime_root, write_record

CONTEXT_PACKS_DIR = runtime_root() / "process" / "context_packs"

# Rule file paths
SYSTEM_BRIEF_FILE = repo_root() / "rules" / "system_brief.yaml"
MODULES_FILE = repo_root() / "rules" / "modules.yaml"
CONTEXT_MANIFEST_FILE = repo_root() / "rules" / "context_manifest.yaml"


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


def detect_task_type(text: str) -> str:
    """Detect task type from proposal/request text using keyword heuristics.

    Returns the best-matching task type key, or 'unknown' if no match.
    """
    manifest = load_context_manifest()
    detection = manifest.get("task_type_detection", {})
    keywords_map: dict[str, list[str]] = detection.get("keywords", {})

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for task_type, keywords in keywords_map.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[task_type] = score

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


def _read_file_content(rel_path: str, *, limit: int = 16000) -> dict[str, Any]:
    """Read a file from the repo and return its content with metadata.

    Returns a dict with: path, exists, size, content (possibly truncated), truncated flag.
    """
    full_path = repo_root() / rel_path
    result: dict[str, Any] = {"path": rel_path, "exists": full_path.exists()}

    if not full_path.exists():
        result["content"] = None
        result["error"] = "FILE_NOT_FOUND"
        return result

    try:
        text = full_path.read_text(encoding="utf-8", errors="replace")
        result["size"] = len(text)
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

    # Get required modules and files
    required_modules = context_spec.get("required_modules", [])
    required_files = context_spec.get("required_files", [])
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

    # Load system brief
    system_brief = load_system_brief()

    # Get module info for included modules
    module_info = _get_module_info(required_modules)

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

        "modules_included": required_modules,
        "module_info": module_info,

        "files_included": [f["path"] for f in file_contents if f.get("exists")],
        "files_missing": missing_files,
        "file_contents": file_contents,

        "constraints": system_brief.get("hard_constraints", []),
        "acceptance_criteria": context_spec.get("required_checks", []),
    }

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
        "files_included": [f["path"] for f in file_contents if f.get("exists")],
        "files_missing": missing_files,
        "file_count": len([f for f in file_contents if f.get("exists")]),
        "total_content_size": sum(len(f.get("content") or "") for f in file_contents),
    }
    CONTEXT_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    write_record(CONTEXT_PACKS_DIR / f"{pack_id}.yaml", pack_record)

    return context_pack


def render_context_pack_for_prompt(context_pack: dict[str, Any]) -> str:
    """Render a context pack into a Markdown section suitable for inclusion in a prompt package.

    This produces the text that gets injected into the agent's prompt.
    """
    sections: list[str] = []

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

    lines = [
        f"Context Pack: {pack_id}",
        f"  Agent: {agent_id}",
        f"  Task Type: {task_type}",
        f"  Modules: {', '.join(modules)}",
        f"  Files included: {len(files_included)}",
    ]
    if files_missing:
        lines.append(f"  ⚠️ Files missing: {', '.join(files_missing)}")

    return "\n".join(lines)
