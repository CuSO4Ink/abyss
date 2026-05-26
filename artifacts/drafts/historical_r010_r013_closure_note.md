# Historical R010 / R013 Closure Note

Roadmap item: R072
Purpose: reclassify two older ambiguity points as structural review inputs rather than active health failures.

## Boundary statement

This note is documentation-only. It does not change source code, prompts, Harness behavior, workflow state, approval policy, provider behavior, or ROADMAP entries outside the governed R072 record.

## Current health interpretation

At the R072 baseline, active health is determined by `summary.state_semantics.active_health_gates`:

- `active_workflows`
- `pending_owner_items`
- `true_failures`
- `true_blocked`

R010 and R013 are not current active health failures unless a new workflow reproduces them into one of those active gates. They remain structural review inputs.

## R010: Harness Review Recovery

Classification: historical failed recovery sample / review input.

Current interpretation:

- R010 should not be treated as an active failure while `true_failures` and `true_blocked` remain zero.
- Later work added stronger deterministic validation, Harness review evidence, supersede accounting, and corrected ChangeSet accounting.
- The structural review should still ask whether Harness recovery has a current positive example and whether the old R010 record should be closed as superseded by later capabilities or retested with a narrow probe.

Remaining review questions:

1. What exact recovery case should count as a positive Harness Review Recovery example?
2. Should recovery mean retrying Harness review, reconstructing a lost review record, or revalidating a corrected ChangeSet?
3. Is the current supersede-by-corrected path enough, or does Harness need a separate recovery command?

## R013: Agent Prompt normalization

Classification: no-op / already-satisfied semantics sample / review input.

Current interpretation:

- R013 should not be treated as an active failure while `true_failures` and `true_blocked` remain zero.
- Its value is as a semantics case: already_satisfied, blocked, no-op, and satisfied_without_changes must be represented consistently.
- Later summary state semantics now distinguish active health gates from historical or expected buckets.

Remaining review questions:

1. Should already_satisfied be a terminal success, a blocked subtype, or a separate satisfied_without_changes outcome?
2. Should prompt normalization be retested as a new narrow item, or considered superseded by later output protocol hardening?
3. Which prompt changes require governance-core/meta handling versus ordinary source/prompt maintenance?

## Reclassification criteria

A historical item may remain a review input when all of these are true:

1. It is not present in `active_workflows`.
2. It does not create a pending Owner item.
3. It is absent from `true_failures`.
4. It is absent from `true_blocked`.
5. Its evidence is preserved in workflow, ChangeSet, report, or artifact records.
6. A future action can be expressed as a new explicit proposal rather than silently reopening the old item.

## Recommended handling during structural review

- Keep R010 and R013 visible in the review baseline.
- Do not fix or retest them opportunistically during unrelated maintenance.
- If either becomes relevant, create a new narrow proposal with clear acceptance criteria.
