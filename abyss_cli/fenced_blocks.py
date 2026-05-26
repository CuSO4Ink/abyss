from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

FENCE_RE = re.compile(r"```")


def _names(value: str | Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _start_re(block_names: str | Sequence[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(name) for name in _names(block_names))
    return re.compile(rf"```(?:{alternatives})\s*", re.IGNORECASE)


def parse_json_object(raw_json: str, *, object_error: str = "JSON block was not an object") -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        repaired = re.sub(r",\s*([}\]])", r"\1", raw_json)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError:
            return None, str(exc)
    return (parsed, None) if isinstance(parsed, dict) else (None, object_error)


def extract_named_json_blocks(text: str, block_names: str | Sequence[str]) -> list[str]:
    """Extract JSON object text from named fenced blocks.

    The scanner tries each possible closing fence until the enclosed text parses as
    a JSON object. This tolerates literal triple-backticks inside JSON strings,
    where a naive non-greedy regex would stop too early.
    """
    blocks: list[str] = []
    for start in _start_re(block_names).finditer(text):
        content_start = start.end()
        for fence in FENCE_RE.finditer(text, content_start):
            raw_json = text[content_start:fence.start()].strip()
            if not raw_json:
                continue
            parsed, _error = parse_json_object(raw_json)
            if parsed is not None:
                blocks.append(raw_json)
                break
    return blocks


def parse_named_json_block(text: str, block_names: str | Sequence[str], *, object_error: str = "JSON block was not an object") -> tuple[dict[str, Any] | None, str | None, bool]:
    """Parse the first JSON object from a named fenced block.

    Returns (record, parse_error, saw_block). A missing block returns
    (None, None, False); a present but unparseable block returns
    (None, error, True).
    """
    saw_block = False
    for start in _start_re(block_names).finditer(text):
        saw_block = True
        content_start = start.end()
        last_error: str | None = None
        for fence in FENCE_RE.finditer(text, content_start):
            raw_json = text[content_start:fence.start()].strip()
            if not raw_json:
                continue
            parsed, error = parse_json_object(raw_json, object_error=object_error)
            if parsed is not None:
                return parsed, None, saw_block
            last_error = error
        if last_error:
            return None, last_error, saw_block
    return None, None, saw_block
