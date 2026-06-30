```abyss-edit-plan
{
  "schema": "abyss.edit_plan.v1",
  "id": "chg_r085_demo_hello_banner",
  "roadmap_id": "R085",
  "summary": "Add demo_hello_banner helper function to abyss_cli/utils.py",
  "risk_level": "L2",
  "edits": [
    {
      "id": "op_001",
      "kind": "append_after_anchor",
      "target": {"path": "abyss_cli/utils.py", "anchor": "    return proc.returncode == 0"},
      "new_content": "\n\ndef demo_hello_banner() -> str:\n    return \"Hello from Abyss demo!\"\n"
    }
  ],
  "checks": ["python -m compileall -q abyss_cli", "python -m abyss_cli check"]
}
```
