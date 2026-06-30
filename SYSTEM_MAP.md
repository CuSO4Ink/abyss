# Abyss System Map

## Entry commands

```powershell
abyss status
abyss intent new "<goal>"
abyss intent list
abyss prompt build latest --copy
abyss prompt build-external "<task objective>" [--details "..."] [--copy]
abyss external import-result <external_response.md> [--task-id <id>] [--source-platform <name>]
abyss llm run <prompt-package|latest> --provider cli
abyss result import <response.md> --intent latest
abyss agent run harness --target latest
abyss agent run self_evolution --target latest
abyss agent run implementation --target latest
abyss harness review latest
abyss harness changeset-review latest
abyss evolution request "<summary>" [--details "..."]
abyss evolution list
abyss evolution show [latest|id]
abyss evolution propose <request>
abyss evolution approve <proposal>
abyss evolution reject <proposal> [--reason "..."]
abyss evolution status
abyss evolution finalize-direct-mode
abyss evolution smoke --provider cli
abyss changeset import <changeset.json>
abyss changeset list
abyss changeset show <latest|id>
abyss changeset dry-run <latest|id>
abyss changeset approve <latest|id>
abyss changeset reject <latest|id> [--reason "..."]
abyss changeset apply <latest|id>
abyss workflow start <approved-proposal|latest>
abyss workflow tick [workflow]
abyss workflow run [workflow]
abyss workflow watch [workflow] --interval 300
abyss workflow retry <workflow> [--from-stage implementation|changeset|harness_review]
abyss workflow list
abyss owner inbox
abyss owner show <owner-item>
abyss owner approve <owner-item>
abyss owner reject <owner-item> [--reason "..."]
abyss report list
abyss report show <latest|id>
abyss summary [--check]
abyss review list
abyss review approve <review>
abyss review reject <review>
abyss check
abyss data init|status|pull|push
abyss memory record --kind decision|direction --title "..." --body "..." [--related ids] [--tags ...]
abyss memory list [--kind ...] [--json]
abyss memory show <latest|id>
abyss memory project <latest|id>
```

## Core modules

- `abyss_cli/__main__.py` — CLI routing and command handlers.
- `abyss_cli/intent.py` — creates structured Intents.
- `abyss_cli/prompt_builder.py` — builds Prompt Packages from intents and context, including governed external developer collaboration packages.
- `abyss_cli/llm_executor.py` — optional LLM Executor; writes result files, then imports them.
- `abyss_cli/agent_runner.py` — runs configured agents through Agent Prompt Packages and provider result files, including self-evolution analysis, implementation ChangeSet generation, and Harness reviews.
- `abyss_cli/context_pack.py` — Context Broker; reads cognition/context manifests, prefers canonical Request Envelope `request_type` when present, injects `rules/architecture_cognition.yaml`, tracks context size budget, and records context pack metadata.
- `abyss_cli/request_rules.py` — canonical request semantics access layer; reads `rules/request_types.v1.yaml`, request envelope contract/schema locations, V0 request type defaults, and request_type-to-context task mapping.
- `abyss_cli/request_envelope.py` — builds and validates `abyss.request_envelope.v1` candidates; normalization grants no execution or approval authority.
- `abyss_cli/rule_registry.py` — deterministic Rule Source Registry V0 reader/validator; lists rule sources, validates source-file/command declarations, and exposes task-type rule files to Context Broker without granting execution or approval authority.
- `abyss_cli/external_collab.py` — imports external model output as candidate feedback cards without creating proposals, approvals, executions, or workflow transitions.
- `abyss_cli/harness_review.py` — parses HarnessAgent output into local harness review records for action proposals and ChangeSets.
- `abyss_cli/result.py` — imports LLM output and extracts action proposals.
- `abyss_cli/policy.py` — interprets `rules/policy.yaml`; no independent policy truth.
- `abyss_cli/review.py` — manages pending human reviews.
- `abyss_cli/audit.py` — appends local runtime audit events.
- `abyss_cli/data_sync.py` — connects the private GitHub data repository.
- `abyss_cli/evolution.py` — records governed self-iteration requests/proposals, approves or rejects proposals, ingests approved proposals into ROADMAP, manages direct-modification governance state, and runs LLM provider smoke tests.
- `abyss_cli/changeset.py` — imports, validates, approves, dry-runs, and applies approved `abyss.change_set.v1` records through a narrow local executor capability allowlist.
- `abyss_cli/workflow.py` — native autonomous workflow runner; advances approved roadmap work through implementation, dry-run, HarnessAgent review, owner approval, executor apply, check, and report without external assistant state-chaining.
- `abyss_cli/owner.py` — Owner Inbox approval surface for user decisions, including automatic continuation after approval.
- `abyss_cli/summary.py` — user-facing status overview for active workflows, pending approvals, failures, changesets, and optional integrity result.
- `abyss_cli/integrity.py` — checks repository structure, runtime references, workflow records, safety invariants, cognition-layer synchronization, module capsule completeness, contract/schema presence, and minimum-disclosure boundaries.
- `abyss_cli/brain.py` — renders Brain Agent v0 read-only status briefs; explains state and next candidates without execution, approval, mutation, or scheduling. R086: also renders a deterministic direction-alignment view over Memory v0 records (no LLM).
- `abyss_cli/disclosure.py` — audits `rules/context_manifest.yaml` against L0-L7 disclosure levels without replacing current context pack behavior.
- `abyss_cli/schema_validator.py` — validates structured records against the local JSON Schema subset; structural validation only, not governance approval.
- `abyss_cli/memory.py` — Memory v0 (R085): records Owner direction/decision knowledge as `abyss.memory_record.v1` and projects a record into an Obsidian note. Read-only projection, candidate knowledge only; no LLM, no promotion, no agent write authority.
- `abyss_cli/fsm.py` — periodic integrity-check state machine (unknown/idle/checking/needs_attention); runs ticks via `fsm tick` and `fsm watch`. Registered as module capsule in R087.

