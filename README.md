# Abyss

Harness-first personal AI orchestration workspace.

For system cognition, global rules, Brain Agent direction, and progressive disclosure order, read `ABYSS.md` first.

This README focuses on installation, commands, and operational usage.

Abyss MVP is a local, CLI-first orchestration layer. It turns user intent into structured Prompt Packages, routes outputs through a deterministic Harness, and records an auditable trail before anything becomes an action.

## MVP scope

This MVP intentionally does **not** implement a full chat UI, background agent, automatic action executor, or automatic external side effects.

It focuses on:

1. Intent creation
2. Prompt Package generation
3. Manual Client Executor workflow
4. Optional LLM Executor provider workflow
5. LLM result import
6. Action Proposal parsing
7. Harness policy decisions
8. Review queue
9. Audit trail
10. Integrity checks

## Design principles

Abyss is guided by five system-level design principles:

1. Progressive disclosure
2. High information density
3. Low cognitive load
4. Modular decoupling
5. Extensibility first

The canonical structured rules live in `rules/design_principles.yaml`; the highest-level commitments live in `ABYSS_CONSTITUTION.md`.

## Minimum disclosure and contracts

Abyss cognition starts from `ABYSS.md`, then moves through constitution, system brief, direction documents, `SYSTEM_MAP.md`, module capsules in `rules/modules.yaml`, and contracts in `rules/contracts/` before source code. Source files under `abyss_cli/` are implementation evidence, not the default entrypoint.

`rules/modules.yaml` is the module capsule manifest. `rules/contracts/` contains machine-readable contracts for structured records such as `abyss.change_set.v1`, `abyss.context_request.v1`, `abyss.blocked_result.v1`, `abyss.harness_review.v1`, `abyss.evolution_analysis.v1`, `abyss.context_pack.v1`, `abyss.external_work_feedback_card.v1`, and `abyss.request_envelope.v1`.

`rules/request_types.v1.yaml` is the canonical V0 request semantics source. `request_id` tracks identity only; `request_type` is the authoritative semantic field for parsing, routing, validation, context selection, and governance behavior.

`python -m abyss_cli check` validates key cognition-layer expectations: required entry files, contract presence, JSON Schema presence, request type semantics, module capsule fields, context manifest references, disclosure audit warnings, Brain Agent v0 read-only boundaries, and runtime noise exclusions.

Read-only cognition commands:

```powershell
python -m abyss_cli brain brief
python -m abyss_cli brain brief --json
python -m abyss_cli disclosure audit
python -m abyss_cli disclosure audit --json
```

These commands explain state and disclosure boundaries only. They do not execute work, approve changes, modify files, schedule tasks, or replace Owner/Harness authority.

## Layered data architecture

Abyss separates information into three layers:

1. **User data layer** — the default user-facing knowledge surface, primarily aligned with active Obsidian notes, current directions, working summaries, and decision records.
2. **Implementation layer** — the hidden-by-default system internals: code, prompts, rules, harness logic, process records, audit, schemas, and executors.
3. **Data storage layer** — the hidden-by-default archive for inactive, dormant, bulky, historical, or not-currently-useful material.

The implementation layer and data storage layer should not appear in the user's default information retrieval scope. When archived material becomes relevant, Abyss should retrieve a focused subset from storage and promote or materialize it into the user data layer with provenance, rather than exposing storage directly.

The user data layer is **Obsidian-first**. Use Markdown notes, YAML frontmatter, Obsidian wiki links like `[[Project Name]]`, relative attachments under `_attachments/`, and `Home.md` as the human entry point for active areas.

The canonical structured rules live in `rules/data_layers.yaml`.

## Multi-device sync

Abyss uses a separated single-user GitHub sync model:

1. **System repository** — this repository. It contains Abyss implementation, rules, prompts, process structure, and architecture documentation.
2. **GitHub private data repository** — `CuSO4Ink/abyss-data`. It contains the real `user_data/` and `storage/archive/` content used across devices.

This keeps the system implementation safe to sync or publish without mixing in personal Obsidian notes or archives.

After creating the GitHub private repository, configure it once per device:

```powershell
abyss data init
```

By default this uses:

```text
git@github-personal:CuSO4Ink/abyss-data.git
```

Optional custom local path:

```powershell
abyss data init --path C:\Users\violinapeng\Documents\abyss-data
```

Daily sync commands:

```powershell
abyss data status
abyss data pull
abyss data push -m "update active notes"
```

