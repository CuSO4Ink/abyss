from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
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
OPENAI_CHAT_PROVIDER_INTERFACE = "http_openai_chat_completion_v1"


def sanitize_llm_text(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


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


def _positive_int(value: Any, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


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
    command = list(command)
    model = str(provider_config.get("model") or "").strip()
    model_argument = str(provider_config.get("model_argument") or "--model").strip()
    if model:
        if not model_argument:
            raise SystemExit("CLI provider model is configured but model_argument is empty")
        command.extend([model_argument, model])

    timeout = _positive_int(provider_config.get("timeout_seconds"), 120)
    max_attempts = _positive_int(provider_config.get("max_attempts"), 2, maximum=3)
    retry_backoff_seconds = _positive_int(provider_config.get("retry_backoff_seconds"), 3, minimum=0, maximum=30)
    retryable_errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
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
        except subprocess.TimeoutExpired:
            message = f"CLI provider timed out after {timeout} seconds (provider=cli, interface={interface}, attempt {attempt}/{max_attempts})"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": "cli", "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": "timeout", "timeout_seconds": timeout})
        except OSError as exc:
            raise SystemExit(f"CLI provider could not start: {exc}") from exc
        else:
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "").strip()
                raise SystemExit(detail or f"CLI provider failed with exit code {proc.returncode}")
            output = proc.stdout.strip()
            if output:
                if attempt > 1:
                    append_event("llm.provider.retry_recovered", "CLI provider returned output after retry", {"provider": "cli", "attempt": attempt, "max_attempts": max_attempts, "prior_errors": retryable_errors})
                return output + "\n"
            message = f"CLI provider returned empty stdout (provider=cli, interface={interface}, attempt {attempt}/{max_attempts}, stdout_empty_before_filtering=True)"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": "cli", "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": "empty_stdout", "stdout_length": 0, "stdout_empty_before_filtering": True, "stderr_preview": (proc.stderr or "")[:200]})

        if attempt < max_attempts and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * attempt)

    detail = "; ".join(retryable_errors[-max_attempts:]) or "unknown retryable provider failure"
    raise SystemExit(f"CLI provider failed after {max_attempts} attempt(s) (provider=cli, interface={interface}): {detail}")


def _json_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index < 0 or index >= len(current):
                return None
            current = current[index]
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

    timeout = _positive_int(provider_config.get("timeout_seconds"), 120)
    max_attempts = _positive_int(provider_config.get("max_attempts"), 2, maximum=3)
    retry_backoff_seconds = _positive_int(provider_config.get("retry_backoff_seconds"), 3, minimum=0, maximum=30)
    retryable_errors: list[str] = []
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
    request_body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    response_path = str(provider_config.get("response_json_path") or "response")

    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(url, data=request_body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            if exc.code == 429 or 500 <= exc.code <= 599:
                message = f"API provider HTTP {exc.code}: {detail or exc.reason} (attempt {attempt}/{max_attempts})"
                retryable_errors.append(message)
                append_event("llm.provider.retryable_failure", message, {"provider": "api", "attempt": attempt, "max_attempts": max_attempts, "reason": "http_retryable", "http_status": exc.code})
            else:
                raise SystemExit(f"API provider HTTP {exc.code}: {detail or exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            reason = getattr(exc, "reason", exc)
            message = f"API provider request failed: {reason} (attempt {attempt}/{max_attempts})"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": "api", "attempt": attempt, "max_attempts": max_attempts, "reason": str(reason), "timeout_seconds": timeout})
        else:
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"API provider returned non-JSON response: {response_text[:500]}") from exc

            output = _json_path(payload, response_path)
            if isinstance(output, str) and output.strip():
                if attempt > 1:
                    append_event("llm.provider.retry_recovered", "API provider returned output after retry", {"provider": "api", "attempt": attempt, "max_attempts": max_attempts, "prior_errors": retryable_errors})
                return output.strip() + "\n"
            stdout_empty_after_filtering = isinstance(output, str) and not output.strip()
            message = f"API provider JSON response field is empty or not a string: {response_path} (provider=api, interface={interface}, attempt {attempt}/{max_attempts}, stdout_empty_after_filtering={stdout_empty_after_filtering})"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": "api", "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": "empty_response_field", "response_json_path": response_path, "stdout_empty_after_filtering": stdout_empty_after_filtering})

        if attempt < max_attempts and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * attempt)

    detail = "; ".join(retryable_errors[-max_attempts:]) or "unknown retryable provider failure"
    raise SystemExit(f"API provider failed after {max_attempts} attempt(s) (provider=api, interface={interface}): {detail}")


def _classify_openai_chat_error(status_code: int | None, exc: Exception | None = None) -> str:
    if status_code in (401, 403):
        return "auth"
    if status_code == 402:
        return "quota"
    if status_code == 429:
        return "rate_limit"
    if status_code is not None and 500 <= status_code <= 599:
        return "server"
    if isinstance(exc, (urllib.error.URLError, TimeoutError, socket.timeout, OSError)):
        return "network"
    return "bad_response"


def _openai_chat_endpoint(provider_config: dict[str, Any]) -> str:
    url = str(provider_config.get("url") or "").strip()
    if url:
        return url
    base_url = str(provider_config.get("base_url") or "").strip().rstrip("/")
    endpoint = str(provider_config.get("endpoint") or "/chat/completions").strip()
    if not base_url:
        raise SystemExit("OpenAI-compatible chat provider is not configured. Set providers.<name>.url or base_url in .local/llm_providers.json")
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return base_url + endpoint


