from __future__ import annotations

import json
from pathlib import Path

import abyss_cli.llm_executor as llm_executor


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_openai_chat_usage_cache_telemetry_is_sanitized_and_persisted(mini_repo, monkeypatch):
    prompt_dir = llm_executor.PROMPT_DIR
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / "ppkg_usage_test.md"
    prompt_path.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        llm_executor,
        "load_provider_config",
        lambda: {
            "providers": {
                "deepseek": {
                    "enabled": True,
                    "interface": llm_executor.OPENAI_CHAT_PROVIDER_INTERFACE,
                    "base_url": "https://api.example.test",
                    "endpoint": "/chat/completions",
                    "model": "deepseek-chat",
                    "timeout_seconds": 1,
                    "max_attempts": 1,
                }
            }
        },
    )
    monkeypatch.setattr(llm_executor, "import_result", lambda result_path, intent_path: [])

    payload = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {
            "prompt_tokens": 600000,
            "completion_tokens": 10,
            "total_tokens": 600010,
            "prompt_cache_hit_tokens": 123456,
            "prompt_cache_miss_tokens": 476544,
            "prompt_tokens_details": {"cached_tokens": 123456, "ignored_text": "do-not-store"},
            "secret_like_field": "must-not-persist",
        },
    }
    monkeypatch.setattr(llm_executor.urllib.request, "urlopen", lambda request, timeout: _FakeHTTPResponse(payload))

    result_path, proposals = llm_executor.run_llm(str(prompt_path), "deepseek")

    assert proposals == []
    assert result_path.read_text(encoding="utf-8") == "ok\n"
    usage_files = list(llm_executor.LLM_USAGE_DIR.glob("*.json"))
    assert len(usage_files) == 1
    usage_record = json.loads(usage_files[0].read_text(encoding="utf-8"))

    assert usage_record["schema"] == "abyss.llm_usage_diagnostics.v1"
    assert usage_record["provider"] == "deepseek"
    assert usage_record["model"] == "deepseek-chat"
    assert usage_record["usage"] == {
        "prompt_tokens": 600000,
        "completion_tokens": 10,
        "total_tokens": 600010,
        "prompt_cache_hit_tokens": 123456,
        "prompt_cache_miss_tokens": 476544,
    }
    assert usage_record["prompt_tokens_details"] == {"cached_tokens": 123456}
    assert "secret_like_field" not in json.dumps(usage_record)
    assert "ignored_text" not in json.dumps(usage_record)
