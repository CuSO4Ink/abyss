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

Current active/current-reading window: R070-R091.

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

### R079A. Meta-governance workflow closure for governance-core and meta-evolution requests

Source approval: current owner conversation.

Purpose: Close the dedicated meta-governance path for changes to governance-core surfaces and self-evolution mechanisms.

Why it is needed: Self-iteration must not approve, apply, or activate structural changes to itself. Abyss already has governance_mutation and meta_evolution_request semantics, governance-core detection, recommended meta_governance routing, and delayed-activation rules; this item turns those rules into a minimal review packet flow. Scope: add a read-only/request-recording meta-governance packet builder and CLI wiring that consumes Request Envelope records, validates prior-rule review requirements, surfaces required Owner/Harness/rollback/validation/delayed-activation checks, and refuses to grant execution or approval authority. Non-goals: no same-cycle activation, no automatic approval, no executor apply, no policy relaxation, no ordinary self-evolution bypass, no Brain or external model authority expansion.

Minimal implementation slice:

- Add a meta-governance packet builder for governance_mutation and meta_evolution_request envelopes.
- Expose a request meta-packet command that can render JSON and optionally persist the review packet.
- Include prior accepted rule sources, missing meta requirements, forbidden closures, and delayed activation status.
- Keep the packet as candidate review material only.

Expected user-visible result: governance-core/self-evolution structural change requests can be turned into explicit review packets instead of being mistaken for ordinary self-evolution work.

Risk level: L3 governance-core-adjacent.

Acceptance check:

- Packet generation performs no execution, no approval, no file mutation other than optional packet persistence, and no activation.
- Missing old-rule review, rollback plan, validation plan, explicit Owner approval, or delayed activation policy are reported.
- governance_mutation and meta_evolution_request requests remain outside ordinary self-evolution closure.
- compileall, abyss check, request type listing, governance-core detection, and packet generation smoke pass.

### R080. Context Broker V1 evidence-driven target discovery

Source approval: current owner conversation.

Purpose: Replace fragile keyword-rule context selection with evidence-driven target discovery.

Why it is needed: The current Context Broker remains vulnerable to missing or wrong implementation context because it relies heavily on deterministic keyword/task-type logic. This causes downstream agents to generate incorrect ChangeSets. Goal: move from keyword rules to evidence-driven target discovery. Scope: design and implement a bounded Context Broker V1 that discovers likely files/symbols through request envelope evidence, repository search, manifests, imports/dependency adjacency, and sufficiency checks while preserving governance and disclosure boundaries.

Minimal implementation slice:

- Add target discovery evidence records before context pack construction.
- Use exact file/symbol/request evidence before falling back to task-type keyword matching.
- Emit context sufficiency and ambiguity diagnostics.
- Preserve existing disclosure policy and approval boundaries unless separately routed through meta-governance.

Expected user-visible result: Implementation Agent receives the right target context more often, reducing incorrect ChangeSet generation.

Risk level: L3.

Acceptance check:

- Existing context behavior remains compatible for known task categories.
- Target discovery emits evidence and uncertainty instead of silent keyword-only selection.
- No disclosure expansion occurs without explicit governance approval.
- Context-insufficient cases block or request more evidence rather than producing low-confidence edit context.

Implementation evidence:

- Added Context Broker V1 target discovery evidence using explicit paths, path mentions, filename/module mentions, symbol export matches, and import adjacency.
- Context packs now include target_discovery and context_sufficiency diagnostics.
- Implementation prompts now expose target discovery evidence and warn agents to request local_edit_context instead of guessing when confidence is low or ambiguous.

### R081. Implementation edit-plan contract hardening


Source approval: current owner conversation.

Purpose: Reduce invalid Implementation Agent edit-plan output.

Why it is needed: Historical invalid ChangeSets include 31 output-contract issues where agent output could not be applied as a valid edit plan. Goal: significantly reduce the probability that the Agent outputs an unappliable edit plan.

Minimal implementation slice:

