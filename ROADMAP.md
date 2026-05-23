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

### R001. Governed self-iteration intake and evolution mechanism

Purpose: replace ad-hoc direct system modification with a safer, explicit, staged self-iteration chain.

Why it is needed: the current pattern where the assistant immediately modifies system files after conversational feedback is useful during bootstrapping, but becomes increasingly risky as the system grows. Abyss needs a native mechanism that separates raw user requests, normalized proposals, approved roadmap items, implementation slices, review, and completion evidence.

Minimal implementation slice:

- Define a native intake structure for user change requests.
- Define proposal states such as inbox, normalized, proposed, needs_user_decision, approved, planned, implementing, reviewing, done, rejected, and deferred.
- Ensure raw user requests do not automatically become approved roadmap items.
- Ensure only explicitly approved items can become executable self-iteration targets.
- Provide a way to list and inspect pending requests/proposals.
- Provide a standard LLM-provider smoke test for the self-iteration chain.
- Define a self-evolution Agent that can analyze and propose plans, but cannot execute, approve, mutate files, schedule work, or operate Git.
- Provide explicit approve/reject commands for evolution proposals.
- Add approved proposals to `ROADMAP.md` only after explicit approval.
- Provide a governed switch that disables ordinary direct modification mode after the chain is accepted.
- Preserve the transitional direct-modification rule until the user explicitly accepts the completed chain.

Expected user-visible result: the user can express desired changes without the assistant immediately mutating system design, while still allowing approved items to progress through a controlled evolution path.

Risk level: L2.

Acceptance check:

- A new user change request can be recorded without becoming executable by default.
- A proposal can be inspected before approval.
- Only user-approved items can enter the executable roadmap.
- The system documentation clearly distinguishes transitional direct modification from the final governed self-iteration mechanism.

### R002. 收口自我迭代治理链路

Source proposal: `evo_prop_20260523_234133_b4d546`.

Purpose: 收口自我迭代治理链路

Why it is needed: 补齐 approve/reject、批准后写入 ROADMAP、直接修改模式 finalize 开关和完整性检查

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
