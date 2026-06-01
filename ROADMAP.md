# Abyss Roadmap

Abyss is a harness-first personal AI orchestration system.

This roadmap is intentionally empty until the user approves roadmap items one by one.

## Roadmap authority

No feature, capability, backlog item, implementation slice, self-evolution target, scheduled task, agent role, integration, or delivery commitment may be added to this roadmap unless the user has explicitly approved that specific item.

Approval must be item-by-item. A general discussion, assistant suggestion, architecture explanation, or inferred preference is not enough to add a roadmap item.

## Transitional direct-modification mode

Until the governed self-iteration chain is complete and explicitly accepted by the user, the current human-assistant collaboration may continue to use direct, timely modification mode when the user explicitly authorizes the specific modification in the current conversation.

This transition rule does not weaken the P0 external interface boundary. External interfaces still may only be used for unified standard LLM invocation.

Direct modification mode must end for ordinary system changes once the governed self-iteration chain is complete and the user confirms the transition. After finalization, ordinary system changes must enter through `abyss evolution request`, become proposals, receive explicit approval, and only then enter the approved roadmap.

## Approved roadmap items

> Archive note: inactive/historical approved items R001-R069 were moved to [docs/archive/ROADMAP_R001_R069.md](docs/archive/ROADMAP_R001_R069.md).

> The active ROADMAP.md keeps the current reading window only; archived items remain available as historical approval evidence.

Current active/current-reading window: R070-R079.

### R070. R070 Insight v0 read-only snapshot

Source proposal: `evo_prop_20260526_184750_9c796d`.

Purpose: R070 Insight v0 read-only snapshot

Why it is needed: Source feature. Scope: add abyss_cli/insight.py and minimal CLI wiring in abyss_cli/__main__.py only. Goal: provide a read-only insight snapshot command that wraps existing summary data into a compact abyss.insight_snapshot.v1 JSON view for operator review. The command should not approve, execute, mutate files, call LLMs, change workflow states, edit ROADMAP, or perform Git operations. Suggested CLI: python -m abyss_cli insight snapshot --json. Snapshot fields: schema, generated_at, health from operations_health_counts, state_semantics from summary, active_workflows, pending_owner_items, true_failures, true_blocked, historical_review_inputs including invalid_changesets and diagnostics keys, and recommended_next_safe_action. Non-goals: no Brain behavior, no Memory, no provider calls, no scheduling, no state transition changes. Acceptance: command exists, emits valid JSON, uses existing build_summary include_check option, compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R071. R071 provider health check command

Source proposal: `evo_prop_20260526_185031_3dd1ac`.

Purpose: R071 provider health check command

Why it is needed: Source feature. Scope: add abyss_cli/health.py and minimal CLI wiring in abyss_cli/__main__.py only. Goal: provide a governed read-only provider health check command that invokes the configured real provider with a tiny prompt and reports JSON status, elapsed_ms, provider, interface, response_empty, response_preview, and error if any. Suggested CLI: python -m abyss_cli health provider --provider cli --json. Non-goals: no fake provider, no agent health matrix, no scheduling, no config mutation, no workflow state mutation, no action import, no ROADMAP manual edits. Acceptance: command calls the real configured provider path, writes no result files, imports no actions, returns JSON, compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R072. R072 historical R010 R013 closure note

Source proposal: `evo_prop_20260526_185407_f4361d`.

Purpose: R072 historical R010 R013 closure note

Why it is needed: Source-adjacent documentation maintenance. Scope: create artifacts/drafts/historical_r010_r013_closure_note.md only. Goal: record that R010 Harness Review Recovery and R013 Agent Prompt normalization are historical samples for structural review rather than active health failures; summarize current reclassification criteria and remaining review questions. Non-goals: no source code changes, no prompt changes, no Harness behavior changes, no workflow state mutation, no ROADMAP manual edits. Acceptance: note exists, states whether each item is active failure vs historical review input, references current summary state semantics, compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R073. R073 safe local git checkpoint command

Source proposal: `evo_prop_20260526_185618_042b35`.

Purpose: R073 safe local git checkpoint command

