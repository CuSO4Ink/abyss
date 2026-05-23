from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import append_event
from .harness import render_harness_json
from .harness_review import parse_harness_review
from .llm_executor import LLM_RESULTS_DIR, _provider_response, load_provider_config
from .evolution import resolve_evolution_target
from .evolution_analysis import parse_evolution_analysis
from .result import ACTIONS_DIR
from .utils import latest_record, new_id, now_iso, read_record, relative_to_repo, repo_root, resolve_record_arg, runtime_root, write_record

AGENTS_FILE = repo_root() / "rules" / "agents.yaml"
AGENT_PROMPT_DIR = runtime_root() / "process" / "prompt_packages"
AGENT_RUNS_DIR = runtime_root() / "process" / "agent_runs"


def load_agents_config() -> dict[str, Any]:
    if not AGENTS_FILE.exists():
        raise SystemExit(f"Agent registry not found: {AGENTS_FILE}")
    return read_record(AGENTS_FILE)


def _agent_spec(agent_id: str) -> dict[str, Any]:
    config = load_agents_config()
    agents = config.get("agents", {})
    spec = agents.get(agent_id)
    if not isinstance(spec, dict) or not spec.get("enabled", False):
        raise SystemExit(f"Agent is not enabled or configured: {agent_id}")
    return spec


def _latest_llm_result() -> Path | None:
    if not LLM_RESULTS_DIR.exists():
        return None
    files = [p for p in LLM_RESULTS_DIR.glob("llm_result_*.md") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime)[-1] if files else None


def _safe_read(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text if len(text) <= limit else text[:limit] + "\n\n[TRUNCATED BY ABYSS]\n"


def _resolve_action_target(target: str) -> Path:
    return resolve_record_arg(ACTIONS_DIR, target, "act")


def _build_harness_agent_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str | None]:
    target_path = _resolve_action_target(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"HarnessAgent role prompt not found or empty: {role_prompt_path}")

    latest_result = _latest_llm_result()
    latest_result_text = _safe_read(latest_result) if latest_result else "[no llm_result found]"
    policy_text = json.dumps(read_record(repo_root() / "rules" / "policy.yaml"), ensure_ascii=False, indent=2)
    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=6000)

    ppkg_id = new_id("ppkg_agent_harness")
    body = f"""# Abyss Agent Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: harness
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target action proposal

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Latest related LLM result

```markdown
{latest_result_text}
```

---

## Policy snapshot

```json
{policy_text}
```

---

## Harness snapshot

```json
{render_harness_json()}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

---

## Required output

Return exactly one `abyss-harness-review` fenced block. Do not produce `abyss-action` blocks. Do not claim that any action was executed.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("agent.prompt_package.created", "Built agent prompt package", {"agent_id": "harness", "target_id": target_id, "path": prompt_path.as_posix()})
    return prompt_path, target_path, target_id


def _build_self_evolution_agent_prompt(spec: dict[str, Any], target: str) -> tuple[Path, Path, str]:
    target_path = resolve_evolution_target(target)
    target_record = read_record(target_path)
    target_id = str(target_record.get("id") or target_path.stem)

    role_prompt_path = repo_root() / str(spec.get("role_prompt", ""))
    role_prompt = _safe_read(role_prompt_path)
    if not role_prompt.strip():
        raise SystemExit(f"Self-evolution agent role prompt not found or empty: {role_prompt_path}")

    agents_text = json.dumps(spec, ensure_ascii=False, indent=2)
    roadmap_text = _safe_read(repo_root() / "ROADMAP.md", limit=8000)
    constitution_text = _safe_read(repo_root() / "ABYSS_CONSTITUTION.md", limit=8000)
    system_map_excerpt = _safe_read(repo_root() / "SYSTEM_MAP.md", limit=6000)

    ppkg_id = new_id("ppkg_agent_self_evolution")
    body = f"""# Abyss Agent Prompt Package

- prompt_package_id: {ppkg_id}
- agent_id: self_evolution
- target_id: {target_id}
- target_path: {relative_to_repo(target_path)}
- created_at: {now_iso()}
- executor: agent_cli_provider

---

## Agent registry spec

```json
{agents_text}
```

---

## Agent role prompt

{role_prompt}

---

## Target evolution record

```json
{json.dumps(target_record, ensure_ascii=False, indent=2)}
```

---

## Roadmap snapshot

```markdown
{roadmap_text}
```

---

## Constitution excerpt

```markdown
{constitution_text}
```

---

## System map excerpt

```markdown
{system_map_excerpt}
```

---

## Required output

Return exactly one `abyss-evolution-analysis` fenced block. Do not produce `abyss-action` blocks. Do not claim that any action was executed.
"""
    AGENT_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = AGENT_PROMPT_DIR / f"{ppkg_id}.md"
    prompt_path.write_text(body, encoding="utf-8")
    append_event("agent.prompt_package.created", "Built self-evolution agent prompt package", {"agent_id": "self_evolution", "target_id": target_id, "path": prompt_path.as_posix()})
    return prompt_path, target_path, target_id


def run_agent(agent_id: str, target: str = "latest", provider: str | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    spec = _agent_spec(agent_id)
    provider_name = provider or str(spec.get("provider") or "cli")
    if agent_id == "harness":
        prompt_path, _target_path, target_id = _build_harness_agent_prompt(spec, target)
    elif agent_id == "self_evolution":
        prompt_path, _target_path, target_id = _build_self_evolution_agent_prompt(spec, target)
    else:
        raise SystemExit(f"Agent is configured but not implemented: {agent_id}")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    provider_config_root = load_provider_config()
    providers = provider_config_root.get("providers", {})
    provider_config = providers.get(provider_name)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider_name}")

    response_text = _provider_response(provider_name, provider_config, prompt_path, prompt_text)
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(response_text, encoding="utf-8")

    agent_run = {
        "schema": "abyss.agent_run.v1",
        "id": new_id("agent_run"),
        "agent_id": agent_id,
        "target_id": target_id,
        "provider": provider_name,
        "prompt_package": prompt_path.as_posix(),
        "result_path": result_path.as_posix(),
        "status": "completed",
        "no_action_executed": True,
        "created_at": now_iso(),
    }
    write_record(AGENT_RUNS_DIR / f"{agent_run['id']}.yaml", agent_run)
    append_event("agent.run.completed", "Agent run completed", {"agent_run_id": agent_run["id"], "agent_id": agent_id, "target_id": target_id, "result_path": result_path.as_posix()})

    specialized_record = None
    if agent_id == "harness":
        specialized_record = parse_harness_review(response_text, target_id=target_id, agent_run_id=agent_run["id"], result_path=result_path)
    elif agent_id == "self_evolution":
        specialized_record = parse_evolution_analysis(response_text, target_id=target_id, agent_run_id=agent_run["id"], result_path=result_path)

    return agent_run, specialized_record


def run_harness_review(target: str = "latest", provider: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    agent_run, review = run_agent("harness", target=target, provider=provider)
    if review is None:
        raise SystemExit("Harness review was not created")
    return agent_run, review
