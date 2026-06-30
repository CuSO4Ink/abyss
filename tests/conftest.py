"""Shared pytest fixtures for Abyss self-iteration tests.

The whole point of this module is *isolation*: no test may read or write the
real ``.local/runtime`` directory of the working repository, and no test may
mutate real source files. We achieve that by redirecting both ``repo_root`` and
``runtime_root`` (and the module-level directory constants that were already
computed from them at import time) onto a temporary, self-contained mini-repo.

Strategy:
  * Build a tmp "mini repo" that mirrors just enough real structure for the
    self-iteration flow (abyss_cli/ marker dir, artifacts/drafts/, ROADMAP.md,
    rules/ stubs the flow reads, and a .local/runtime tree).
  * Patch ``abyss_cli.utils.repo_root`` / ``runtime_root`` to point at it.
  * Re-point every already-evaluated ``*_DIR`` constant in the modules that
    cached them at import time, because ``from .utils import runtime_root`` was
    only called once during import.

This file deliberately contains no test logic; it is pure scaffolding so the
individual test modules stay focused and readable.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import pytest


# Modules that cached `runtime_root()/...` or `repo_root()/...` constants at
# import time. For each, we list the attribute names that must be redirected
# onto the temporary runtime/repo tree.
_RUNTIME_CONST_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "abyss_cli.changeset": {"runtime": ("CHANGESETS_DIR", "EXECUTIONS_DIR")},
    "abyss_cli.patch_compiler": {"runtime": ("CHANGESETS_DIR",)},
    # audit.AUDIT_FILE is written by append_event() on *every* changeset
    # import/dry-run/approve/apply. It was previously NOT redirected, so tests
    # leaked audit lines into the real .local/runtime/audit/audit.md. Redirect it.
    "abyss_cli.audit": {"runtime": ("AUDIT_FILE",)},
    "abyss_cli.harness_review": {"runtime": ("HARNESS_REVIEWS_DIR",)},
    "abyss_cli.result": {"runtime": ("ACTIONS_DIR", "REVIEWS_DIR", "IMPORTS_DIR")},
    "abyss_cli.review": {"runtime": ("REVIEWS_DIR", "ACTIONS_DIR")},
    "abyss_cli.llm_executor": {"runtime": ("LLM_RESULTS_DIR", "LLM_USAGE_DIR")},
    "abyss_cli.direct_auth": {"runtime": ("DIRECT_AUTH_DIR",)},
    "abyss_cli.external_collab": {"runtime": ("EXTERNAL_RESULTS_DIR", "FEEDBACK_CARDS_DIR")},
    "abyss_cli.evolution_analysis": {"runtime": ("EVOLUTION_ANALYSES_DIR",)},
    "abyss_cli.fsm": {"runtime": ("FSM_DIR",)},
    "abyss_cli.intent": {"runtime": ("INTENTS_DIR",)},
    "abyss_cli.prompt_builder": {"runtime": ("PROMPT_DIR",)},
    "abyss_cli.workflow": {
        "runtime": ("WORKFLOWS_DIR", "REPORTS_DIR", "LOCK_PATH", "CONTEXT_PACKS_DIR"),
    },
    "abyss_cli.owner": {"runtime": ("OWNER_ITEMS_DIR",)},
    "abyss_cli.meta_governance": {
        "runtime": ("META_GOVERNANCE_DIR", "META_GOVERNANCE_PACKETS_DIR"),
    },
    "abyss_cli.evolution": {
        "runtime": ("EVOLUTION_DIR", "REQUESTS_DIR", "PROPOSALS_DIR", "SMOKE_DIR"),
        "repo": ("GOVERNANCE_PATH", "ROADMAP_PATH"),
    },
    "abyss_cli.agent_runner": {
        "runtime": ("AGENT_PROMPT_DIR", "AGENT_RUNS_DIR"),
        "repo": ("AGENTS_FILE",),
    },
    "abyss_cli.context_pack": {
        "runtime": ("CONTEXT_PACKS_DIR",),
        "repo": (
            "SYSTEM_BRIEF_FILE",
            "MODULES_FILE",
            "CONTEXT_MANIFEST_FILE",
            "ARCHITECTURE_COGNITION_FILE",
        ),
    },
}


def _build_mini_repo(root: Path) -> None:
    """Create a minimal but coherent repo tree under ``root``."""
    (root / "abyss_cli").mkdir(parents=True, exist_ok=True)
    (root / "abyss_cli" / "__init__.py").write_text("", encoding="utf-8")
    (root / "abyss_cli" / "example.py").write_text(
        "def sample_function():\n    return 1\n", encoding="utf-8"
    )
    (root / "artifacts" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Mini Repo\n", encoding="utf-8")
    (root / "SYSTEM_MAP.md").write_text("# System Map\n\nstub\n", encoding="utf-8")
    (root / "ABYSS_CONSTITUTION.md").write_text("# Constitution\n\nstub\n", encoding="utf-8")
    (root / "ROADMAP.md").write_text(
        "# Roadmap\n\n## Pending proposals\n", encoding="utf-8"
    )
    (root / ".local" / "runtime").mkdir(parents=True, exist_ok=True)


@pytest.fixture()
def mini_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect repo_root + runtime_root and all cached dir constants to tmp.

    Critical: every module does ``from .utils import repo_root, runtime_root``,
    which binds an *independent* reference in that module's namespace. Patching
    only ``abyss_cli.utils`` is therefore insufficient and would let real source
    files get mutated. We patch the bound reference in *every* loaded
    ``abyss_cli`` module, plus re-anchor the cached ``*_DIR`` constants.
    """
    import sys
    import abyss_cli  # noqa: F401  ensure package import side effects ran

    root = tmp_path / "repo"
    _build_mini_repo(root)
    runtime = root / ".local" / "runtime"

    import abyss_cli.utils as utils

    fake_repo_root = lambda: root
    fake_runtime_root = lambda: runtime

    monkeypatch.setattr(utils, "repo_root", fake_repo_root)
    monkeypatch.setattr(utils, "runtime_root", fake_runtime_root)

    # Patch the independently-bound references inside every loaded submodule.
    for name, module in list(sys.modules.items()):
        if not name.startswith("abyss_cli"):
            continue
        if module is None:
            continue
        if hasattr(module, "repo_root"):
            monkeypatch.setattr(module, "repo_root", fake_repo_root, raising=False)
        if hasattr(module, "runtime_root"):
            monkeypatch.setattr(module, "runtime_root", fake_runtime_root, raising=False)

    # Re-anchor module-level directory constants computed at import time.
    for module_name, groups in _RUNTIME_CONST_MAP.items():
        module = importlib.import_module(module_name)
        for attr in groups.get("runtime", ()):  # re-anchor under tmp runtime
            old: Path = getattr(module, attr)
            rel = _relative_under(old, "runtime")
            monkeypatch.setattr(module, attr, runtime / rel)
        for attr in groups.get("repo", ()):  # re-anchor under tmp repo root
            old = getattr(module, attr)
            rel = _relative_under(old, "repo")
            monkeypatch.setattr(module, attr, root / rel)

    return root