Why it is needed: Source feature. Scope: add abyss_cli/git_checkpoint.py and minimal CLI wiring in abyss_cli/__main__.py only. Goal: provide a safe local checkpoint helper that runs git status, git diff --stat, compileall, abyss check, and optionally creates a local commit with an explicit message. Non-goals: no push, no pull, no force push, no branch deletion, no remote operations, no rewrite history, no automatic scheduling, no bypass of checks. Suggested CLI: python -m abyss_cli checkpoint status --json and python -m abyss_cli checkpoint commit -m MESSAGE. Acceptance: status is read-only JSON; commit refuses dirty health checks, stages current working tree only when explicitly invoked, makes local commit only, compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R074. R073A read-only git checkpoint status

Source proposal: `evo_prop_20260526_185939_dc1179`.

Purpose: R073A read-only git checkpoint status

Why it is needed: Source feature. Scope: add abyss_cli/git_checkpoint.py and minimal CLI wiring in abyss_cli/__main__.py only. Goal: provide read-only local git checkpoint status as JSON using git status --porcelain, git diff --stat, and git diff --staged --stat. Non-goals: no commit command, no git add, no push, no pull, no fetch, no remote operations, no history rewrite, no staging, no config mutation, no scheduling. Suggested CLI: python -m abyss_cli checkpoint status --json. Acceptance: command is read-only, emits valid JSON, exposes clean/files_modified/files_added/files_deleted/files_untracked/diff_stat/diff_staged_stat, compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R075. R075 Context Broker task type rule table extraction

Source proposal: `evo_prop_20260526_190205_fe8ee3`.

Purpose: R075 Context Broker task type rule table extraction

Why it is needed: Source maintenance. Scope: abyss_cli/context_pack.py only if sufficient. Goal: reduce hard-coded keyword cascade fragility by extracting the task type keyword matching table into a structured constant inside the same module, preserving existing task type outputs and order. Non-goals: no disclosure policy changes, no allowed path changes, no forbidden path changes, no new context files, no rules/schema changes, no meta-governance behavior change, no broad rewrite. Acceptance: detect_task_type behavior is preserved for existing task categories; task matching order is represented as data rather than scattered conditional text; compileall/check/summary pass; a simple smoke command or inspection confirms common categories still map.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L3.

Acceptance check:

- Governance-core scope is explicitly classified before any implementation work.
- The proposal cannot proceed through ordinary self-evolution as a self-approving closure.
- Self Evolution and Brain Agent may analyze or prepare but cannot approve, apply, activate, or retroactively legitimize governance-core changes.
- Risk assessment, rollback plan, validation plan, activation note, old-rule review, and explicit Owner approval are required before implementation.
- Accepted governance-core changes activate only in a later workflow cycle, not in the cycle that approved them.
- No governance-core change was applied, activated, or scheduled by this proposal record.

### R076. R076 provider implementation-load reliability baseline

Source proposal: `evo_prop_20260526_194114_dd8f97`.

Purpose: R076 provider implementation-load reliability baseline

Why it is needed: Reliability maintenance before adding API model providers. Problem: provider health can pass short prompts while Implementation Agent workflow prompts still produce repeated filtered-empty responses. Goal: add a read-only implementation-load reliability baseline so Abyss can distinguish short_prompt_ok from implementation_prompt_empty/filtered_empty/timeout without silently switching models. Scope preference: provider health or insight/summary reporting files only; no provider credential changes, no automatic model switching, no network config changes, no governance policy changes. Acceptance: expose recent provider empty-response trend from runtime records; record/print a provider_degraded style diagnostic when repeated empty responses are observed under implementation-load context; preserve existing short health check behavior; validation compileall/check/summary passes.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R077. R077 provider reliability workflow empty-response counting

Source proposal: `evo_prop_20260526_194632_a025a7`.

Purpose: R077 provider reliability workflow empty-response counting

Why it is needed: Reliability maintenance follow-up to R076. Problem: the new provider_reliability baseline reports zero implementation-load empty responses because it only checks agent result file size and misses workflow history errors such as 'knot-cli response field was empty after filtering'. Goal: include recent workflow history/runtime records when counting implementation-load empty_or_filtered events, so the baseline reflects observed provider empty-response failures from workflow runs. Scope: abyss_cli/provider_reliability.py only if sufficient; no API provider integration, no model switching, no credentials, no network config, no governance policy changes. Acceptance: provider reliability report counts recent workflow empty-response events under implementation_load; provider_degraded can become true when thresholds are met; existing insight integration remains read-only; compileall/check/summary pass.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R078. R078 OpenAI-compatible API provider interface standard

