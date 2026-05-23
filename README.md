# Abyss

Harness-first personal AI orchestration workspace.

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
```

Standard HTTP JSON API provider interface:

```text
interface: http_json_prompt_package_response_v1
method:    POST
request:   { "schema": "abyss.llm_api_request.v1", "prompt_package": "...", "metadata": {...} }
response:  { "response": "complete LLM response body" }
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
