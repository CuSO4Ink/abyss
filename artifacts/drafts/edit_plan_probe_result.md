```abyss-edit-plan
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
      "content": "patch compiler probe\n"
    }
  ],
  "checks": ["python -m abyss_cli check"]
}
```