The local sync configuration is stored in `.local/data_sync.json`, which is ignored by Git and must not contain tokens, passwords, or private keys.

The canonical structured rules live in `rules/sync.yaml`.

## Memory v0: direction and decision records

Approved roadmap item `R085` adds the first runnable knowledge-precipitation mechanism. It records Owner direction choices and key decisions as structured candidate knowledge and can project a record into an Obsidian-friendly note.

```powershell
abyss memory record --kind direction --title "..." --body "..." --related "R085" --tags "direction,governance"
abyss memory list
abyss memory list --kind decision --json
abyss memory show latest
abyss memory project latest
```

Records are stored as `abyss.memory_record.v1` under `.local/runtime/memory/records/`. The `project` command writes a single Obsidian note under `user_data/memory/` with provenance frontmatter.

V0 boundaries:

```text
Memory records are candidate knowledge written explicitly by the Owner.
Creating a record approves nothing, executes nothing, and triggers no workflow transition.
The project command is a read-only projection, NOT the storage->user_data promotion mechanism.
The v0 schema is intentionally minimal; new fields require an explicit contract revision before Brain v1 depends on them.
No LLM calls, no policy/governance/prompt/ROADMAP changes, no agent write authority.
```

## Quick start

Install once in editable mode so Abyss can be run from any directory:

```powershell
python -m pip install -e C:\Users\violinapeng\Documents\abyss
```

Then run either style from any directory:

```powershell
abyss status
python -m abyss_cli status
```

From this repository root, direct module execution also works without installation:

```powershell
python -m abyss_cli intent new "总结当前 git diff，生成组内同步说明"
python -m abyss_cli prompt build latest --copy
python -m abyss_cli check
```

## Request semantics V0

Abyss has a canonical Request Envelope layer for making request semantics explicit before context selection or governance routing:

```powershell
python -m abyss_cli request types
python -m abyss_cli request types --all
python -m abyss_cli request normalize --type maintenance_request --title "Refactor integrity checks" --field target_module=abyss_cli/integrity.py --field maintenance_kind=refactor
python -m abyss_cli request validate path\to\request_envelope.json
```

V0 boundaries:

```text
Request normalization grants no execution authority.
Request normalization grants no approval authority.
Automatic natural-language classification is not authoritative in V0.
Mutation requests still require proposal, workflow, ChangeSet, dry-run, Harness review, Owner approval, executor apply, and check.
```

## Rule Source Registry V0

Abyss has a lightweight rule source registry for declaring where accepted rule sources live and which consumers should include them in later context or validation paths:

```powershell
python -m abyss_cli rules list --json
python -m abyss_cli rules validate --json
```

V0 boundaries:

```text
The registry is declarative and discoverable only.
It grants no execution authority and no approval authority.
It is not an event bus, daemon, hot-reload system, broad rule engine, or automatic propagation authority.
Context Broker may include declared rule source files for matching task types, and integrity checks fail on a missing or malformed registry.
```

## Manual LLM loop

1. Create an intent.
2. Build a prompt package.
3. Paste the generated prompt into Knot / Claude / ChatGPT / Cursor.
4. Save the LLM response to a local markdown file.
5. Import it:

```powershell
python -m abyss_cli result import path\to\response.md --intent latest
```

If the response contains action proposals, Abyss parses them into `process/actions/` and runs the Harness policy gate.

## External model collaboration package

For scoped external model/developer collaboration, build a governed cognition-first task package:

```powershell
python -m abyss_cli prompt build-external "<task objective>" --details "<constraints or acceptance criteria>"
```

This package uses the Context Broker and `rules/architecture_cognition.yaml` to include Abyss cognition, governance boundaries, module capsules, and external collaboration protocol before source code. External model output remains candidate material only; it cannot approve, execute, mutate files, or bypass workflow, Harness, Owner, or executor boundaries.

After saving an external model response, import it as a candidate feedback card:

```powershell
python -m abyss_cli external import-result path\to\external_response.md --task-id <prompt-package-id> --source-platform <platform>
```

The feedback card is an intake artifact only. It does not create proposals, approve work, apply changes, or change workflow state.

## Autonomous workflow bootstrap

Abyss can run an approved evolution proposal through the native self-iteration workflow without an external assistant manually chaining internal commands:

```powershell
abyss workflow start <approved-proposal-id> --provider cli
abyss workflow run
abyss owner inbox
abyss owner show <owner-item-id>
abyss owner approve <owner-item-id>
abyss report list
abyss report show latest
abyss summary --check
```