- Strengthen edit-plan schema and prompt contract checks.
- Add stricter import-time validation for operations, anchors, old_content/new_content, and target paths.
- Provide precise format feedback for retry without granting execution authority.
- Preserve existing ChangeSet/Harness/Owner boundaries.

Expected user-visible result: Implementation Agent outputs conform to the expected ChangeSet/edit-plan contract more reliably.

Risk level: L2.

Acceptance check:

- Invalid format cases are classified as output-contract issues with actionable retry guidance.
- Valid existing ChangeSets continue to import and dry-run.
- No automatic apply or approval is introduced.

Implementation evidence:

- Added preflight_validate_edit_plan_contract for required edit kind, target.path, symbol, anchor, new_content, and content fields.
- Contract failures are classified before target resolution to keep output-contract feedback separate from context failures.
- Prompt grounding now states the stricter abyss-edit-plan contract and forbids abbreviated placeholder code.

### R082. ChangeSet preflight and auto-recovery


Source approval: current owner conversation.

Purpose: Reduce target-resolution failures through preflight checks and bounded context recovery.

Why it is needed: Historical invalid ChangeSets include 17 target-resolution issues where anchor, old_content, or symbol resolution failed. Goal: after anchor/old_content/symbol failure, automatically supplement local context and retry within bounded limits.

Minimal implementation slice:

- Add preflight checks for target path, anchor uniqueness, old_content match, and symbol presence.
- Generate local context recovery packets when target resolution fails.
- Allow bounded retry with supplemented evidence, without expanding scope silently.
- Record recovery classification and outcome.

Expected user-visible result: Recoverable ChangeSet target-resolution failures produce better follow-up context instead of requiring manual repair in most cases.

Risk level: L3.

Acceptance check:

- Preflight detects target-resolution failures before execution.
- Recovery packets include precise evidence and retry limits.
- Auto-recovery never bypasses dry-run, Harness review, Owner approval, or executor boundaries.

Implementation evidence:

- ChangeSet dry-run now includes a structured abyss.changeset_preflight.v1 report.
- Invalid edit-plan target-resolution failures can include an abyss.context_recovery_packet.v1 with local context preview and retry_limit=1.
- Recovery remains candidate retry context only and does not apply, approve, or bypass Harness/Owner boundaries.

### R083. Self-iteration reliability metrics


Source approval: current owner conversation.

Purpose: Quantify whether the self-iteration process is becoming more reliable.

Why it is needed: Abyss needs operational metrics rather than anecdotal confidence. Metrics should expose first-pass success, invalid ChangeSet rate, provider empty rate, manual correction rate, and context recovery success rate.

Minimal implementation slice:

- Add read-only metrics aggregation from workflow, ChangeSet, provider, and recovery records.
- Report first_pass_success_rate, invalid_changeset_rate, provider_empty_rate, manual_correction_rate, and context_recovery_success_rate.
- Integrate compact summaries into insight/current views without creating active gates prematurely.

Expected user-visible result: The operator can see whether self-iteration reliability is improving or regressing.

Risk level: L2.

Acceptance check:

- Metrics are read-only and derived from existing records where possible.
- Missing data is reported explicitly instead of guessed.
- No workflow state changes or approvals are performed.

Implementation evidence:

- Added abyss_cli/self_iteration_metrics.py with first_pass_success_rate, invalid_changeset_rate, provider_empty_rate, manual_correction_rate, and context_recovery_success_rate.
- Added python -m abyss_cli reliability metrics --json.
- Summary, insight, and roadmap current views expose the metrics as read-only observations.
- Stability pass added all_time, recent_20, and recent_50 metric windows so post-hardening behavior can be compared against historical baselines without creating gates.
- Stability pass added a read-only schema registry view for runtime-only and rules-backed contracts so metric/insight schemas are visible before externalization.

### R084. Failure-to-probe feedback loop



Source approval: current owner conversation.

Purpose: Turn failures into repeatable tests or probes.

Why it is needed: Repeated self-iteration failures should not remain only as audit history; each meaningful failure should produce a candidate probe/test so future changes can demonstrate improvement.

Minimal implementation slice:

