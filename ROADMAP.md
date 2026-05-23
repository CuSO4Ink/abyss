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

### A0. P0: Native Evolution Runner and external-client decoupling

Goal: remove any dependency on external LLM/Knot/IM/agent clients for Abyss core self-evolution.

Problem:

- External clients may currently be convenient for scheduling, notification, or provider access.
- They must not become the place where Abyss stores or executes its core FSM/self-evolution logic.
- If Abyss self-evolution only works because an external client provides hidden tools, file mutation, scheduling, approval, memory, or execution authority, the architecture is invalid.

Required design:

```text
OS scheduler or manual command
  -> python -m abyss_cli evolution run --scheduled
  -> Abyss-native roadmap selection / proposal approval check
  -> Abyss-native bounded implementation workflow
  -> deterministic checks
  -> HarnessAgent review through declared provider interface
  -> audit + Git evidence
  -> notification through optional channel
```

Allowed external roles:

- Optional trigger.
- Optional notification channel.
- Optional LLM/provider interface declared in config.
- Optional human interaction surface.

Forbidden external roles:

- Required FSM state owner.
- Required self-evolution executor.
- Required file mutation tool.
- Required approval authority.
- Required audit source of truth.
- Required scheduler for correctness.
- Hidden dependency for Harness or policy decisions.

Deliverables:

- Add native `abyss evolution run --scheduled` command.
- Add `abyss evolution list/show/approve` or equivalent record inspection commands.
- Store evolution records under `.local/runtime/evolution/`.
- Move daily evolution instructions from external-client prompt text into Abyss code/docs/config.
- Replace external-client-dependent daily task with either OS scheduler invoking Abyss CLI, or a minimal external trigger that only calls the native command.

Acceptance:

```powershell
python -m abyss_cli evolution run --scheduled --dry-run
python -m abyss_cli evolution list
python -m abyss_cli check
```

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
4. Capabilities discovered by self-inspection but not already listed in the roadmap backlog must be recorded as `EvolutionProposal` only.
5. A non-backlog `EvolutionProposal` must receive explicit user approval before any real implementation work starts.
6. Execute at most one bounded backlog slice per scheduled run.
7. Stop and notify the user if the slice requires credentials, broad refactors, destructive migration, production access, or ambiguous product judgment.

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

1. **Scope gate** — selected implementation work must map to one roadmap backlog item. A self-discovered non-backlog proposal cannot be implemented until explicitly approved by the user and added/marked as approved.
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
  roadmap_id: A2 | null
  title: string
  source: roadmap_backlog | self_discovered
  user_approval_required: true | false
  user_approval_status: not_required | pending | approved | rejected
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

### Scheduled delivery cadence

Default cadence is low-frequency but continuous:

- Run once per day at a fixed configured time.
- Each run should attempt to evolve one bounded capability slice.
- Prefer delivering a concrete, user-visible function increment over producing only a proposal.
- If no safe executable roadmap slice exists, deliver an `EvolutionProposal` explaining the self-discovered capability and wait for explicit user approval before implementation.
- Never run more frequently than hourly.
- Prefer daytime local time.

Daily delivery output should include:

- Selected roadmap item or discovered evolution proposal.
- What capability changed.
- Files changed.
- Checks executed and results.
- HarnessAgent review result.
- Commit hash and push status if code/docs changed.
- How the user can verify the new function.
- Any blocker, risk, or required user decision.

Recommended prompt for scheduled run:

```text
Run today's Abyss controlled self-evolution cycle. Prefer the next executable item from ROADMAP.md and attempt to deliver one bounded, user-visible capability increment. If no roadmap item is executable, inspect the system for one suitable evolution capability and record it as an EvolutionProposal only; do not implement self-discovered non-backlog capabilities until the user explicitly approves them. Execute at most one bounded roadmap slice only if it passes scope/risk/check/HarnessAgent gates. Do not perform destructive actions, credential work, broad refactors, production access, or unreviewed external side effects. Commit and push focused successful repository changes when checks pass. At the end, deliver the evolved function or pending approval proposal back to the user: summarize what changed or what is proposed, files changed, checks, HarnessAgent result, commit hash, push status, verification command when applicable, and any risks or blockers. You must use the notify mechanism to proactively inform the user of success or exception.
```

## Near-term priority order

0. A0 P0: Native Evolution Runner and external-client decoupling.
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

The next implementation slice must be **A0 P0: Native Evolution Runner and external-client decoupling**.

Reason:

- Daily self-evolution is a core Abyss capability.
- Core Abyss capability must not depend on an external LLM/Knot/IM/agent client runtime.
- The current scheduled reminder can exist only as a temporary external trigger, not as the owner of the evolution workflow.

Minimum slice:

- Add `abyss_cli/evolution.py`.
- Add CLI entry for `abyss evolution run --scheduled --dry-run`.
- Add `abyss evolution list` and `abyss evolution show latest` if small enough for the slice.
- Add local runtime directory `.local/runtime/evolution/`.
- Implement roadmap-backed slice selection in dry-run mode first.
- Enforce: roadmap-listed items may be selected for implementation; self-discovered non-backlog items require user approval before implementation.
- Add docs and `python -m abyss_cli check` coverage.
- Update or replace the external scheduled task so it only triggers the native command and does not contain the workflow logic.