Source proposal: `evo_prop_20260526_200705_45d140`.

Purpose: R078 OpenAI-compatible API provider interface standard

Why it is needed: Add a governed standard LLM provider interface for OpenAI-compatible chat completions, using DeepSeek as the first target configuration pattern. Scope: extend provider schema with http_openai_chat_completion_v1; preserve existing cli and http_json_prompt_package_response_v1 behavior; build non-streaming chat/completions request from the complete Abyss Prompt Package as one user message; support bearer_token_env without storing secrets; extract choices.0.message.content as execution text; treat reasoning_content as diagnostics only; classify auth/quota/rate-limit/server/network/bad-response/empty-response errors; document disabled-by-default DeepSeek local config example. Non-goals: no tool calls, no streaming v1, no automatic model switching, no hardcoded API keys, no governance policy changes, no external provider side effects beyond standard LLM text invocation.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- The proposal can be inspected independently of ROADMAP.md.
- No external interface is used for anything other than standard LLM invocation.

### R079. Agent specs declare default model invocation interface

Source proposal: `evo_prop_20260526_205151_f12a4d`.

Purpose: Agent specs declare default model invocation interface

Why it is needed: Add an explicit default model invocation interface field to each agent structure so an agent declares both its default provider name and the provider interface contract it expects. Scope: update agent spec/schema/validation and any read-only display needed so harness, self_evolution, implementation, and brain can declare default_provider_interface aligned with their provider. Preserve existing provider execution behavior: runtime still resolves provider configuration through llm_providers, no external provider gains scheduling, approval, file edit, git, audit, policy, or state-transition authority. Non-goals: no automatic model switching, no provider routing policy changes, no DeepSeek-as-default rollout, no secret/config changes beyond schema examples.

Minimal implementation slice:

- Convert the approved proposal into a bounded implementation plan.
- Keep implementation within the proposal scope unless the user approves a new roadmap item.
- Run integrity checks and capture review evidence before completion.

Expected user-visible result: the approved proposal progresses through the governed self-iteration chain instead of ad-hoc direct modification.

Risk level: L3.

Acceptance check:

- Governance-core scope is explicitly classified before any implementation work.
- The proposal cannot proceed through ordinary self-evolution as a self-approving closure.
- Self Evolution and Brain Agent may analyze or prepare but cannot approve, apply, activate, or retroactively legitimize governance-core changes.
- Risk assessment, rollback plan, validation plan, activation note, old-rule review, and explicit Owner approval are required before implementation.
- Accepted governance-core changes activate only in a later workflow cycle, not in the cycle that approved them.
- No governance-core change was applied, activated, or scheduled by this proposal record.

## Pending proposals

None.

## Roadmap item intake rule

Before adding any roadmap item, the assistant must present it to the user as a separate proposal and wait for explicit approval.

A proposal should include:

- Title.
- Purpose.
- Why it is needed.
- Minimal implementation slice.
- Expected user-visible result.
- Risk level.
- Acceptance check.

Only after the user explicitly approves that exact item may it be added to `Approved roadmap items`.

## Self-evolution boundary

Abyss may not use this roadmap as permission to implement anything unless the relevant item is listed under `Approved roadmap items`.

If Abyss discovers a potentially useful capability that is not listed under `Approved roadmap items`, it may only produce a proposal under `Pending proposals` or report it to the user. It must not implement the capability until the user explicitly approves it and the item is added to this roadmap.

## External interface P0 boundary

External LLM clients, Knot, IM clients, agent clients, browser automation sessions, vendor-specific assistant runtimes, or any other external interface must not become Abyss system dependencies.

The only allowed external interface role is a unified standard LLM invocation interface:

```text
Abyss Prompt / Prompt Package
  -> external LLM invocation interface
  -> model response text
  -> Abyss result import
```

External interfaces may only send prompts or Prompt Packages to an LLM model and return the model's response text to Abyss.

External interfaces must not be used for scheduling, triggering core workflows, notification delivery, file mutation, command execution, approval, rejection, audit, memory, policy decisions, state transitions, Git operations, Harness decisions, or self-evolution execution.
