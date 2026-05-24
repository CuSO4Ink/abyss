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

### R003. Native Governed OperationSet and Implementation Bootstrap

Source proposal: `evo_prop_20260524_002641_100ced`.

Purpose: Native Governed OperationSet and Implementation Bootstrap

Why it is needed: 目标：补齐 Abyss 已批准 ROADMAP item 从授权到实现的最小受治理闭环。范围包括：operation-based ChangeSet/OperationSet schema、capability registry、最小 Local Executor MVP、ChangeSet review/approval flow、Implementation Agent MVP、execution evidence/owner report。第一版只开放 fs.create_file、fs.replace_exact、fs.append_file 和白名单 check.command；不开放任意 shell、浏览器自动化、端口服务启动、外部接口写入、git push、policy/prompt/governance 修改。所有新增能力必须继续遵守 P0 外部接口边界、ROADMAP 逐条批准规则和 no_action_executed Agent 边界。

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

### R004. Native Autonomous Workflow Orchestrator Bootstrap

Source proposal: `evo_prop_20260524_024143_bcfaec`.

Purpose: Native Autonomous Workflow Orchestrator Bootstrap

Why it is needed: Final bootstrap to remove external assistant dependency from normal Abyss feature iteration: roadmap execution state, workflow tick/watch, owner inbox approval, automatic continuation through implementation, dry-run, HarnessAgent review, ChangeSet approval gate, Executor apply, check, audit, summary and reports.

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

### R005. 把 self-evolution Agent 真正接入 evolution propose 主流程

Source proposal: `evo_prop_20260524_033737_a48b61`.

Purpose: 把 self-evolution Agent 真正接入 evolution propose 主流程

Why it is needed: Approved evolution proposal.

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

### R006. 替代 R005：让 evolution propose 消费 self-evolution Agent analysis 生成高质量 proposal

Source proposal: `evo_prop_20260524_034731_e25608`.

Purpose: 替代 R005：让 evolution propose 消费 self-evolution Agent analysis 生成高质量 proposal

Why it is needed: This request supersedes the thin approved R005 proposal. The smoke test showed that self-evolution Agent can produce a valid evolution_analysis, but evolution propose does not consume that analysis and instead creates a generic proposal. Required outcome: when proposing a user request, Abyss should call or read the latest matching self-evolution analysis and include its summary, minimal_slice, risks, roadmap_status, implementation_allowed_now, and acceptance_checks in the proposal. The proposal must remain pending user approval and must not auto-approve, auto-write ROADMAP, execute code, or let the Agent approve/reject anything. Acceptance: with a short request, the generated proposal reflects self-evolution analysis instead of generic template text.

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

### R007. R007 Provider and Agent Health Check

Source proposal: `evo_prop_20260524_041427_27c56b`.

Purpose: R007 Provider and Agent Health Check

Why it is needed: Add a governed CLI health check capability for the real LLM provider and registered agents. The system should expose commands such as provider check and/or agent health to verify that self_evolution, implementation, and harness can call the current real provider and produce valid outputs. The result should include pass/fail, elapsed time, error summary, and recent run record path where available. The summary command should surface a concise health status. This must be implemented through the governed evolution workflow, not by direct file edits.

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