def _relative_under(path: Path, anchor: str) -> str:
    """Return the path tail after the runtime/repo boundary.

    For runtime constants the original is ``<real_repo>/.local/runtime/<tail>``;
    for repo constants it is ``<real_repo>/<tail>``. We reconstruct ``<tail>``
    so it can be re-rooted under the temp tree.
    """
    parts = path.parts
    if anchor == "runtime":
        # find ".local" / "runtime" marker
        for i in range(len(parts) - 1):
            if parts[i] == ".local" and parts[i + 1] == "runtime":
                return str(Path(*parts[i + 2:])) if parts[i + 2:] else ""
        return path.name
    # anchor == "repo": tail is everything after the repo root. We approximate
    # by taking the path relative to the first ".local"-free segment chain.
    # Simplest robust approach: use the portion after the known repo dir name.
    # Since real constants are repo_root()/<rel>, and repo_root() is the parent
    # of "abyss_cli", we locate "abyss_cli" or known top-level names.
    return _repo_relative_tail(path)


def _repo_relative_tail(path: Path) -> str:
    parts = list(path.parts)
    # Known top-level repo entries used by constants we redirect.
    for marker in ("rules", "ROADMAP.md", "ABYSS_CONSTITUTION.md", "README.md", "SYSTEM_MAP.md"):
        if marker in parts:
            idx = parts.index(marker)
            return str(Path(*parts[idx:]))
    return path.name


@pytest.fixture()
def make_envelope() -> Callable[..., dict[str, Any]]:
    """Factory for Request Envelope dicts used by meta-governance tests."""

    def _factory(**overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "schema": "abyss.request_envelope.v1",
            "id": "req_test_0001",
            "request_type": "maintenance_request",
            "title": "test request",
            "description": "",
            "scope": [],
            "risk_level": "medium",
        }
        base.update(overrides)
        return base

    return _factory