## Data flow

```text
user goal
  -> intent record
  -> prompt package
  -> manual LLM response OR standard CLI provider
  -> result file
  -> result import
  -> action proposal
  -> policy decision from rules/policy.yaml
  -> optional HarnessAgent review via Agent Prompt Package
  -> harness review record
  -> allow / review / deny
  -> audit event

approved roadmap item
  -> workflow start / tick / watch
  -> ImplementationAgent Prompt Package
  -> proposed abyss.change_set.v1 record
  -> deterministic dry-run validation
  -> HarnessAgent ChangeSet review
  -> Owner Inbox approval item
  -> explicit user ChangeSet approval through owner approve
  -> automatic workflow continuation
  -> narrow local executor apply
  -> execution record
  -> integrity check / audit event
  -> workflow report / summary

external collaboration objective
  -> prompt build-external
  -> Context Broker external_collaboration context pack
  -> architecture cognition + governance + module capsules + external protocol
  -> external model candidate response
  -> external import-result
  -> candidate feedback card
  -> human/Brain Agent review and governed intake path

normalized request semantics
  -> request envelope candidate
  -> request_type validation from rules/request_types.v1.yaml
  -> Context Broker request_type-aware context mapping
  -> later governed intake path if Owner chooses to proceed
```

```text
accepted rule source
  -> rules/rule_sources.v1.yaml registry entry
  -> rule_registry validation and listing
  -> Context Broker task-type rule source inclusion
  -> integrity check failure if registry is missing or malformed
  -> no execution, approval, scheduling, or mutation authority
```

Request envelopes, external collaboration packages, and feedback cards are cognition-first and candidate-material-only. They do not grant execution, approval, scheduling, file mutation, proposal creation, workflow transitions, or governance authority.

## System directories

