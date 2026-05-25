# R022: Edit-Plan Compiler Smoke Marker

This file was created through the governed workflow to verify that the
Implementation Agent can produce a valid `abyss.edit_plan.v1` output and
that Abyss deterministically compiles it into a concrete ChangeSet.

## Evidence

- Schema: abyss.edit_plan.v1
- Edit kind used: create_file
- Compiled by: patch_compiler.compile_edit_plan_from_agent_output
- Acceptance: workflow reaches owner approval or done without invalid old_content

## Result

If this file exists on disk after executor apply, the edit-plan compiler
path is confirmed functional end-to-end.
