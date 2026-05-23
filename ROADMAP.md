# Abyss Roadmap

Abyss is a harness-first personal AI orchestration system. This roadmap separates two tracks:

1. **Feature iteration backlog** — user-visible capabilities that can be implemented as explicit slices.
2. **FSM-driven evolution loop** — low-frequency self-inspection that proposes system evolution, but never executes changes automatically.

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

- No autonomous execution of action proposals.
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

The FSM may propose system evolution, but it must not implement it automatically.

### Evolution principles

1. Observe only local, allowed state.
2. Prefer deterministic checks before LLM calls.
3. Use LLM/Agent only to produce proposals or reports.
4. Write every proposal as an auditable local record.
5. Route any implementation through normal review and Git workflow.
6. Notify the user on completion or failure when the run is long or scheduled.

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
blocked_by:
  - string
recommendation: defer | plan | implement_next | needs_user_decision
no_action_executed: true
```

### Suggested scheduled cadence

Default cadence should be low frequency:

- Daily or every few days for evolution proposal generation.
- Never more frequent than hourly.
- Prefer daytime local time.

Recommended prompt for scheduled run:

```text
Run an Abyss evolution check. Inspect the current repository state and recent local runtime metadata. Produce a concise evolution proposal list only. Do not modify code. Do not execute actions. Use the notify mechanism to proactively inform the user of success or exception.
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

