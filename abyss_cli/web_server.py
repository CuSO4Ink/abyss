"""Thin HTTP server for Abyss dashboard (R096).

Pure Python stdlib — zero external dependencies.
Serves a static HTML dashboard and JSON API endpoints that call
existing CLI/core functions directly.

Architecture:
    Browser (Alpine.js, CDN)
        -> JSON over HTTP
    Python http.server (this file, calls core functions)
        -> Abyss CLI modules (brain, summary, memory, adapter, etc.)

All endpoints are read-only in Phase A. No writes, no execution, no approval.
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "web"


# ---------------------------------------------------------------------------
#  Data collectors — thin wrappers over existing core functions
# ---------------------------------------------------------------------------

def _collect_summary() -> dict[str, Any]:
    from .summary import build_summary
    return build_summary(include_check=False)


def _collect_integrity() -> dict[str, Any]:
    from .integrity import run_checks
    ok, messages = run_checks()
    return {"ok": ok, "messages": messages}


def _collect_brain_context() -> dict[str, Any]:
    from .brain import build_brain_context
    return build_brain_context()


def _collect_brain_brief() -> dict[str, Any]:
    from .brain import build_brain_brief
    return build_brain_brief()


def _collect_memory_records() -> list[dict[str, Any]]:
    from .memory import list_memory_records
    return list_memory_records()


def _collect_working_memory() -> list[dict[str, Any]]:
    from .brain import load_working_memory
    return load_working_memory(limit=50)


def _collect_outbox_needs() -> list[dict[str, Any]]:
    from .external_adapter import list_needs
    return list_needs()


def _collect_roadmap() -> dict[str, Any]:
    from .roadmap_current import render_roadmap_current_json
    raw = render_roadmap_current_json()
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _collect_workflows() -> list[dict[str, Any]]:
    from .workflow import list_workflows
    return list_workflows()


def _collect_owner_items() -> list[dict[str, Any]]:
    from .owner import list_owner_items
    return list_owner_items()


def _collect_skills() -> list[dict[str, Any]]:
    from .skill import render_skills_json
    raw = render_skills_json()
    return json.loads(raw) if isinstance(raw, str) else raw


def _collect_fsm_state() -> dict[str, Any]:
    from .brain import _read_fsm_state
    return _read_fsm_state()


def _collect_git_status() -> dict[str, Any]:
    from .utils import run_git
    try:
        status = run_git(["status", "--short", "--branch"], allow_fail=True)
        return {"status": status.strip()}
    except Exception as exc:
        return {"status": "", "error": str(exc)}


# ---------------------------------------------------------------------------
#  JSON API route table
# ---------------------------------------------------------------------------

API_ROUTES: dict[str, Any] = {
    "/api/summary":          _collect_summary,
    "/api/integrity":        _collect_integrity,
    "/api/brain/context":    _collect_brain_context,
    "/api/brain/brief":      _collect_brain_brief,
    "/api/brain/memory":     _collect_working_memory,
    "/api/memory":           _collect_memory_records,
    "/api/outbox/needs":     _collect_outbox_needs,
    "/api/roadmap":          _collect_roadmap,
    "/api/workflows":        _collect_workflows,
    "/api/owner/items":      _collect_owner_items,
    "/api/skills":           _collect_skills,
    "/api/fsm/state":        _collect_fsm_state,
    "/api/git/status":       _collect_git_status,
}


# ---------------------------------------------------------------------------
#  HTTP handler
# ---------------------------------------------------------------------------

class AbyssHandler(SimpleHTTPRequestHandler):
    """Serve static files from web/ dir and JSON API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_static_dir()), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        # API routes
        if parsed.path in API_ROUTES:
            self._serve_json_api(parsed.path)
            return

        # Dashboard root -> index.html
        if parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"
        elif parsed.path == "/dashboard":
            self.path = "/index.html"

        super().do_GET()

    def _serve_json_api(self, route: str) -> None:
        try:
            collector = API_ROUTES[route]
            data = collector()
            body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            self._json_response(200, body)
        except Exception as exc:
            error_body = json.dumps({"error": str(exc), "route": route}, indent=2)
            self._json_response(500, error_body)

    def _json_response(self, code: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args) -> None:
        # Suppress default logging; print concise request lines
        pass


def run_server(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    """Start the Abyss web dashboard server."""
    server = HTTPServer((host, port), AbyssHandler)

    url = f"http://{host}:{port}"
    print(f"Abyss dashboard running at {url}")
    print(f"Static dir: {_static_dir()}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