The workflow advances through ImplementationAgent ChangeSet generation, deterministic dry-run, HarnessAgent ChangeSet review, Owner Inbox approval, Local Executor apply, integrity check, audit, and workflow report generation. Agents still cannot approve or execute; the owner approval gate remains explicit. After this bootstrap, external assistants should interact through these user-facing commands instead of directly editing Abyss system files or manually chaining internal state transitions.

## Minimal FSM and scheduled structure checks

Abyss includes a minimal local FSM for periodic structural health checks:

```powershell
abyss fsm tick
abyss fsm watch --interval 300
abyss fsm watch --once
```

The FSM currently models only the local control loop:

```text
unknown/idle -> checking -> idle | needs_attention
```

Each tick runs the existing integrity checks, writes state under `.local/runtime/fsm/`, and appends an audit event. The watch command is intentionally simple: it is a foreground local loop, not a background daemon.

## Harness snapshot for LLMs

A safe, read-only subset of the Harness can be exported:

```powershell
abyss harness export
abyss harness export --format json
```

Prompt Packages now include this Harness snapshot automatically, so the LLM can see action proposal format, risk boundaries, safe path prefixes, and the rule that it must never claim actions were executed. The snapshot does not expose execution authority.

## Optional LLM Executor

Abyss also provides a thin LLM Executor layer for running a built Prompt Package through a standardized provider:

```powershell
abyss llm run latest --provider cli
abyss llm run <prompt-package> --provider cli
abyss llm run latest --provider api
```

This does not change the Intent / Prompt Package / Result Import flow. The executor always performs this sequence:

```text
Prompt Package -> provider stdout text -> saved result file -> existing import_result -> Action Proposal records
```

The executor stops at Action Proposal import. It never executes actions automatically.

Standard CLI provider interface:

```text
interface: stdin_prompt_package_stdout_response_v1
stdin:  complete Prompt Package text, UTF-8
stdout: complete LLM response text, UTF-8
stderr: diagnostics only; surfaced on failure
exit:   0 means success; non-zero means provider failure
model:  optional backend model name; when non-empty, Abyss appends [model_argument, model] to command
model_argument: optional CLI flag for model selection; defaults to --model
```

Standard HTTP JSON API provider interface:

```text
interface: http_json_prompt_package_response_v1
method:    POST
request:   { "schema": "abyss.llm_api_request.v1", "prompt_package": "...", "metadata": {...} }
response:  { "response": "complete LLM response body" }
```

OpenAI-compatible chat provider interface:

```text
interface: http_openai_chat_completion_v1
method:    POST
request:   { "model": "...", "messages": [{ "role": "user", "content": "complete Prompt Package" }], "stream": false }
response:  choices.0.message.content is imported as the complete LLM response body
notes:     choices.0.message.reasoning_content is diagnostics only and is not imported as executable response text
```

Provider defaults live in `rules/llm_providers.yaml`. Machine-local overrides live in `.local/llm_providers.json`, which is ignored by Git. Do not hardcode tokens, passwords, API keys, or private credentials in tracked files; use environment variables or local config controlled by the user.

Example local CLI provider config:

```json
{
  "providers": {
    "cli": {
      "enabled": true,
      "interface": "stdin_prompt_package_stdout_response_v1",
      "command": ["your-provider-adapter"],
      "model": "deepseek-v3.2",
      "model_argument": "--model",
      "timeout_seconds": 300
    }
  }
}
```

Example local API provider config:

```json
{
  "providers": {
    "api": {
      "enabled": true,
      "interface": "http_json_prompt_package_response_v1",
      "url": "https://example.local/llm",
      "headers": {
        "X-Client": "abyss"
      },
      "bearer_token_env": "ABYSS_LLM_API_TOKEN",
      "response_json_path": "response",
      "timeout_seconds": 300
    }
  }
}
```

Example local OpenAI-compatible chat provider config:

```json
{
  "providers": {
    "openai_chat": {
      "enabled": true,
      "interface": "http_openai_chat_completion_v1",
      "base_url": "https://api.deepseek.com",
      "endpoint": "/chat/completions",
      "model": "deepseek-chat",
      "bearer_token_env": "DEEPSEEK_API_KEY",
      "timeout_seconds": 300,
      "max_attempts": 2
    }
  }
}
```

On this Windows machine, `.local/knot_cli_provider.py` adapts the standard stdin/stdout interface to `knot-cli chat -p`.

## Governed self-iteration chain

Abyss includes a minimal governed self-iteration intake path. It records user change requests separately from approved roadmap items, so raw conversation does not automatically become executable work.