- Classify failure records that are suitable for probes.
- Generate candidate probe specs from invalid ChangeSet, provider, context, and workflow failures.
- Keep generated probes as candidate material until approved or explicitly selected.
- Link probes back to source failures and reliability metrics.

Expected user-visible result: Each meaningful failure can become a repeatable regression signal instead of being manually rediscovered.

Risk level: L2.

Acceptance check:

- Probe generation is read-only/candidate by default.
- Probe specs preserve source failure evidence.
- No test is activated as a required gate without explicit approval.

Implementation evidence:

- Added abyss_cli/failure_probe.py to generate inactive failure probe candidates from invalid ChangeSets and failed/blocked workflows.
- Added python -m abyss_cli reliability probe-candidates --json.
- Summary, insight, and roadmap current views expose candidate counts/evidence while keeping probes inactive by default.
- Stability pass added abyss_cli/failure_taxonomy.py so summary, insight, Brain brief, and failure probes share one classification vocabulary.
- Stability pass added a read-only smoke fixture manifest so negative/boundary smoke artifacts remain clearly candidate-only and cannot be confused with runtime records or approvals.

### R085. Memory v0 Direction and Decision Records

Source proposal: `evo_prop_20260627_165537_8efd9c`.

Purpose: Memory v0 Direction and Decision Records

Why it is needed: Add abyss_cli/memory.py with record/list/show/project commands; store abyss.memory_record.v1 under .local/runtime/memory/records/; add contract+schema; project to Obsidian user_data note with provenance frontmatter; lightweight integrity check. Non-goals: no storage auto promote/demote, no vector search, no LLM, no policy/governance/prompt/ROADMAP changes, no agent write authority. Risk L2. Purpose: first runnable knowledge-precipitation mechanism, the food for Brain v1 direction alignment.

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

### R086. Brain v1 read the direction layer (deterministic, no LLM)

Source proposal: `evo_prop_20260627_171809_bb9da3`.

Purpose: Brain v1 read the direction layer (deterministic, no LLM)

Why it is needed: Extend abyss_cli/brain.py so the read-only Brain brief ALSO reads abyss.memory_record.v1 records from .local/runtime/memory/records/ and emits a deterministic direction-alignment view: list recent directions/decisions, group by kind, and surface a simple consistency note comparing recorded directions against recent system activity. Scope: brain.py read-side only, plus minimal __main__ wiring if needed. NON-GOALS: no LLM calls, no enabling the brain agent provider, no agents.yaml enabled/role_prompt change, no approval/execute/mutate/schedule authority, no policy/governance/prompt/ROADMAP changes, no Memory schema change. Brain stays read-only candidate cognition. Risk L2. Purpose: give the Memory layer its first reader so today's direction records produce value, before any LLM semantic alignment (which is a later separate proposal).

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

### R087. Register FSM module capsule in modules.yaml

Source proposal: `evo_prop_20260627_193027_da32f2`.

Purpose: Register FSM module capsule in modules.yaml

