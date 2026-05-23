# Abyss Roadmap

Abyss is a harness-first personal AI orchestration system. This roadmap separates two tracks:

1. **Feature iteration backlog** — user-visible capabilities that can be implemented as explicit slices.
2. **FSM-driven evolution loop** — low-frequency controlled self-evolution that may execute bounded implementation slices, but only through the Harness / HarnessAgent review path.

## Current baseline

Committed baseline: `d28e643 Add harness agent orchestration path`.

Available core path:

```text
Intent
  -> Prompt Package
  -> LLM/CLI Provider
  -> Result File
  -> Result Import
  -> Action Proposal
  -> Policy/Review
  -> Optional HarnessAgent Review
  -> Audit
```

Available components:

- CLI-first orchestration.
- Prompt Package generation.
- LLM Executor with provider abstraction.
- Harness policy gate.
- Review queue.
- Minimal FSM structural check.
- Harness snapshot export.
- Pluggable Agent registry.
- HarnessAgent review path.
- Local runtime audit records.

Non-goals for the current stage:

- No autonomous execution that bypasses Harness policy, HarnessAgent review, audit, and Git evidence.
- No automatic approval/rejection by agents.
- No direct mutation of user data without explicit review path.
- No hidden provider credentials in tracked files.

## Track A: Feature iteration backlog

### A1. Roadmap and evolution records

Goal: make system planning itself auditable.

Deliverables:

- `ROADMAP.md` as the human-readable plan.
- `.local/runtime/evolution/` for local evolution run records.
- A structured `EvolutionProposal` format for future capability suggestions.

Acceptance:

```powershell
python -m abyss_cli check
```

### A2. Event Source abstraction

Goal: unify future inputs without building one-off pipelines.

Target sources:

- Manual CLI intent.
- Obsidian note request.
- Remote IM inbox command.
- Chat log file.
- Web digest schedule.
- Git diff / project state event.
- UE log / build log event.

Canonical shape:

```yaml
schema: abyss.event.v1
id: evt_...
source_type: cli | note | remote_inbox | chatlog | web_digest | git | build_log
source_ref: string
created_at: iso8601
payload: object
status: received | normalized | ignored | converted | failed
```

Acceptance:

- One event can be normalized into one Intent.
- Ignored events are recorded with reason.
- No source can bypass Intent -> Prompt Package.

### A3. Note request scanner

Goal: connect Obsidian-style notes to the existing pipeline.

MVP behavior:

- Scan an inbox directory for Markdown notes with an explicit AI request marker.
- Convert each request into an Intent.
- Do not modify the source note in the first version.
- Write scan records under local runtime.

Suggested command:

```powershell
abyss note scan
```

Acceptance:

- A marked note produces an Intent.
- Duplicate scans do not duplicate Intents.
- The process stops at Prompt Package or Action Proposal, depending on chosen mode.

### A4. Remote IM Gateway MVP

Goal: allow remote control through a safe local inbox before integrating real IM callbacks.

MVP behavior:

- Poll `.local/runtime/remote_inbox.jsonl`.
- Support `/status`, `/run <task>`, `/review`, `/help`.
- `/run` creates an Intent and runs only to Action Proposal.
- Push summaries through the existing webhook script when available.
- Do not support `/approve` in MVP.

FSM states:

```text
received -> authenticated -> accepted -> queued -> running -> awaiting_review | done | failed
```

Acceptance:

- A synthetic remote inbox command triggers the local pipeline.
- Duplicate command ids are ignored.
- Result summary is recorded and notification attempted.

### A5. Chat log summarizer

Goal: summarize exported chat logs as an offline batch pipeline.

MVP behavior:

- Command: `abyss chatlog summarize <file>`.
- Input: `.txt` or `.md` only.
- Output: new Markdown summary file; never modify original log.
- Long logs are chunked.
- Summary includes: one-line summary, key issues, decisions, todos by owner, risks/blockers, user-attention items, noise.

Acceptance:

- One exported text file produces a structured summary.
- No automatic replies or forwarding.
- Completion notification is attempted for long runs.

### A6. Daily technical digest

Goal: periodically collect technical updates relevant to Unreal/TA/rendering/AI tooling.

MVP sources:

- Unreal Engine release notes/blog.
- NVIDIA developer blog.
- Rendering/SIGGRAPH-related feeds.
- GitHub trending or search for selected keywords.
- Hacker News or equivalent public feeds.

Output:

- Daily Markdown digest.
- Short webhook summary.
- Deduped source item log.

Harness boundary:

- Allowed: fetch public pages/RSS, summarize, write new digest file, notify.
- Forbidden: download unknown binaries, log into sensitive systems automatically, modify existing notes, send group messages as the user.

### A7. ReviewAgent

Goal: add a second specialized agent for code/doc quality review.

Role:

- Review diffs, generated docs, and proposed implementation slices.
- Find missing tests, schema drift, risky coupling, unclear acceptance criteria.
- Output review report only.

Forbidden:

- Modify files.
- Approve/reject reviews.
- Execute commands.

Acceptance:

```powershell
abyss agent run review --target latest
```

### A8. PlannerAgent

Goal: turn high-level goals into small implementation slices.

Role:

- Produce slice plans with files, commands, risk level, acceptance checks.
- Keep plans aligned with `SYSTEM_MAP.md`, `README.md`, and `ROADMAP.md`.

Forbidden:

- Execute the plan.
- Rewrite roadmap automatically.