```powershell
abyss evolution request "建立规范自我迭代链路" --details "raw user request details"
abyss evolution list
abyss evolution show latest
abyss evolution propose latest
abyss evolution approve latest
abyss evolution reject latest --reason "not now"
abyss evolution status
abyss evolution finalize-direct-mode
abyss evolution smoke --provider cli
```

The smoke command uses the standard LLM provider interface only:

```text
Abyss Prompt / Prompt Package -> external LLM invocation interface -> model response text -> Abyss result record
```

It verifies that a real model can return text without producing action blocks or executing side effects.

`approve` is the only native command that promotes an evolution proposal into the approved roadmap. `reject` closes a proposal without implementation authority. `finalize-direct-mode` disables ordinary direct modification mode so future ordinary system changes must enter through request -> proposal -> approval -> roadmap.

## Pluggable Agent runner and HarnessAgent

Abyss supports a minimal pluggable Agent runner. Agents are configured in `rules/agents.yaml`, use role prompts under `prompts/agents/`, and must follow the same controlled path:

```text
Agent Prompt Package -> provider stdout text -> saved result file -> specialized runtime record -> audit
```

The first implemented agent is `harness`, a review-only HarnessAgent. It reviews action proposals, related LLM results, policy snapshots, and Harness snapshots for boundary violations or underestimated risk.

```powershell
abyss agent run harness --target latest
abyss harness review latest
```

HarnessAgent is not an executor. It cannot approve, reject, modify files, change policy, change prompts, send messages, or execute actions. It writes `abyss.harness_review.v1` records under `.local/runtime/process/harness_reviews/` and always preserves the `no_action_executed` boundary.

Abyss also declares a `self_evolution` Agent for planning-only self-iteration analysis:

```powershell
abyss agent run self_evolution --target latest
```

The self-evolution Agent may analyze evolution requests and propose bounded plans. It cannot approve roadmap items, modify files, run commands, schedule work, send messages, or operate Git. Its `abyss-evolution-analysis` output is parsed into `.local/runtime/process/evolution_analyses/` and schema-contract warnings are recorded instead of being treated as authority.

R003 adds an `implementation` Agent that generates proposed ChangeSets only:

```powershell
abyss agent run implementation --target latest
```

ImplementationAgent uses the same Agent Prompt Package -> provider stdout -> result file path. Its `abyss-changeset` output is parsed into `.local/runtime/process/changesets/` as `abyss.change_set.v1`. It cannot approve, reject, apply, modify files directly, run commands, or operate Git.

## Governed OperationSet / ChangeSet MVP

Approved roadmap item `R003` introduces a minimal native ChangeSet path for governed local implementation. A ChangeSet is an operation-based `abyss.change_set.v1` record stored under `.local/runtime/process/changesets/` after import.

```powershell
abyss changeset import .\artifacts\drafts\example_changeset.json
abyss changeset list
abyss changeset show latest
abyss changeset dry-run latest
abyss harness changeset-review latest
abyss changeset approve latest
abyss changeset apply latest
```

The intended R003 flow is:

```text
approved roadmap target
  -> ImplementationAgent produces abyss.change_set.v1
  -> changeset import / deterministic validation
  -> HarnessAgent reviews the ChangeSet
  -> user explicitly approves the ChangeSet
  -> narrow local executor applies it
  -> execution record + integrity check + audit
```

The MVP executor is intentionally narrow. It only supports approved ChangeSets and these operation kinds:

- `fs.create_file`
- `fs.replace_exact`
- `fs.append_file`
- `check.command` with an allowlist of `python -m abyss_cli check` and `python -m compileall -q abyss_cli`

It blocks arbitrary shell commands, browser automation, service/port management, external writes, Git push, policy/prompt/governance modification, and direct ROADMAP modification. Agents still cannot execute ChangeSets; they may only propose records for review.

## Action proposal format

LLM responses may include fenced action proposals:

```yaml
```abyss-action
capability: fs.write
operation: create
path: artifacts/drafts/example.md
reason: Save a draft summary.
risk_estimate: L2
```
```

## Repository layout

```text
abyss/
├── ABYSS_CONSTITUTION.md
├── README.md
├── rules/
├── prompts/
├── process/
├── audit/
├── artifacts/
└── abyss_cli/
```

## Data format note

MVP structured records use `.yaml` filenames with JSON-compatible YAML content. This keeps the MVP dependency-free while preserving a future migration path to richer YAML.
