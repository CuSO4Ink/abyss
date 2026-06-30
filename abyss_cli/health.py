"""Read-only health checks for Abyss providers.

Health checks are observational: they call configured providers and report
structured status without importing actions, writing result files, or mutating
workflow state.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .llm_executor import CLI_PROVIDER_INTERFACE, _provider_response, load_provider_config


def check_provider_health(provider: str = "cli") -> dict[str, Any]:
    """Call the configured real provider with a tiny prompt and return JSON-safe status."""
    started = time.perf_counter()
    config = load_provider_config()
    providers = config.get("providers", {}) if isinstance(config.get("providers"), dict) else {}
    provider_config = providers.get(provider)
    interface = CLI_PROVIDER_INTERFACE
    if isinstance(provider_config, dict):
        interface = str(provider_config.get("interface") or CLI_PROVIDER_INTERFACE)

    result: dict[str, Any] = {
        "schema": "abyss.provider_health.v1",
        "provider": provider,
        "interface": interface,
        "ok": False,
        "elapsed_ms": 0,
        "response_empty": True,
        "response_preview": "",
        "error": "",
        "no_action_executed": True,
    }

    if not isinstance(provider_config, dict) or not provider_config.get("enabled", False):
        result["error"] = f"LLM provider is not enabled or configured: {provider}"
        result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    prompt = "Return exactly: ABYSS_PROVIDER_HEALTH_OK"
    try:
        response, _usage_diagnostics = _provider_response(provider, provider_config, Path("provider_health_probe.md"), prompt)
    except SystemExit as exc:
        result["error"] = str(exc)
    except Exception as exc:  # defensive health check boundary
        result["error"] = f"{type(exc).__name__}: {exc}"
    else:
        stripped = response.strip()
        result["response_empty"] = not bool(stripped)
        result["response_preview"] = stripped[:200]
        result["ok"] = bool(stripped)
    finally:
        result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)

    return result


def render_provider_health_json(provider: str = "cli") -> str:
    """Render provider health as formatted JSON."""
    return json.dumps(check_provider_health(provider), ensure_ascii=False, indent=2)