### A9. Evolution dashboard / reports

Goal: make pending reviews, harness reviews, and evolution proposals easy to inspect.

MVP command ideas:

```powershell
abyss status --verbose
abyss evolution list
abyss evolution show latest
```

Acceptance:

- User can see current system health and pending proposals without reading runtime files manually.

## Track B: FSM-driven evolution loop

The FSM is allowed to evolve the system by executing bounded implementation slices. It is not merely a suggestion generator. However, every self-evolution run must remain inside the Abyss control path:

```text
Roadmap backlog / self-inspection
  -> select one bounded slice
  -> build implementation prompt/package or local task plan
  -> execute bounded code/doc changes
  -> run deterministic checks
  -> generate ActionProposal / change summary
  -> HarnessAgent review
  -> audit + Git evidence
  -> notify user
```

### Evolution selection policy

1. Prefer the user-authored roadmap backlog first.
2. Pick the first high-value slice that is small, testable, and not blocked.
3. If the backlog has no executable item, run self-inspection to discover a new suitable capability.
4. Convert discovered capabilities into `EvolutionProposal` records before implementation unless they are trivial documentation/check updates.
5. Execute at most one bounded slice per scheduled run.
6. Stop and notify the user if the slice requires credentials, broad refactors, destructive migration, production access, or ambiguous product judgment.

### Evolution principles

1. Observe only local, allowed state.
2. Prefer deterministic checks before LLM calls.
3. LLM/Agent may plan, review, and generate bounded implementation material, but must not bypass Harness.
4. Write every proposal, selected slice, check result, HarnessAgent review, and Git commit id as auditable local records.
5. Route implementation through normal test/check/Git workflow.
6. Notify the user on completion or failure when the run is long or scheduled.
7. Do not execute external side effects beyond the scoped repository workflow unless that capability is explicitly allowed by policy and reviewed.

### Mandatory gates for self-execution

A scheduled FSM evolution run may only complete an implementation if all gates pass:

1. **Scope gate** — selected work maps to one roadmap item or one recorded evolution proposal.
2. **Risk gate** — estimated risk is L0-L3. L4-L5 require explicit user intervention.
3. **Change gate** — changes are bounded to the Abyss system repository, unless the roadmap item explicitly targets a local runtime-only record.
4. **Check gate** — `python -m abyss_cli check` and relevant compile/tests pass.
5. **HarnessAgent gate** — generated proposal/change summary is reviewed by HarnessAgent.
6. **Git gate** — successful code/doc changes are committed with a focused message; push may occur only if the scheduled task policy explicitly allows pushing.
7. **Notify gate** — success/failure summary is sent to the user.

### Evolution check inputs

A scheduled evolution check may inspect:

- `README.md`
- `SYSTEM_MAP.md`
- `ROADMAP.md`
- `rules/*.yaml`
- `prompts/**/*.md`
- recent `.local/runtime/process/*` metadata
- recent audit records
- `git status --short`
- `python -m abyss_cli check` result

It must not inspect secrets, tokens, private keys, or unrelated personal files.

### Evolution proposal format

```yaml
schema: abyss.evolution_proposal.v1
id: evo_...
created_at: iso8601
trigger: scheduled | manual | after_failure | after_review
summary: string
observations:
  - string
proposed_capabilities:
  - id: string
    title: string
    why: string
    expected_value: low | medium | high
    risk_level: L0 | L1 | L2 | L3 | L4 | L5
    suggested_slice: string
    acceptance_checks:
      - string
selected_slice:
  roadmap_id: A2
  title: string
  execution_mode: propose_only | implement_bounded | needs_user_decision
  reason: string
blocked_by:
  - string
harness_agent_review:
  required: true
  status: pending | passed | warning | violation
recommendation: defer | plan | implement_next | implemented | needs_user_decision
no_unreviewed_external_side_effects: true
```

### Suggested scheduled cadence

Default cadence should be low frequency:

- Daily or every few days for evolution proposal generation.
- Never more frequent than hourly.
- Prefer daytime local time.

Recommended prompt for scheduled run:

```text
Run an Abyss controlled evolution cycle. Prefer the next executable item from ROADMAP.md. If no roadmap item is executable, inspect the system for one suitable evolution capability and record it as an EvolutionProposal. Execute at most one bounded slice only if it passes scope/risk/check/HarnessAgent gates. Do not perform destructive actions, credential work, broad refactors, production access, or unreviewed external side effects. Commit focused successful repository changes if allowed by the scheduled task policy. Use the notify mechanism to proactively inform the user of success or exception.
```

## Near-term priority order

1. A1 Roadmap and evolution records.
2. A2 Event Source abstraction.
3. A3 Note request scanner.
4. A4 Remote IM Gateway MVP.
5. A5 Chat log summarizer.
6. A6 Daily technical digest.
7. A7 ReviewAgent.
8. A8 PlannerAgent.
9. A9 Evolution dashboard.

## Immediate next slice recommendation

The next implementation slice should be **A2 Event Source abstraction**, because it prevents note scanning, remote IM commands, chat logs, web digests, and build logs from becoming separate incompatible pipelines.

Minimum slice:

- Add `abyss_cli/event_source.py`.
- Add local runtime directory `.local/runtime/events/`.
- Add `abyss event import --type manual --payload <file>` or equivalent.
- Convert one event into one Intent.
- Add docs and `python -m abyss_cli check` coverage.

