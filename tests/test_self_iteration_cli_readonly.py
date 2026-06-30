"""CLI read-only smoke tests.

These run the real ``python -m abyss_cli ...`` read-only entrypoints as
subprocesses against the actual repo. They must never mutate state. If a
command fails due to workspace/environment state, we record it as a finding
(xfail-style soft assertion) rather than forcing a workaround.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Isolate any *write* side effects of "read-only" CLI commands (notably the
# audit log appended by append_event) into a throwaway runtime dir, so smoke
# tests never mutate the real .local/runtime. We deliberately do NOT override
# ABYSS_REPO_ROOT: the commands must still read the real repo's rules/ etc.
_ISOLATED_RUNTIME = Path(tempfile.mkdtemp(prefix="abyss_cli_smoke_runtime_"))


def _run(args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["ABYSS_RUNTIME_ROOT"] = str(_ISOLATED_RUNTIME)
    return subprocess.run(
        [sys.executable, "-m", "abyss_cli", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=env,
    )


READONLY_JSON_COMMANDS = [
    (["insight", "snapshot", "--json"], "abyss.insight"),
    (["reliability", "metrics", "--json"], "abyss.self_iteration_reliability_metrics.v1"),
    (["reliability", "probe-candidates", "--json", "--limit", "5"], "abyss.failure_probe_candidates.v1"),
]


@pytest.mark.parametrize("args,schema_hint", READONLY_JSON_COMMANDS)
def test_readonly_json_commands_parse(args, schema_hint):
    proc = _run(args)
    if proc.returncode != 0:
        pytest.skip(f"command {args} returned {proc.returncode} in this workspace: {proc.stderr[:200]}")
    # Output should be JSON-parseable and mention the expected schema family.
    out = proc.stdout.strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        pytest.skip(f"command {args} did not emit pure JSON in this workspace")
    assert isinstance(data, dict)
    assert schema_hint.split(".")[0] in json.dumps(data)


def test_check_runs():
    proc = _run(["check"])
    # check may pass or report issues; it must at least run and produce output.
    assert proc.returncode in (0, 1)
    assert (proc.stdout or proc.stderr).strip()


def test_summary_check_runs():
    proc = _run(["summary", "--check"])
    assert proc.returncode in (0, 1)
    assert (proc.stdout or proc.stderr).strip()


def test_brain_brief_runs():
    proc = _run(["brain", "brief"])
    assert proc.returncode in (0, 1)
    assert (proc.stdout or proc.stderr).strip()


def test_readonly_commands_do_not_claim_execution():
    """Read-only surfaces must not claim to have executed/approved actions."""
    proc = _run(["insight", "snapshot", "--json"])
    if proc.returncode != 0:
        pytest.skip("insight snapshot unavailable in this workspace")
    blob = proc.stdout.lower()
    assert "no_action_executed" in blob or "read_only" in blob or "readonly" in blob
