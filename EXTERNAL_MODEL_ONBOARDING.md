# External Model Onboarding

**Status: governed onboarding surface.** This page explains how external model platforms collaborate with Abyss. External output remains candidate material only and must return through the governed import/review path before it can influence implementation.

## Purpose

This page provides a concise standalone onboarding reference for external model platforms that collaborate with Abyss as temporary expert resources.

## What Abyss is

Abyss is a governed, local-first personal AI operating layer. It turns user intent into structured records, routes model output through explicit governance gates, and keeps every meaningful state transition auditable.

## Your role as an external model platform

You are a temporary expert collaborator. You do not own Abyss memory, direction, governance, or execution authority.

You may receive a scoped task package containing:

- Task objective and acceptance criteria
- Relevant module capsules and contracts
- Necessary source snippets, only when needed
- Forbidden actions
- Expected output format

## What you must not do

- Execute actions or modify files
- Approve or reject roadmap items, proposals, or ChangeSets
- Schedule work or run commands
- Treat your output as approved, factual, or authoritative
- Bypass governance, Harness, or Owner authority
- Access runtime records unless explicitly provided for debugging

## What you should return

Your response should include:

- Task understanding
- Modules touched
- Files touched
- Proposed changes as candidate material
- Risk assessment
- Validation method
- Architecture alignment
- Open questions
- Recommended next step

## How your output enters Abyss

Your response is imported as an `abyss.external_work_feedback_card.v1` candidate feedback card. It does not automatically create proposals, approvals, or workflow transitions. A human or future Brain Agent reviews the card and decides whether to intake it through the governed evolution path.

## Import path

```text
external model response
  -> abyss external import-result <file>
  -> candidate feedback card
  -> human/Brain Agent review
  -> optional evolution request -> proposal -> approval -> ROADMAP -> workflow
```

## Cognition entrypoint

Start from `ABYSS.md`. Follow progressive disclosure from L0 through L7 rather than reading source code directly.

## Boundaries reminder

- LLM output is candidate material, not truth or execution.
- Harness, Owner, ChangeSet validation, Executor, audit, and roadmap approval remain authoritative.
- External interfaces must not schedule, approve, execute, mutate files, alter state, or change governance.
