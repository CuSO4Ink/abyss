# Drafts Archive 2026-05-26

This archive contains low-risk `artifacts/drafts` files moved out of the active drafts surface on 2026-05-26.

No files were permanently deleted.

## Archive rationale

`artifacts/drafts/` is a low-risk generated draft surface, but many files in it had become historical implementation residue. The cleanup keeps active or referenced candidate material in `artifacts/drafts/` and moves unreferenced one-off generators, probes, rollback helpers, and obsolete smoke ChangeSet inputs into this archive.

## Long-term keep in active drafts

- `.gitkeep` — required to keep the active drafts directory present.
- `candidate_patch_request_semantics_v0.md` — directly referenced by ROADMAP R047/R048 and runtime context records as preserved candidate material.

## Retained in active drafts as referenced audit / ChangeSet evidence

- `autonomous_workflow_bootstrap.md`
- `build_r011_changeset.py`
- `candidate_patch_request_semantics_v0.md`
- `chg_r012_implementation_evidence_guard.json`
- `chg_r021_implementation_agent_stability_corrected.json`
- `chg_r021_implementation_agent_stability_corrected_v2.json`
- `chg_r041_corrected.json`
- `chg_r045_corrected.json`
- `chg_r049_corrected_integrity_process_records_helper.json`
- `chg_r049_corrected_integrity_review_refs_helper.json`
- `chg_r049_corrected_integrity_runtime_records_helper.json`
- `chg_r049_corrected_integrity_static_helpers.json`
- `chg_r049_corrected_integrity_structure_helper.json`
- `chg_r050_corrected_safe_target_file_context.json`
- `chg_r051_corrected_shared_fenced_blocks_parser.json`
- `chg_r052_corrected_meta_evolution_analysis_parser_reuse.json`
- `chg_r052_corrected_meta_evolution_analysis_parser_reuse_v2.json`
- `chg_r056_corrected_anchor_placeholder_feedback.json`
- `chg_r060_repeated_placeholder_handling.json`
- `chg_rule_source_registry_v0_corrected.json`
- `chg_rule_source_registry_v0_docs_and_checks.json`
- `decorative_symbol_validation_probe.json`
- `edit_plan_probe_result.md`
- `implementation_readiness_check.md`
- `probe_patch_compiler.py`
- `r003_agent_bootstrap_report.md`
- `r003_executor_smoke.md`
- `r003_implementation_agent_smoke.md`
- `r011_bad_import_probe.json`
- `r011_deterministic_import_validation_changeset.json`
- `r022_edit_plan_compiler_smoke.md`
- `r052_regression_result.md`
- `r061_corrected_placeholder_preflight_changeset.json`

## Archived now

- `build_r060_changeset.py`
- `chg_r049_corrected_integrity_static_helpers_syntax_fix.json`
- `decorative_symbol_validation_probe.yaml`
- `emit_r060_changeset_from_script_vars.py`
- `make_r049_static_helpers_changeset.py`
- `make_r056_corrected_changeset.py`
- `r003_smoke_changeset.json`
- `r056_placeholder_probe.py`
- `rollback_r060_direct_patch.py`

## Skipped because archive target already existed

- None

## Missing during cleanup

- None

## Delete recommendation

No immediate permanent deletion is recommended.

Deletion can be considered later only after:

1. archive has existed through at least one stable development cycle,
2. `python -m abyss_cli check` and `python -m abyss_cli summary --check` remain green,
3. no workflow, ChangeSet, Harness review, audit record, or prompt package depends on the active path,
4. Owner explicitly approves permanent removal.
