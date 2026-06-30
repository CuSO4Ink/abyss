```abyss-edit-plan
{
  "schema": "abyss.edit_plan.v1",
  "id": "chg_demo_iteration_marker_r085",
  "roadmap_id": "R085",
  "summary": "Add read-only demo helper function demo_iteration_marker to abyss_cli/utils.py",
  "risk_level": "L2",
  "edits": [
    {
      "id": "op_001",
      "kind": "append_after_anchor",
      "target": {"path": "abyss_cli/utils.py"},
      "anchor": "    return proc.returncode == 0\n",
      "new_content": "\n\ndef demo_iteration_marker() -> str:\n    return \"abyss_demo_iteration_ok\"\n"
    }
  ],
  "checks": [
    "python -m compileall -q abyss_cli",
    "python -m abyss_cli check"
  ]
}
```
