from __future__ import annotations

import json
from pathlib import Path

from abyss_cli.utils import now_iso, repo_root

ROOT = repo_root()
SCRIPT = ROOT / "artifacts" / "drafts" / "build_r060_changeset.py"
text = SCRIPT.read_text(encoding="utf-8")
prefix = text.split("record = {", 1)[0]
namespace: dict[str, object] = {}
exec(compile(prefix, str(SCRIPT), "exec"), namespace)

ops = [
    ("op_001", "abyss_cli/workflow.py", "workflow_old", "workflow_new"),
    ("op_002", "abyss_cli/workflow.py", "workflow_branch_old", "workflow_branch_new"),
    ("op_003", "abyss_cli/summary.py", "summary_categories_old", "summary_categories_new"),
    ("op_004", "abyss_cli/summary.py", "summary_outcome_old", "summary_outcome_new"),
    ("op_005", "abyss_cli/context_pack.py", "context_manifest_old", "context_manifest_new"),
    ("op_006", "abyss_cli/agent_runner.py", "agent_runner_old", "agent_runner_new"),
]
record = {
    "schema": "abyss.change_set.v1",
    "id": "chg_r060_repeated_placeholder_handling",
    "roadmap_id": "R060",
    "summary": "Deterministically block repeated placeholder format_feedback and preserve concrete context-request files",
    "risk_level": "L2",
    "status": "proposed",
    "operations": [],
    "created_at": now_iso(),
    "updated_at": now_iso(),
    "metadata": {
        "corrects_workflow_id": "wf_20260526_135904_03e5e5",
        "corrects_block_event": "implementation_repeated_placeholder_blocked",
    },
}
for op_id, path, old_name, new_name in ops:
    record["operations"].append({
        "id": op_id,
        "kind": "fs.replace_exact",
        "target": {"path": path},
        "input": {
            "old_content": namespace[old_name],
            "new_content": namespace[new_name],
        },
    })
record["operations"].extend([
    {"id": "op_007", "kind": "check.command", "input": {"command": "python -m compileall -q abyss_cli"}},
    {"id": "op_008", "kind": "check.command", "input": {"command": "python -m abyss_cli check"}},
    {"id": "op_009", "kind": "check.command", "input": {"command": "python -m abyss_cli summary --check"}},
])
out = ROOT / "artifacts" / "drafts" / "chg_r060_repeated_placeholder_handling.json"
out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(out)