Why it is needed: Add a 'fsm' entry to rules/modules.yaml describing the existing abyss_cli/fsm.py. The FSM module manages a periodic integrity-check state machine (unknown/idle/checking/needs_attention) with tick and watch commands. Capsule will declare: files=[abyss_cli/fsm.py], responsibility=[run periodic integrity ticks, transition FSM states, record tick history], inputs=[integrity check result, .local/runtime/fsm/state.yaml], outputs=[abyss.fsm_tick.v1, abyss.fsm_state.v1], permissions=[read_integrity, write_fsm_state, write_fsm_ticks, append_audit], dependencies=[integrity, audit], risk_level=low, validation=[python -m abyss_cli fsm tick, python -m abyss_cli check], failure_modes=[stale state, missed integrity regression], observability=[.local/runtime/fsm/ticks/, .local/runtime/fsm/state.yaml, audit events], runtime_records=[.local/runtime/fsm/ticks/*.yaml], allowed_callers=[human_owner, local_cli], forbidden_actions=[execute_action, approve_changeset, modify_files, run_commands, bypass_harness], invariants=[FSM transitions must follow FSM_TRANSITIONS table, tick must call integrity check, state must persist to state.yaml]. NON-GOALS: no new code in fsm.py, no new CLI commands, no FSM behavior change, no agents.yaml change, no policy/governance/ROADMAP change. Pure capsule registration of existing code. Risk L2. Purpose: bring the FSM module into the formal capsule map so cognition layer fully recognizes it.

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

### R088. Batch register infrastructure module capsules in modules.yaml

Source approval: current owner conversation.

Purpose: Batch register all remaining unregistered abyss_cli/*.py modules as capsules in modules.yaml.

Why it is needed: After R087 registered the FSM capsule, 26 infrastructure modules still had no capsule entries in modules.yaml. These modules are already implemented and functional but invisible to the cognition layer. This item registers all of them in a single batch so the capsule map achieves full coverage of abyss_cli/*.py files. Capsules added: audit, data_sync, direct_auth, fenced_blocks, harness, intent, policy, result, review, utils, failure_probe, failure_taxonomy, git_checkpoint, health, insight, meta_governance, patch_compiler, prompt_builder, provider_reliability, request_envelope, request_rules, roadmap_current, rule_registry, schema_registry, self_iteration_metrics, smoke_fixtures. Each capsule declares all 13 required fields based on actual source code analysis. NON-GOALS: no new code, no CLI commands, no behavior change, no agents.yaml change, no policy/governance change. Pure capsule registration of existing code. Risk L2. Purpose: bring the entire abyss_cli module set into the formal capsule map so Context Broker, Brain, and future agents can discover and understand all modules.

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

Implementation evidence:

- modules.yaml capsule count increased from 17 to 43.
- All 45 abyss_cli/*.py files now have capsule coverage (2 shared capsules cover multiple files).
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli summary --check passes.

### R089. R089 Skill v0 read-only skill registry

Source proposal: `evo_prop_20260627_200800_skill_v0`.

Purpose: R089 Skill v0 read-only skill registry

Why it is needed: Skill infrastructure was the last completely blank module among the five foundational architectures (the others being Memory, Brain, FSM, and external executor). This item adds a minimal read-only skill registry that declares existing capabilities as named skills without granting execution authority. The registry follows the established v0 pattern: declare first, read first, execute later (with a future roadmap item).

Scope: add abyss_cli/skill.py and rules/skills.yaml, wire CLI subcommands (skill list/show/check) in abyss_cli/__main__.py, register skill_registry capsule in rules/modules.yaml, register skill_registry_rules in rules/rule_sources.v1.yaml, add skill check to ALLOWED_VALIDATION_COMMANDS. Pre-register 4 skills: health_check, memory_record, git_checkpoint, integrity_check — each mapped to an existing read-only command.

Minimal implementation slice:

- rules/skills.yaml: abyss.skill_registry.v1 schema with v0_constraints (read_only, no_execution, no_llm_calls, no_file_mutation, no_workflow_transitions)
- abyss_cli/skill.py: list_skills, show_skill, check_skill_registry functions
- CLI: abyss skill list [--json], abyss skill show <name>, abyss skill check
- modules.yaml: skill_registry capsule (files, responsibilities, forbidden_actions, invariants)
- rule_sources.v1.yaml: skill_registry_rules entry

Expected user-visible result: User can list, inspect, and validate declared skills via CLI. All skills are read-only declarations mapped to existing commands. No skill is executed.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- No external interface is used for anything other than standard LLM invocation.
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli skill list/check/show all work.
- python -m abyss_cli rules validate passes.

Implementation evidence:

- rules/skills.yaml created with abyss.skill_registry.v1 schema and 4 pre-registered skills.
- abyss_cli/skill.py implemented with list/show/check functions.
- CLI subcommands registered in abyss_cli/__main__.py.
- modules.yaml capsule count increased from 43 to 44.
- rule_sources.v1.yaml entry count increased from 9 to 10.
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli skill check passes.
- python -m abyss_cli rules validate passes.

### R090. External Outbox Pattern v0 — need declarations, capability cards, and BoxAI fulfillment flow

Source proposal: inline discussion (Owner-directed architecture design).

Purpose: Establish the Outbox Pattern as Abyss's external platform interaction model. Abyss writes passive need declarations to a local outbox; external platforms (starting with BoxAI) poll, read, fulfill, and write back fulfillment records. Abyss never makes outbound calls.

Why it is needed: The five foundational architectures (Memory, Brain, FSM, Skill, External Executor) were all in place except the external executor. The core challenge was that Abyss cannot directly invoke external platforms (zero external dependency principle), and BoxAI has no inbound endpoint for Abyss to call. The Outbox Pattern resolves this: Abyss declares needs locally, platforms fulfill at their discretion. The need_type namespace uses dotted open strings (like MIME types) with bidirectional prefix matching, enabling progressive generalization to future platforms without schema changes.

Scope: add rules/schemas/external_need.v1.schema.json (need envelope schema), rewrite rules/external_adapters.yaml as Outbox Pattern registry (need templates, capability cards, transport contract), add abyss_cli/external_adapter.py (write needs, read fulfillments, list/show/check), wire CLI subcommands (adapter list/show/platforms/platform/write-need/needs/need/fulfillment/check), register external_adapter capsule in rules/modules.yaml, register external_adapter_rules in rules/rule_sources.v1.yaml, add adapter check to ALLOWED_VALIDATION_COMMANDS.

Minimal implementation slice:

- rules/schemas/external_need.v1.schema.json: abyss.external_need.v1 envelope (id, type as open dotted string, version, payload, lifecycle with status/created_at/fulfilled_at/fulfilled_by/error)
- rules/external_adapters.yaml: abyss.external_need_registry.v1 — need_type_namespace with matching_rule, lifecycle_states, outbox_transport (v0=file_outbox), 4 need_templates (notify/notify/execute.git.commit/store.kb.box), 1 capability_card (boxai with 8 supported_types), hard_boundaries
- abyss_cli/external_adapter.py: write_need(), list_needs(), show_need(), list_pending_needs(), read_fulfillment(), check_registry(), check_outbox(), plus registry list/show for templates and platforms
- CLI: abyss adapter list/show/platforms/platform/write-need/needs/need/fulfillment/check
- modules.yaml: external_adapter capsule (45 total, +skill_registry from R089 = 45)
- rule_sources.v1.yaml: external_adapter_rules entry (11 total)
- rule_registry.py: adapter check added to ALLOWED_VALIDATION_COMMANDS

Expected user-visible result: User can write external needs to the outbox via CLI, list pending needs, and read fulfillment records written by BoxAI. The full flow works: Abyss writes need -> BoxAI reads pending -> BoxAI fulfills -> Abyss reads fulfillment. Registry and outbox consistency is validated by adapter check.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- No external interface is used for anything other than standard LLM invocation.
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli adapter check passes.
- python -m abyss_cli adapter list/platforms work.
- python -m abyss_cli adapter write-need/needs/need/fulfillment flow works end-to-end.
- python -m abyss_cli rules validate passes.

Implementation evidence:

- rules/schemas/external_need.v1.schema.json created with abyss.external_need.v1 schema.
- rules/external_adapters.yaml rewritten as abyss.external_need_registry.v1 with 4 need templates and 1 capability card (boxai).
- abyss_cli/external_adapter.py implemented with write/read/check functions.
- CLI subcommands registered in abyss_cli/__main__.py.
- modules.yaml capsule count increased from 43 to 45 (skill_registry + external_adapter).
- rule_sources.v1.yaml entry count increased from 10 to 11.
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli adapter check passes.
- Full outbox flow tested: need written -> fulfillment written -> fulfillment read successfully.
- python -m abyss_cli rules validate passes (11 entries, ok=true).




### R091. Brain Agent v1 Internal Coordinator — system understanding, outbox driving, integration, and proposal drafting

Source proposal: inline discussion (Owner-directed architecture upgrade).

Purpose: Upgrade Brain Agent from v0 (disabled, read-only brief) to v1 (enabled, internal coordinator). Brain Agent v1 builds system understanding, evaluates trigger conditions to drive the Outbox Pattern, integrates external fulfillment results, and drafts candidate evolution proposals for Owner approval. Brain becomes the internal PM/coordinator bridging system state, external platforms, and Owner decisions.

Why it is needed: R090 established the Outbox Pattern pipe but no one was driving it. Brain Agent v0 was disabled and purely a read-only brief renderer. The system needs an internal coordinator that can detect conditions requiring external action, write needs to the outbox, read fulfillment results, and surface candidate proposals — all without execution, approval, or outbound calls. This bridges the gap between system awareness and external collaboration.

Scope: upgrade abyss_cli/brain.py with 4 coordinator functions (build_brain_context, brain_tick, brain_intake, brain_propose), create prompts/agents/brain_agent.md, update rules/agents.yaml (enabled=true, role_prompt, v1 permissions/forbidden), update rules/modules.yaml brain capsule (L2 risk, new responsibilities/outputs/dependencies), update abyss_cli/integrity.py brain check (remove disabled requirement, add role_prompt + outbound_calls + treat_suggestions forbidden checks), wire CLI subcommands (brain context/tick/intake/propose) in abyss_cli/__main__.py.

Minimal implementation slice:

- brain.py: build_brain_context() aggregates integrity/summary/memory/outbox/roadmap into abyss.brain_context.v1; _evaluate_triggers() matches registry templates against system state; brain_tick() writes needs when triggers fire (dedup by type); brain_intake() reads fulfilled needs and produces integration view with recommendations; brain_propose() drafts candidate evolution proposal for Owner
- prompts/agents/brain_agent.md: v1 coordinator role prompt with mission, allowed/forbidden lists, workflow steps
- agents.yaml: brain enabled=true, role=brain_agent_v1_internal_coordinator, role_prompt set, allowed includes write_outbox_needs/read_outbox_fulfillments/draft_evolution_proposal, forbidden includes make_outbound_calls/treat_suggestions_as_approved_tasks
- modules.yaml: brain capsule updated with v1 responsibilities, L2 risk, new inputs (outbox/roadmap), outputs (5 schemas), dependencies (external_adapter/roadmap_current/audit), audit events observability
- integrity.py: brain check updated from "must be disabled" to "enabled must be bool + role_prompt required + expanded forbidden list"
- __main__.py: brain context/tick/intake/propose subcommands registered

Expected user-visible result: User can run `abyss brain context` to see a system-understanding snapshot, `abyss brain tick` to evaluate triggers and write needs, `abyss brain intake` to read fulfilled needs, and `abyss brain propose` to draft a candidate evolution proposal. Brain Agent is enabled as an internal coordinator with bounded write authority (outbox needs only). The v0 `brain brief` command remains backward compatible.

Risk level: L2.

Acceptance check:

- The request remains non-executable until explicit user approval.
- No external interface is used for anything other than standard LLM invocation.
- python -m abyss_cli check passes.
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli brain brief/context/tick/intake/propose all work.
- python -m abyss_cli rules validate passes.
- End-to-end: write need -> brain intake reads pending -> write fulfillment -> brain intake reads fulfilled with recommendations.
- Brain propose detects fulfilled items and drafts candidate proposal.

Implementation evidence:

- abyss_cli/brain.py upgraded with 4 v1 coordinator functions.
- prompts/agents/brain_agent.md created with v1 coordinator role definition.
- rules/agents.yaml brain entry updated: enabled=true, role_prompt set, v1 permissions/forbidden.
- rules/modules.yaml brain capsule updated: L2 risk, 7 responsibilities, 6 outputs, 8 dependencies.
- abyss_cli/integrity.py brain check updated: enabled-must-be-bool + role_prompt + expanded forbidden.
- abyss_cli/__main__.py: 4 new brain subcommands registered.
- python -m abyss_cli check passes (OK).
- python -m compileall -q abyss_cli passes.
- python -m abyss_cli brain brief/context/tick/intake/propose all produce valid output.
- End-to-end verified: test need -> intake reads pending -> fulfillment -> intake reads fulfilled with recommendations -> propose detects fulfilled item.
- python -m abyss_cli rules validate passes (11 entries, ok=true).


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
