from pathlib import Path

from abyss_cli.patch_compiler import compile_edit_plan_from_agent_output

text = '''```abyss-edit-plan
{
  "schema": "abyss.edit_plan.v1",
  "id": "chg_probe_patch_compiler_no_apply",
  "roadmap_id": "RPROBE",
  "summary": "Probe deterministic edit plan compiler",
  "risk_level": "L2",
  "edits": [
    {
      "id": "op_001",
      "kind": "create_file",
      "target": {"path": "artifacts/drafts/patch_compiler_probe_output.txt"},
      "content": "patch compiler probe\\n"
    }
  ],
  "checks": ["python -m abyss_cli check"]
}
```'''

result_path = Path("artifacts/drafts/edit_plan_probe_result.md")
result_path.write_text(text, encoding="utf-8")
record = compile_edit_plan_from_agent_output(text, agent_run_id="probe", result_path=result_path)
print(record["id"])
print(record["validation"])