- `abyss_cli/` — implementation code.
- `rules/` — rule truth sources; especially `rules/rule_sources.v1.yaml`, `rules/request_types.v1.yaml`, `rules/policy.yaml`, `rules/llm_providers.yaml`, `rules/agents.yaml`, `rules/modules.yaml`, `rules/context_manifest.yaml`, `rules/architecture_cognition.yaml`, and `rules/governance.yaml`.
- `rules/contracts/` — machine-readable contracts for structured records such as ChangeSets, context requests, blocked results, Harness reviews, evolution analyses, context packs, request envelopes, and external feedback cards. Contracts are L5 disclosure material and should be read before source code when record structure matters.
- `prompts/` — system, mode, and agent prompt templates.
- `artifacts/drafts/` — low-risk generated drafts.
- `process/*/.gitkeep` — process directory skeleton only; not the authoritative runtime process path.
- `.local/runtime/process/` — authoritative local runtime process path for generated records.
- `.local/knot_provider_workspace/` — provider/prompt-package scratch space; excluded from default context and only read when explicitly debugging provider or historical prompt-package behavior.
- `audit/README.md` — audit directory skeleton documentation only.
- `ABYSS_CONSTITUTION.md`, `README.md`, `SYSTEM_MAP.md`, `pyproject.toml` — system docs/config.
- `abyss-data/user_data/SYSTEM_MAP.md` — Obsidian-visible projection of this map.

## Runtime record directories

Runtime records are local machine state and do not belong in system Git.

- `.local/runtime/process/intents/`
- `.local/runtime/process/prompt_packages/`
- `.local/runtime/process/llm_results/`
- `.local/runtime/process/imports/`
- `.local/runtime/process/actions/`
- `.local/runtime/process/reviews/`
- `.local/runtime/process/agent_runs/`
- `.local/runtime/process/harness_reviews/`
- `.local/runtime/process/evolution_analyses/`
- `.local/runtime/process/changesets/`
- `.local/runtime/process/executions/`
- `.local/runtime/process/workflows/`
- `.local/runtime/process/owner_inbox/`
- `.local/runtime/process/reports/`
- `.local/runtime/memory/records/`
- `.local/runtime/evolution/requests/`
- `.local/runtime/evolution/proposals/`
- `.local/runtime/evolution/smoke_tests/`
- `.local/runtime/audit/audit.md`

Future option:

- `abyss-data/runtime/` for selected syncable runtime records.

## Governed evolution mode

The current direct-modification governance state is stored in `rules/governance.yaml`.

Before finalization, direct and timely human-assistant modification may continue only when the user explicitly authorizes the specific modification in the current conversation. After `direct_modification_mode` is disabled, ordinary system changes must enter through `abyss evolution request`, become proposals, receive explicit approval, and then enter `ROADMAP.md`.

This governance mode is a human collaboration rule, not an external interface permission. External interfaces still may only be used for unified standard LLM invocation.

## User data directories

System repo keeps only placeholders/README files here.
Real synced user data lives in the private GitHub data repo.

- `user_data/` — Obsidian-first active notes: Markdown, wiki links, frontmatter.
- `user_data/Home.md` — human entry point for active areas.
- `user_data/_attachments/` — relative note assets.
- `storage/archive/` — inactive archived material.
- default private data repo: `git@github-personal:CuSO4Ink/abyss-data.git`
- default local data path: `~/Documents/abyss-data`

## Forbidden

- P0: Do not use any external LLM client, Knot client, IM client, agent client, browser automation session, vendor-specific assistant runtime, or other external interface for anything other than unified standard LLM invocation: sending an Abyss Prompt / Prompt Package to an LLM model and returning model response text to Abyss.
- Do not use external interfaces for scheduling, triggering core workflows, notification delivery, file mutation, command execution, approval, rejection, audit, memory, policy decisions, state transitions, Git operations, Harness decisions, or self-evolution execution.
- Do not commit real `process/*` runtime records to the system repo.
- Do not commit `audit/audit.md` to the system repo.
- Do not duplicate policy logic between `policy.py` and `rules/policy.yaml`.
- Do not hardcode LLM provider secrets; use environment variables or `.local/`.
- Do not auto-execute action proposals from LLM Executor output.
- Do not let Agent output approve, reject, or execute actions; agents may only report or propose.
- Do not let the ChangeSet executor run arbitrary shell commands, browser automation, service/port management, external writes, Git push, policy/prompt/governance modification, or direct ROADMAP modification.
- After the final autonomous workflow bootstrap, external assistants must use Abyss user-facing interaction surfaces (`workflow`, `owner`, `summary`, `report`) and must not bypass them by directly editing system files or manually chaining internal state transitions, except for explicit human-authorized fault recovery.
- Do not put secrets, tokens, credentials, keys, or local caches in Git.
- Do not expose implementation or archive layers in default user retrieval.
- Do not put real Obsidian notes or bulk archives into the system repo.