def _optional_number(config: dict[str, Any], key: str, numeric_type: type[int] | type[float]) -> int | float | None:
    value = config.get(key)
    if value is None:
        request_config = config.get("request")
        if isinstance(request_config, dict):
            value = request_config.get(key)
    if value is None:
        return None
    try:
        return numeric_type(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"OpenAI-compatible chat provider request.{key} must be a {numeric_type.__name__}") from exc


def _openai_chat_response(provider: str, provider_config: dict[str, Any], prompt_path: Path, prompt_text: str) -> str:
    interface = provider_config.get("interface", OPENAI_CHAT_PROVIDER_INTERFACE)
    if interface != OPENAI_CHAT_PROVIDER_INTERFACE:
        raise SystemExit(f"Unsupported OpenAI-compatible chat provider interface: {interface}")

    url = _openai_chat_endpoint(provider_config)
    model = str(provider_config.get("model") or "").strip()
    if not model:
        raise SystemExit("OpenAI-compatible chat provider is not configured. Set providers.<name>.model in .local/llm_providers.json")

    timeout = _positive_int(provider_config.get("timeout_seconds"), 120)
    max_attempts = _positive_int(provider_config.get("max_attempts"), 2, maximum=3)
    retry_backoff_seconds = _positive_int(provider_config.get("retry_backoff_seconds"), 3, minimum=0, maximum=30)
    retryable_errors: list[str] = []

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    configured_headers = provider_config.get("headers", {})
    if isinstance(configured_headers, dict):
        headers.update({str(k): str(v) for k, v in configured_headers.items()})

    bearer_env = str(provider_config.get("bearer_token_env") or "").strip()
    if bearer_env:
        token = os.environ.get(bearer_env)
        if not token:
            raise SystemExit(f"OpenAI-compatible chat provider bearer_token_env is set but environment variable is empty: {bearer_env}")
        headers["Authorization"] = f"Bearer {token}"

    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "stream": False,
    }
    max_tokens = _optional_number(provider_config, "max_tokens", int)
    temperature = _optional_number(provider_config, "temperature", float)
    top_p = _optional_number(provider_config, "top_p", float)
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if temperature is not None:
        body["temperature"] = temperature
    if top_p is not None:
        body["top_p"] = top_p

    request_body = json.dumps(body, ensure_ascii=False).encode("utf-8")

    for attempt in range(1, max_attempts + 1):
        request = urllib.request.Request(url, data=request_body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_text = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            category = _classify_openai_chat_error(exc.code, exc)
            if category in ("rate_limit", "server"):
                message = f"OpenAI-compatible chat provider HTTP {exc.code} [{category}] (provider={provider}, attempt {attempt}/{max_attempts}): {detail or exc.reason}"
                retryable_errors.append(message)
                append_event("llm.provider.retryable_failure", message, {"provider": provider, "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": category, "http_status": exc.code})
            else:
                raise SystemExit(f"OpenAI-compatible chat provider HTTP {exc.code} [{category}] (provider={provider}): {detail or exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            category = _classify_openai_chat_error(None, exc)
            reason = getattr(exc, "reason", exc)
            message = f"OpenAI-compatible chat provider request failed [{category}] (provider={provider}, attempt {attempt}/{max_attempts}): {reason}"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": provider, "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": category, "timeout_seconds": timeout})
        else:
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"OpenAI-compatible chat provider returned non-JSON response [bad_response] (provider={provider}): {response_text[:500]}") from exc

            message_obj = _json_path(payload, "choices.0.message")
            if not isinstance(message_obj, dict):
                raise SystemExit(f"OpenAI-compatible chat provider response missing choices.0.message [bad_response] (provider={provider})")

            reasoning_content = message_obj.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content.strip():
                append_event("llm.provider.diagnostics", "OpenAI-compatible chat provider returned reasoning_content (diagnostics only)", {"provider": provider, "interface": interface, "prompt_package": prompt_path.as_posix(), "reasoning_content_length": len(reasoning_content)})

            content = message_obj.get("content")
            if isinstance(content, str) and content.strip():
                if attempt > 1:
                    append_event("llm.provider.retry_recovered", "OpenAI-compatible chat provider returned output after retry", {"provider": provider, "attempt": attempt, "max_attempts": max_attempts, "prior_errors": retryable_errors})
                return content.strip() + "\n"

            message = f"OpenAI-compatible chat provider choices.0.message.content is empty [empty_response] (provider={provider}, attempt {attempt}/{max_attempts})"
            retryable_errors.append(message)
            append_event("llm.provider.retryable_failure", message, {"provider": provider, "interface": interface, "attempt": attempt, "max_attempts": max_attempts, "reason": "empty_response"})

        if attempt < max_attempts and retry_backoff_seconds > 0:
            time.sleep(retry_backoff_seconds * attempt)

    detail = "; ".join(retryable_errors[-max_attempts:]) or "unknown retryable provider failure"
    raise SystemExit(f"OpenAI-compatible chat provider failed after {max_attempts} attempt(s) (provider={provider}, interface={interface}): {detail}")


def _provider_response(provider: str, provider_config: dict[str, Any], prompt_path: Path, prompt_text: str) -> str:
    prompt_text = sanitize_llm_text(prompt_text)
    interface = provider_config.get("interface", CLI_PROVIDER_INTERFACE)
    if interface == CLI_PROVIDER_INTERFACE:
        return _cli_response(provider_config, prompt_text)
    if interface == API_PROVIDER_INTERFACE:
        return _api_response(provider_config, prompt_path, prompt_text)
    if interface == OPENAI_CHAT_PROVIDER_INTERFACE:
        return _openai_chat_response(provider, provider_config, prompt_path, prompt_text)
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
