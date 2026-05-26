from pathlib import Path
from abyss_cli.patch_compiler import compile_edit_plan_from_agent_output
from abyss_cli.agent_runner import _context_request_from_invalid_edit_plan

text = '''```abyss-edit-plan
{
  "schema": "abyss.edit_plan.v1",
  "roadmap_id": "R056_PROBE",
  "summary": "placeholder probe",
  "edits": [
    {
      "id": "op_001",
      "kind": "replace_anchor",
      "target": {"path": "abyss_cli/patch_compiler.py"},
      "anchor": "def parse_edit_plan(text: str) -> dict[str, Any] | None:",
      "new_content": "existing code"
    }
  ]
}
```'''

record = compile_edit_plan_from_agent_output(
    text,
    agent_run_id="manual_r056_placeholder_probe",
    result_path=Path("artifacts/drafts/manual_r056_placeholder_probe.md"),
)
ctx = _context_request_from_invalid_edit_plan(record)
print(record.get("recoverable"), record.get("recovery_classification"), record.get("retry_guidance"))
print(ctx.get("request_kind") if ctx else None, ctx.get("recovery_classification") if ctx else None, ctx.get("retry_guidance") if ctx else None)
