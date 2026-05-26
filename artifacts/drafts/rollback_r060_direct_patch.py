from __future__ import annotations

from pathlib import Path

from abyss_cli.utils import repo_root

ROOT = repo_root()
SCRIPT = ROOT / "artifacts" / "drafts" / "build_r060_changeset.py"
text = SCRIPT.read_text(encoding="utf-8")
prefix = text.split("record = {", 1)[0]
namespace: dict[str, object] = {}
exec(compile(prefix, str(SCRIPT), "exec"), namespace)

for path, old_name, new_name in [
    ("abyss_cli/workflow.py", "workflow_old", "workflow_new"),
    ("abyss_cli/workflow.py", "workflow_branch_old", "workflow_branch_new"),
    ("abyss_cli/summary.py", "summary_categories_old", "summary_categories_new"),
    ("abyss_cli/summary.py", "summary_outcome_old", "summary_outcome_new"),
    ("abyss_cli/context_pack.py", "context_manifest_old", "context_manifest_new"),
    ("abyss_cli/agent_runner.py", "agent_runner_old", "agent_runner_new"),
]:
    file_path = ROOT / path
    current = file_path.read_text(encoding="utf-8")
    old = namespace[old_name]
    new = namespace[new_name]
    if new in current:
        current = current.replace(new, old, 1)
        file_path.write_text(current, encoding="utf-8")
        print(f"rolled back {path} {new_name}")
    elif old in current:
        print(f"already old {path} {old_name}")
    else:
        raise SystemExit(f"neither old nor new found for {path} {old_name}/{new_name}")
