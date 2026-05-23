from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .audit import append_event
from .intent import INTENTS_DIR
from .prompt_builder import PROMPT_DIR
from .result import import_result
from .utils import ensure_dir, new_id, repo_root, runtime_root

LLM_RESULTS_DIR = runtime_root() / "process" / "llm_results"
PROVIDER_RULES_PATH = repo_root() / "rules" / "llm_providers.yaml"
LOCAL_PROVIDER_CONFIG_PATH = repo_root() / ".local" / "llm_providers.json"
INTENT_ID_RE = re.compile(r"^-\s*intent_id:\s*(\S+)\s*$", re.MULTILINE)
CLI_PROVIDER_INTERFACE = "stdin_prompt_package_stdout_response_v1"
API_PROVIDER_INTERFACE = "http_json_prompt_package_response_v1"


def _latest_prompt_package() -> Path | None:
    if not PROMPT_DIR.exists():
        return None
    files = [p for p in PROMPT_DIR.glob("ppkg_*.md") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime)[-1] if files else None


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_provider_config() -> dict[str, Any]:
    rules = _read_json_file(PROVIDER_RULES_PATH)
    local = _read_json_file(LOCAL_PROVIDER_CONFIG_PATH)
    return _deep_merge(rules, local)


def resolve_prompt_package(value: str) -> Path:
    if value == "latest":
        latest = _latest_prompt_package()
        if not latest:
            raise SystemExit(f"No prompt packages found in {PROMPT_DIR}")
        return latest

    candidate = Path(value)
    if not candidate.is_absolute():
        cwd_candidate = (Path.cwd() / candidate).resolve()
        if cwd_candidate.exists():
            return cwd_candidate
        candidate = PROMPT_DIR / value

    if candidate.exists():
        return candidate.resolve()

    if not value.endswith(".md"):
        candidate = PROMPT_DIR / f"{value}.md"
        if candidate.exists():
            return candidate.resolve()

    matches = [p for p in PROMPT_DIR.glob("*.md") if p.stem == value or p.stem.startswith(value)] if PROMPT_DIR.exists() else []
    if len(matches) == 1:
        return matches[0].resolve()
    if len(matches) > 1:
        raise SystemExit(f"Ambiguous prompt package {value}: " + ", ".join(p.stem for p in matches))
    raise SystemExit(f"Prompt package not found: {value}")


def _intent_path_from_prompt(prompt_text: str) -> Path | None:
    match = INTENT_ID_RE.search(prompt_text)
    if not match:
        return None
    intent_id = match.group(1)
    path = INTENTS_DIR / f"{intent_id}.yaml"
    return path if path.exists() else None


def _cli_response(provider_config: dict[str, Any], prompt_text: str) -> str:
    interface = provider_config.get("interface", CLI_PROVIDER_INTERFACE)
    if interface != CLI_PROVIDER_INTERFACE:
        raise SystemExit(f"Unsupported CLI provider interface: {interface}")

    command = provider_config.get("command") or []
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise SystemExit(
            "CLI provider is not configured. Set providers.cli.command in .local/llm_providers.json, "
            "for example: {\"providers\": {\"cli\": {\"command\": [\"your-llm-cli\", \"arg\"]}}}"
        )
    timeout = int(provider_config.get("timeout_seconds", 120))
    try:
        proc = subprocess.run(
            command,
            input=prompt_text,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"CLI provider timed out after {timeout} seconds") from exc
    except OSError as exc:
        raise SystemExit(f"CLI provider could not start: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise SystemExit(detail or f"CLI provider failed with exit code {proc.returncode}")
    output = proc.stdout.strip()
    if not output:
        raise SystemExit("CLI provider returned empty stdout")
    return output + "\n"


def _json_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _api_response(provider_config: dict[str, Any], prompt_path: Path, prompt_text: str) -> str:
    interface = provider_config.get("interface", API_PROVIDER_INTERFACE)
    if interface != API_PROVIDER_INTERFACE:
        raise SystemExit(f"Unsupported API provider interface: {interface}")

    url = str(provider_config.get("url") or "").strip()
    if not url:
        raise SystemExit("API provider is not configured. Set providers.<name>.url in .local/llm_providers.json")

    timeout = int(provider_config.get("timeout_seconds", 120))
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    configured_headers = provider_config.get("headers", {})
    if isinstance(configured_headers, dict):
        headers.update({str(k): str(v) for k, v in configured_headers.items()})

    bearer_env = str(provider_config.get("bearer_token_env") or "").strip()
    if bearer_env:
        token = os.environ.get(bearer_env)
        if not token:
            raise SystemExit(f"API provider bearer_token_env is set but environment variable is empty: {bearer_env}")
        headers["Authorization"] = f"Bearer {token}"

    body = {
        "schema": "abyss.llm_api_request.v1",
        "prompt_package": prompt_text,
        "metadata": {
            "prompt_package_path": prompt_path.as_posix(),
            "provider_interface": API_PROVIDER_INTERFACE,
        },
    }
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise SystemExit(f"API provider HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"API provider request failed: {exc.reason}") from exc

    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"API provider returned non-JSON response: {response_text[:500]}") from exc

    response_path = str(provider_config.get("response_json_path") or "response")
    output = _json_path(payload, response_path)
    if not isinstance(output, str) or not output.strip():
        raise SystemExit(f"API provider JSON field is empty or not a string: {response_path}")
    return output.strip() + "\n"


def _provider_response(provider: str, provider_config: dict[str, Any], prompt_path: Path, prompt_text: str) -> str:
    interface = provider_config.get("interface", CLI_PROVIDER_INTERFACE)
    if interface == CLI_PROVIDER_INTERFACE:
        return _cli_response(provider_config, prompt_text)
    if interface == API_PROVIDER_INTERFACE:
        return _api_response(provider_config, prompt_path, prompt_text)
    raise SystemExit(f"Unsupported LLM provider interface for {provider}: {interface}")


def run_llm(prompt_package: str, provider: str) -> tuple[Path, list[dict[str, Any]]]:
    config = load_provider_config()
    providers = config.get("providers", {})
    provider_config = providers.get(provider)
    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        raise SystemExit(f"LLM provider is not enabled or configured: {provider}")

    prompt_path = resolve_prompt_package(prompt_package)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    response_text = _provider_response(provider, provider_config, prompt_path, prompt_text)

    ensure_dir(LLM_RESULTS_DIR)
    result_id = new_id("llm_result")
    result_path = LLM_RESULTS_DIR / f"{result_id}.md"
    result_path.write_text(response_text, encoding="utf-8")

    intent_path = _intent_path_from_prompt(prompt_text)
    proposals = import_result(result_path, intent_path)
    append_event(
        "llm.run",
        "Ran LLM provider and imported result",
        {
            "provider": provider,
            "prompt_package": prompt_path.as_posix(),
            "result_path": result_path.as_posix(),
            "actions_found": len(proposals),
        },
    )
    return result_path, proposals
