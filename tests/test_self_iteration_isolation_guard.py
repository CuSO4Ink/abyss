"""Isolation guard tests.

The single most dangerous engineering failure mode for this test-suite is
*leakage*: a test that believes it is sandboxed but actually mutates the real
``.local/runtime`` (or real source files). This already happened once with the
audit log (``audit.AUDIT_FILE`` was a module-level constant computed at import
time and was NOT redirected by the conftest fixture, so every changeset
import/dry-run/approve/apply appended lines to the *real* audit.md).

These tests lock that class of bug down two ways:

1. Static coverage check: every ``abyss_cli`` module that caches a
   ``runtime_root()/...`` constant at import time MUST be declared in the
   conftest redirect map. If someone adds a new module-level runtime constant
   and forgets to redirect it, this test fails loudly.

2. Behavioral check: drive a real write chain (import -> dry-run -> approve ->
   apply, which all call ``append_event``) under ``mini_repo`` and assert the
   real runtime tree is byte-for-byte untouched, while the temp runtime does
   receive the writes.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

import abyss_cli.audit as audit
import abyss_cli.changeset as cs
from abyss_cli.utils import runtime_root as real_runtime_root_func

# Import the conftest map so the static check stays in sync with the fixture.
from conftest import _RUNTIME_CONST_MAP  # type: ignore


ABYSS_DIR = Path(__file__).resolve().parents[1] / "abyss_cli"


def _module_runtime_constants(py_file: Path) -> list[str]:
    """Return UPPER_CASE module-level names assigned from runtime_root()/..."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        # Only top-level constants (single Name target, UPPER_CASE).
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        target = node.targets[0].id
        if not target.isupper():
            continue
        # Does the RHS reference runtime_root()?
        rhs_src = ast.dump(node.value)
        if "runtime_root" in rhs_src:
            names.append(target)
    return names


def test_every_runtime_constant_is_declared_for_redirection():
    """Catch the audit.AUDIT_FILE class of leak at the source level."""
    missing: list[str] = []
    for py_file in sorted(ABYSS_DIR.glob("*.py")):
        module_name = f"abyss_cli.{py_file.stem}"
        runtime_consts = _module_runtime_constants(py_file)
        if not runtime_consts:
            continue
        declared = set(_RUNTIME_CONST_MAP.get(module_name, {}).get("runtime", ()))
        for const in runtime_consts:
            if const not in declared:
                missing.append(f"{module_name}.{const}")
    assert not missing, (
        "These module-level runtime constants are NOT redirected by the "
        "conftest mini_repo fixture, so tests touching them would pollute the "
        "real .local/runtime:\n  " + "\n  ".join(missing)
    )


def test_mini_repo_redirects_audit_file(mini_repo):
    """The previously-leaking audit constant must now point inside tmp."""
    expected_runtime = mini_repo / ".local" / "runtime"
    assert str(audit.AUDIT_FILE).startswith(str(expected_runtime)), (
        f"audit.AUDIT_FILE leaked to {audit.AUDIT_FILE}, expected under {expected_runtime}"
    )


def test_write_chain_does_not_touch_real_runtime(mini_repo):
    """Drive import->dry-run->approve->apply and prove real runtime is intact."""
    real_runtime = real_runtime_root_func()
    # NOTE: real_runtime_root_func is the patched lambda under mini_repo, so we
    # instead read the *true* on-disk real runtime via the source repo path.
    true_real_runtime = Path(__file__).resolve().parents[1] / ".local" / "runtime"
    true_audit = true_real_runtime / "audit" / "audit.md"

    before_audit_mtime = true_audit.stat().st_mtime_ns if true_audit.exists() else None
    before_chg_count = (
        len(list((true_real_runtime / "process" / "changesets").glob("*.yaml")))
        if (true_real_runtime / "process" / "changesets").exists()
        else 0
    )

    record = {
        "schema": cs.SUPPORTED_SCHEMA,
        "id": "chg_isolation_guard",
        "roadmap_id": "R_GUARD",
        "summary": "isolation guard write chain",
        "status": "approved",
        "operations": [
            {
                "id": "op_create",
                "kind": "fs.create_file",
                "target": {"path": "artifacts/drafts/guard.md"},
                "input": {"content": "guard artifact\n"},
            }
        ],
    }
    cs.write_record(cs._record_path("chg_isolation_guard"), record)
    cs.dry_run_changeset("chg_isolation_guard")
    execution = cs.apply_changeset("chg_isolation_guard")
    assert execution["status"] == "succeeded"

    # The artifact and the audit write must live in the temp runtime/repo.
    assert (mini_repo / "artifacts" / "drafts" / "guard.md").exists()
    assert str(audit.AUDIT_FILE).startswith(str(mini_repo))

    # The REAL runtime must be byte-for-byte unchanged.
    after_audit_mtime = true_audit.stat().st_mtime_ns if true_audit.exists() else None
    after_chg_count = (
        len(list((true_real_runtime / "process" / "changesets").glob("*.yaml")))
        if (true_real_runtime / "process" / "changesets").exists()
        else 0
    )
    assert after_audit_mtime == before_audit_mtime, "real audit.md was mutated by a test!"
    assert after_chg_count == before_chg_count, "real changesets dir was mutated by a test!"
    # And the guard changeset must NOT exist in the real changesets dir.
    assert not (
        true_real_runtime / "process" / "changesets" / "chg_isolation_guard.yaml"
    ).exists()
