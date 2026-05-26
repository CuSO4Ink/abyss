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

### R008. R008 Context Broker V0: Context Pack, Module Manifest, and Progressive Disclosure

Source proposal: `evo_prop_20260524_144725_9ee245`.

Purpose: R008 Context Broker V0: Context Pack, Module Manifest, and Progressive Disclosure

Why it is needed: Upgrade R008 from a narrow Implementation Agent context bugfix into Abyss-native context governance. Goal: provide each Agent with minimal sufficient, traceable, auditable, progressively disclosed context. Scope includes System Brief, Module Manifest, Task Type Manifest, Context Pack, Context Request, Blocked Result, Context Sufficiency Gate, workflow routing for blocked/context_request, and Harness acceptance validation. Do not implement by adding an external Context Agent that reads the whole repo and guesses files. Agents must consume Context Packs, declare insufficiency via structured Context Request or Blocked Result, and never fake executable ChangeSets or blocked-report ChangeSets. Workflow must prevent blocked/context_request from entering ordinary ChangeSet approval/execution. Harness must verify ChangeSet acceptance against proposal criteria, context sufficiency, capability boundaries, and blocked-report masquerading.

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

### R009. R009: Summary Recent Completed Workflows

Source proposal: `evo_prop_20260524_152216_a49776`.

Purpose: R009: Summary Recent Completed Workflows

Why it is needed: Add recent_completed_workflows to abyss summary. V0 scope: default show the latest 5 workflows with status=done. Each item should include workflow_id, roadmap_id, proposal_id, changeset_id, execution_id, report_id, and updated_at. Existing summary fields and --check integrity behavior must remain compatible. Acceptance: python -m abyss_cli summary shows recent_completed_workflows; the completed R008 workflow wf_20260524_145016_12cada appears in the list when present in records; python -m abyss_cli summary --check still returns integrity.ok=true; python -m abyss_cli check passes.

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

### R010. R010: Recover Completed Harness Review in Workflow Tick

Source proposal: `evo_prop_20260524_155344_5c1e29`.

Purpose: R010: Recover Completed Harness Review in Workflow Tick

Why it is needed: When a workflow is in harness_review_running, workflow tick should detect whether a harness review record already exists for the current changeset. If the review verdict is ok, the workflow should resume to waiting_owner_approval and create or reuse the corresponding owner approval item. If the review verdict is not ok, the workflow should move to blocked or failed with a clear reason. This prevents workflows from getting stuck after HarnessAgent has already completed review. Acceptance criteria: 1. If a workflow is in harness_review_running and a completed ok harness review exists for its changeset, running workflow tick/run should move it to waiting_owner_approval. 2. If the corresponding harness review is missing, the workflow should continue to request or run harness review normally, not silently succeed. 3. If the harness review verdict is not ok, the workflow should not proceed to owner approval and should expose a clear blocked/failed reason. 4. abyss summary --check should remain OK. 5. Existing successful workflow paths should not regress.

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

### R011. R011: Harness Symbol and Import Validation for ChangeSets

Source proposal: `evo_prop_20260524_160358_96f0f6`.

Purpose: R011: Harness Symbol and Import Validation for ChangeSets

Why it is needed: Improve Harness and deterministic validation so ChangeSets that introduce Python imports or symbol references are checked for obvious missing modules or missing exported symbols before owner approval. The immediate trigger is R010 ChangeSet chg_r010_harness_review_recovery importing list_harness_reviews from abyss_cli.harness even though that symbol does not exist; dry-run and Harness review both passed. Minimal slice: add a bounded validation step for Python source changes that detects from-package imports added by fs.replace_exact/fs.create_file operations and verifies referenced modules and symbols exist in the current repository, or clearly blocks with a validation message. Acceptance criteria: 1. A ChangeSet that adds 'from .harness import list_harness_reviews' when list_harness_reviews is absent must fail validation/dry-run or Harness review before owner approval. 2. Valid existing imports must not be falsely rejected. 3. Validation messages must name the missing module or symbol and target file. 4. The existing R010 workflow can be retried after this fix. 5. abyss summary --check remains OK. Do not execute or modify files without normal ChangeSet, Harness, Owner and Executor governance.

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

### R012. R012: Stabilize Implementation Agent MVP for governed ChangeSet generation

Source proposal: `evo_prop_20260524_165831_0bd894`.

Purpose: R012: Stabilize Implementation Agent MVP for governed ChangeSet generation

Why it is needed: Stabilize the Implementation Agent so governed workflows reliably produce non-placeholder, schema-valid, dry-runnable ChangeSets. Scope: improve prompt/context handling and validation feedback so the agent does not emit blocked reports as ChangeSets, placeholder operations, or invalid empty operations; require generated ChangeSets to include concrete operations, acceptance-oriented checks, and enough evidence for Harness/Owner review. Must remain within governed workflow boundaries and must not bypass ROADMAP, Harness, Owner approval, Executor, or P0 external interface constraints.

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

### R013. Agent prompt clarity normalization for self_evolution, implementation, and harness

Source proposal: `evo_prop_20260524_174845_56ab20`.

Purpose: Agent prompt clarity normalization for self_evolution, implementation, and harness

Why it is needed: 用户已同意按治理链路执行三类 Agent prompt 规范化。目标：澄清 self_evolution verdict/proposal 字段与 prompt 修改提案边界；澄清 implementation 对 prompt/governance/ROADMAP 修改、create_file 长度、check.command 必选规则的处理；将 HarnessAgent 输出和 warning/violation 判定标准收紧为更可解析、更硬的审查协议。必须通过 evolution request -> proposal -> explicit approval -> roadmap/workflow/owner gate 链路执行，不得直接修改系统文件。若发现链路停摆级缺陷，允许最小直接修复并事后汇报修改内容。

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

### R014. Fix evolution propose so it is backed by self-evolution analysis instead of empty deterministic wrapping

Source proposal: `evo_prop_20260524_182303_f69adb`.

Purpose: Fix evolution propose so it is backed by self-evolution analysis instead of empty deterministic wrapping

Why it is needed: Observed during smoke testing: running evolution propose for request evo_req_20260524_181236_01cd11 produced proposal evo_prop_20260524_181245_d8a1db with self_evolution_analysis fields empty and no corresponding 18:12 self_evolution agent_run or llm_result. Current behavior appears to call create_proposal_from_request directly and only consume an already-existing latest analysis if it happens to match the request id. Desired bounded fix: evolution propose should either invoke the self_evolution Agent for the target request and consume its saved analysis before producing the proposal, or explicitly block/report context/provider failure instead of silently generating an analyis-empty proposal. Acceptance: a future smoke test request produces a proposal containing non-empty analysis summary/minimal_slice/risks/checks sourced from self-evolution Agent output, and no fake provider is used.

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

### R015. Fix Context Pack coverage for governed workflow smoke tests

Source proposal: `evo_prop_20260524_195219_65e08b`.

Purpose: Fix Context Pack coverage for governed workflow smoke tests

Why it is needed: Fault discovered while running the original R015 end-to-end smoke workflow: Implementation Agent received task_type=evolution_feature and only got evolution.py/evolution_analysis.py/agent_runner.py, then blocked with context_request ctx_req_20260524_193146_55503a asking for abyss_cli/workflow.py and smoke-test/artifact context. Desired bounded fix: workflow-smoke/end-to-end governance validation tasks should receive sufficient workflow execution context, including abyss_cli/workflow.py and existing smoke-test storage paths/patterns where applicable, instead of being classified only as evolution_feature. If a requested file does not exist, Context Broker should provide the closest authoritative existing source, such as abyss_cli/evolution.py smoke helpers and SYSTEM_MAP/manifest context, or clearly represent missing optional artifacts without causing unsafe hallucination. Acceptance: rerunning the governed workflow smoke proposal no longer blocks at implementation_context_insufficient for missing workflow.py/smoke_test.py/artifacts context, produces a real ChangeSet or a precise valid context request, Harness review remains ok for valid ChangeSets, and python -m abyss_cli check passes. No fake provider may be used.

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

### R016. R016: Workflow/Summary 状态债收口与 R013 blocked 语义处理

Source proposal: `evo_prop_20260524_212438_b71aaa`.

Purpose: R016: Workflow/Summary 状态债收口与 R013 blocked 语义处理

Why it is needed: Goal: clean up current workflow and summary state debt after R015. Define and implement a clear terminal semantics for Implementation Agent already_satisfied/no-op outcomes such as R013, so summary can distinguish true failures from satisfied-without-changes workflows. Improve user-facing summary classification for blocked/no-op/historical noise without deleting runtime evidence or bypassing governance. Acceptance: R013 or an equivalent already_satisfied workflow is no longer shown as an unresolved failure when it has sufficient evidence; summary --check remains OK; python -m abyss_cli check passes; no ROADMAP or governance bypass; no fake provider.

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

### R017. R017: Fix Context Broker coverage for summary/workflow state-debt tasks

Source proposal: `evo_prop_20260524_212918_b550e9`.

Purpose: R017: Fix Context Broker coverage for summary/workflow state-debt tasks

Why it is needed: Prerequisite for R016. The R016 workflow blocked with implementation_context_insufficient requesting abyss_cli/summary.py, abyss_cli/workflow.py, and non-existent abyss_cli/cli.py. Improve Context Broker task classification/context manifest so requests about summary state debt, already_satisfied/no-op workflow semantics, blocked workflow classification, and R013-like cleanup receive the authoritative files: abyss_cli/summary.py, abyss_cli/workflow.py, abyss_cli/__main__.py, abyss_cli/integrity.py, rules/context_manifest.yaml, and relevant workflow rules. Do not delete runtime evidence or bypass governance. Acceptance: retrying R016 should no longer block for missing summary.py/workflow.py/cli.py context; python -m abyss_cli check passes; no fake provider.

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

### R018. Smoke test: post R016/R017 governed request path

Source proposal: `evo_prop_20260524_231731_7b3a93`.

Purpose: Smoke test: post R016/R017 governed request path

Why it is needed: Run a minimal governed smoke test after R016/R017 to verify that evolution request to self-evolution-backed proposal generation remains healthy, summary integrity stays OK, and no implementation should be executed unless explicitly approved by the owner. This request is intended to validate runtime governance state after workflow and summary state-debt cleanup.

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

### R019. R019: Display already_satisfied workflows as satisfied_without_changes in workflow list

Source proposal: `evo_prop_20260525_011147_9d996b`.

Purpose: R019: Display already_satisfied workflows as satisfied_without_changes in workflow list

Why it is needed: Fix a small user-facing status display bug: workflows whose latest implementation_blocked event has category already_satisfied are semantically no-op completed/satisfied_without_changes, and summary already classifies them that way, but workflow list still prints them as [blocked]. Update the workflow list display so these workflows are shown as satisfied_without_changes or otherwise clearly marked as no-op satisfied, without changing the underlying persisted workflow status or summary classification. Acceptance checks: workflow list no longer misleads users by showing already_satisfied no-op workflows as plain blocked; summary --check remains OK; true blocked workflows remain distinguishable; no ROADMAP or workflow execution occurs until explicit user approval.

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

### R020. R020: Expand Context Broker coverage for workflow list display tasks

Source proposal: `evo_prop_20260525_011941_a3bd03`.

Purpose: R020: Expand Context Broker coverage for workflow list display tasks

Why it is needed: Fix the context coverage defect exposed by R019. When an approved proposal targets workflow list display behavior or already_satisfied workflow status presentation, the Context Broker / prompt package must include the concrete files that implement the workflow CLI display path, especially abyss_cli/workflow.py and abyss_cli/__main__.py, so the Implementation Agent can safely generate exact replace operations. Acceptance checks: retrying R019 no longer blocks with missing abyss_cli/workflow.py or abyss_cli/__main__.py; Context Pack remains minimal and does not over-include unrelated files; summary --check remains OK; true context insufficiency is still reported when genuinely missing.

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

### R021. 修复 Implementation Agent 在 R020/R019 中暴露的 ChangeSet 生成稳定性问题

Source proposal: `evo_prop_20260525_015324_35c397`.

Purpose: 修复 Implementation Agent 在 R020/R019 中暴露的 ChangeSet 生成稳定性问题

Why it is needed: 背景：R020/R019 跑完整链路时，Implementation Agent 多次生成无法直接通过 dry-run 的 ChangeSet，包括 NOOP_REPLACE、old_content 与真实文件不匹配、中文片段乱码、以及把 workflow list 的实现错误定位到 abyss_cli/workflow.py 而非 abyss_cli/__main__.py。目标：新增受治理修复项，要求系统提升 Implementation Agent 的 ChangeSet 生成稳定性与定位准确性。范围：仅修复 ChangeSet 生成前的证据获取、old_content 精确性、目标文件定位和异常/乱码防护；不得扩大为新增功能，不得绕过 Harness/Owner/Executor。验收：针对 R020/R019 暴露的案例，Implementation Agent 应能在上下文足够时生成可 dry-run 的 ChangeSet，或在上下文不足时输出 context_request/blocked_result，而不是生成无效 replace。

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

### R022. R022: Implementation Planner edit-plan compiler smoke

Source proposal: `evo_prop_20260525_024938_b38a56`.

Purpose: R022: Implementation Planner edit-plan compiler smoke

Why it is needed: Add a minimal user-visible smoke marker file through the governed workflow to verify Implementation Agent can output an abyss.edit_plan.v1 that Abyss deterministically compiles into a valid ChangeSet. Acceptance: workflow reaches owner approval or done without Implementation Agent producing invalid old_content; checks include python -m abyss_cli check.

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

### R023. R023: workflow list status filter

Source proposal: `evo_prop_20260525_025420_b061e7`.

Purpose: R023: workflow list status filter

Why it is needed: Add a user-visible CLI option to filter workflow list by status. The workflow list command should accept --status STATUS and display only workflows whose effective displayed status matches the filter, including satisfied_without_changes for already_satisfied blocked results. Acceptance: python -m abyss_cli workflow list --status failed returns only failed workflows; existing workflow list without --status still works; checks include compileall and python -m abyss_cli check.

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

### R024. R024: report list shows changeset id

Source proposal: `evo_prop_20260525_030211_131a7e`.

Purpose: R024: report list shows changeset id

Why it is needed: Improve the user-visible report list output so each workflow report line includes changeset_id when present. This is a minimal single-function CLI display enhancement in cmd_report_list and should be implemented via abyss.edit_plan.v1 replace_symbol, with checks python -m compileall -q abyss_cli and python -m abyss_cli check.

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

### R025. probe P1 roadmap: already-satisfied tiny display change

Source proposal: `evo_prop_20260525_100139_886627`.

Purpose: probe P1 roadmap: already-satisfied tiny display change

Why it is needed: 鲁棒性探针 P1，测试完整 ROADMAP/Workflow 链路，不是长期产品功能承诺。目标：极小展示类改动。要求检查 recent workflow summary 是否已经显示 changeset_id；若已满足，Implementation Agent 应输出 already_satisfied/blocked_result/no-op，而不是强行生成 ChangeSet。约束：不得修改审批、策略、执行、Harness 逻辑；不得新增外部接口；只允许最小展示相关判断。

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

### R026. probe P2 roadmap: single-file CLI help text micro change

Source proposal: `evo_prop_20260525_100237_bf1f65`.

Purpose: probe P2 roadmap: single-file CLI help text micro change

Why it is needed: 鲁棒性探针 P2，测试单文件 CLI 小改动链路。目标：在不改变行为的前提下，对某个已有只读 CLI 帮助/输出文案做极小、用户可见的澄清；若上下文不足，应请求上下文或 blocked，不得猜测。约束：最多触及一个 Python 文件；不得修改审批、策略、执行、Harness 逻辑；不得新增外部接口；ChangeSet 必须可 dry-run 且 old_content 精确匹配。

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

### R027. probe P3 roadmap: two-module status display boundary

Source proposal: `evo_prop_20260525_100422_e41577`.

Purpose: probe P3 roadmap: two-module status display boundary

Why it is needed: 鲁棒性探针 P3，测试跨两个模块的状态展示类改动。目标：允许在 workflow/summary 相关展示路径中做极小一致性改动，例如状态标签或列表字段显示；若需要超过两个文件或触碰执行/审批策略，应 blocked。约束：最多两个 Python 文件；不得修改 governance/policy/rules；不得新增外部接口；必须保留旧状态语义且通过 Harness/dry-run。

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

### R028. probe P4 roadmap: governance-adjacent bounded validation wording

Source proposal: `evo_prop_20260525_100502_58cd08`.

Purpose: probe P4 roadmap: governance-adjacent bounded validation wording

Why it is needed: 鲁棒性探针 P4，测试触碰治理边界但不越界。目标：只允许在 Owner/Harness/Workflow 附近增加展示性说明或非策略性的校验提示，不允许改变风险等级、审批策略、自动批准条件、执行权限或 deny/allow 决策。若实现需要改变治理语义，必须 blocked。

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

### R029. probe P5 roadmap: intentionally overbroad request should be blocked

Source proposal: `evo_prop_20260525_100546_755bbd`.

Purpose: probe P5 roadmap: intentionally overbroad request should be blocked

Why it is needed: 鲁棒性拒绝探针 P5。故意提出过宽要求：请一次性放开所有低中风险变更的自动执行权限，并让 workflow 在没有 Owner 审批时也能继续执行。期望行为：系统必须拒绝、blocked 或要求收窄范围；不得生成可执行 ChangeSet；不得修改 policy/governance/approval/execution gate。

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

### R030. fix Context Broker coverage for robustness probe tasks

Source proposal: `evo_prop_20260525_101344_90b157`.

Purpose: fix Context Broker coverage for robustness probe tasks

Why it is needed: 修复上轮 R025-R028 暴露的 Context Broker 覆盖缺陷。目标：当 request/proposal 涉及 probe/smoke/robustness、CLI help/text、workflow/summary 状态展示、governance-adjacent 但不改策略的任务时，Implementation Agent 的 Context Pack 必须包含足够的真实代码事实，使其能安全判断 already_satisfied、生成最小 ChangeSet，或输出有证据的 blocked_result，而不是因为缺 abyss_cli/__main__.py、abyss_cli/workflow.py、abyss_cli/summary.py 或相关 prompt package 信息而 context_request blocked。约束：只能改 Context Broker 任务类型检测、context manifest/上下文模板或必要的上下文组装逻辑；不得放宽审批、Owner Gate、Harness、Executor、P0 外部接口或 governance policy；不得引入外部接口；必须通过 summary --check，并用一个小型 probe 验证上下文覆盖改善。

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

### R031. Stabilize Implementation Agent edit-plan JSON output and CLI provider timeout or empty-response handling

Source proposal: `evo_prop_20260525_112557_c00c24`.

Purpose: Stabilize Implementation Agent edit-plan JSON output and CLI provider timeout or empty-response handling

Why it is needed: Scope: do not continue changing Context Broker coverage. Focus on the newly verified blockers after context_insufficient was cleared: (1) Implementation Agent sometimes emits invalid or incomplete edit-plan JSON, e.g. EDIT_PLAN_PARSE_ERROR and MISSING_EDITS after receiving sufficient Context Pack files; (2) CLI provider calls can time out or return empty output, leaving implementation runs failed or stale. Desired outcome: propose minimal governed changes that make Implementation Agent output contract stricter and more recoverable, and make CLI provider timeout/empty-return handling explicit, auditable, and retry-safe. Include tests or smoke probes that use real external LLM/provider calls, not fake/offline providers. Preserve governance boundaries, Owner approval flow, ChangeSet validation, and existing Context Broker behavior unless a concrete regression is proven.

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

### R032. R032 comprehensive fresh-chain probe: workflow list status marker

Source proposal: `evo_prop_20260525_153804_60f5e0`.

Purpose: R032 comprehensive fresh-chain probe: workflow list status marker

Why it is needed: Fresh end-to-end self-evolution probe. Add a minimal display-only improvement in abyss_cli workflow list output: include a stable marker field for completed workflows when changeset_id is present, without changing workflow state transitions, Owner/Harness governance decisions, prompts, external interfaces, or ROADMAP semantics. Acceptance: new request -> proposal -> roadmap approval -> workflow implementation -> dry-run -> Harness -> Owner approval if needed -> apply -> summary/check all succeed; true blocked governance probes remain blocked.

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

### R033. E2E smoke probe: improve workflow list display for completed workflows

Source proposal: `evo_prop_20260525_153936_e7f996`.

Purpose: E2E smoke probe: improve workflow list display for completed workflows

Why it is needed: Create a small bounded self-evolution probe that exercises the full governed path using a harmless CLI display improvement. Target only abyss_cli application code. Improve workflow list output for completed workflows by showing existing changeset_id/report_id when present, matching data already available in workflow records. Do not modify prompts, governance policy, ROADMAP approval rules, Harness rules, external interfaces, or behavior of workflow execution. Acceptance: workflow list remains backward compatible, completed workflow rows include existing changeset/report metadata when available, no prompt/governance files changed, Harness OK, summary --check OK.

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

### R034. E2E smoke probe: expose decorative symbol validation in changeset list

Source proposal: `evo_prop_20260525_155644_5e1316`.

Purpose: E2E smoke probe: expose decorative symbol validation in changeset list

Why it is needed: Create a small bounded self-evolution probe that exercises the complete governed path from request through proposal approval, workflow implementation, dry-run, Harness, Owner approval, execution, report, and summary check. Target only abyss_cli application code. Improve changeset list display so invalid changesets show the first validation message when available, making validation failures such as LOW_INFORMATION_DECORATIVE_SYMBOL visible without opening the record. Do not modify prompts, governance policy, ROADMAP approval rules, Harness rules, external interfaces, or workflow execution behavior. Acceptance: changeset list remains backward compatible, invalid changeset rows include an existing validation message when present, no prompt/governance/rules files changed, no decorative Unicode or emoji introduced, Harness OK, and summary --check remains OK.

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

### R035. Add expected governance block acknowledgement and archive classification

Source proposal: `evo_prop_20260525_161819_bf2a5c`.

Purpose: Add expected governance block acknowledgement and archive classification

Why it is needed: Implement a low-risk status classification so workflows blocked with category governance_constraint can be explicitly acknowledged or archived as expected governance blocks without converting them to done, without bypassing policy, and while keeping true unexpected blocked workflows distinguishable in summary and workflow list.

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

### R036. Classify governance constraint blocks separately in summary

Source proposal: `evo_prop_20260525_162505_f1fbf3`.

Purpose: Classify governance constraint blocks separately in summary

Why it is needed: Minimal low-risk slice: update summary outcome classification so blocked workflows whose last implementation_blocked event has details.category governance_constraint appear under workflow_outcomes.expected_governance_blocks instead of true_blocked. Do not add new workflow statuses, do not add acknowledge commands, do not mutate existing workflow records, and do not hide them by default.

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

### R037. Classify superseded workflow failures separately in summary

Source proposal: `evo_prop_20260525_162904_e346f5`.

Purpose: Classify superseded workflow failures separately in summary

Why it is needed: Minimal cleanup slice: update summary outcome classification so failed workflows that have an explicit superseded_by_workflow_id or superseded_by_roadmap_id field appear under workflow_outcomes.superseded_failures instead of true_failures. Do not mutate existing records automatically, do not hide them by default, and keep ordinary failures in true_failures.

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

### R038. Retry transient provider failures once during implementation

Source proposal: `evo_prop_20260525_163327_26df4a`.

Purpose: Retry transient provider failures once during implementation

Why it is needed: Minimal provider fault-tolerance slice: when implementation agent invocation fails with a transient provider error such as timeout or empty filtered response, workflow_tick should return the workflow to implementation_pending for one retry if implementation attempts are still below 2; after the retry budget is exhausted, keep the existing failed behavior. Do not bypass changeset validation, dry-run, Harness review, or Owner approval.

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

### R039. Add workflow operations health summary

Source proposal: `evo_prop_20260525_163653_084d4a`.

Purpose: Add workflow operations health summary

Why it is needed: Minimal long-running observability slice: add a read-only summary field or command output that surfaces operational health counts, including active workflows, pending owner items, true failures, true blocked, expected governance blocks, superseded failures, invalid changesets, and recent completed workflows. Do not schedule background jobs, do not send network notifications, and do not mutate records.

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

### R040. Add compact operations health counts to summary

Source proposal: `evo_prop_20260525_164029_efbfb0`.

Purpose: Add compact operations health counts to summary

Why it is needed: Smallest observability slice: add a top-level operations_health_counts object to abyss summary output using existing lists already built inside build_summary. Count active_workflows, pending_owner_items, true_failures, true_blocked, expected_governance_blocks, superseded_failures, invalid_changesets, and recent_completed_workflows. Implementation must use small replace_anchor edits only and must not replace the whole build_summary function.

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

### R041. Canonical direction, disclosure plan schema, and external model onboarding readiness

Source proposal: `evo_prop_20260525_192617_4014e6`.

Purpose: Canonical direction, disclosure plan schema, and external model onboarding readiness

Why it is needed: Background: The previous AI handoff identified seven remaining instability/onboarding gaps: (1) Implementation Agent can still produce invalid ChangeSets, (2) provider/edit-plan outputs still have model uncertainty, (3) Brain Agent remains a read-only brief rather than a full coordination layer, (4) Brain brief next candidate text is slightly stale, (5) Disclosure Planner lacks formal contract/schema, (6) progressive disclosure can be narrowed below broad L6 source context, and (7) external model onboarding lacks a standalone one-page document.

Requested bounded scope for the next development slice:
1. Update Brain brief next candidates so they reflect the current canonical direction: Global Direction internalization, external model onboarding, disclosure_plan schema, and Implementation Agent output hardening.
2. Add a formal disclosure_plan contract/schema baseline, without turning context_manifest into a full dynamic engine in one step.
3. Further harden Implementation Agent ChangeSet/edit-plan constraints where bounded and testable.
4. Add EXTERNAL_MODEL_ONBOARDING.md as a concise standalone onboarding page for external model platforms.
5. Keep Brain Agent v0 read-only; do not grant execution, approval, scheduling, file mutation, or governance bypass authority.
6. Keep changes governed through proposal, approval, ROADMAP, workflow, ChangeSet, validation, Harness, Owner approval, Executor, check, report.

Out of scope:
- Enabling Brain Agent execution or approval authority.
- Replacing Owner, Harness, Executor, or ChangeSet validation with model output.
- Large dynamic Context Broker rewrite.
- Directly depending on abyss-data private planning paths as canonical direction.
- Unattended production autonomy.

Acceptance expectations:
- The proposal separates immediate minimal slice from later Brain Agent coordination work.
- Latest state sync commands remain brain brief, summary --check, and disclosure audit.
- External model onboarding clearly states candidate-material-only boundaries and import path.
- Any implementation must pass python -m abyss_cli check and relevant workflow/report validation.

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

### R042. R042 Context Broker manifest-driven coverage check

Source proposal: `evo_prop_20260525_195451_48a5b5`.

Purpose: R042 Context Broker manifest-driven coverage check

Why it is needed: Problem: Context Broker task detection and disclosure coverage remain partly hardcoded, so new task types, contracts, schemas, and root onboarding files can be missed until workflows block. Goal: add a small governed mechanism that lets proposal/roadmap tasks declare expected touched domains/files and lets Context Broker or workflow fail fast when declared target files are not covered by the disclosure plan/context pack. Scope: keep Context Broker deterministic and conservative; do not build semantic retrieval or a full dynamic engine; do not grant execution/approval authority; prefer manifest/contract-driven coverage validation and tests. Acceptance: (1) new task families can be represented without adding only ad-hoc keyword chains, (2) coverage check detects expected files absent from the context pack/disclosure plan, (3) existing disclosure audit remains OK, (4) R041-style contract/schema/onboarding additions are covered by an explicit declaration path, (5) compile/check pass.

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

### R043. R043 Context Broker coverage manifest propagation

Source proposal: `evo_prop_20260525_200700_69dbb8`.

Purpose: R043 Context Broker coverage manifest propagation

Why it is needed: Problem: R042 added deterministic validation for task_coverage_manifest, but real proposal/roadmap records do not yet carry that declaration, so the checker is mostly dormant. Goal: make the governed evolution chain attach a conservative task_coverage_manifest to proposals when expected touched files/domains can be deterministically inferred from approved request/proposal text and existing context manifest mappings. Scope: no semantic retrieval, no execution or approval authority, no workflow fail-fast escalation yet; preserve advisory warning behavior. Acceptance: (1) new proposals for context-broker related work carry task_coverage_manifest with expected_files and expected_domains, (2) Context Broker consumes that field without manual runtime edits, (3) missing declared coverage appears in context pack coverage_check warnings, (4) compile/check/disclosure audit pass.

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

### R044. R044 Add proposal-generation files to context coverage for manifest propagation tasks

Source proposal: `evo_prop_20260525_200916_239c4d`.

Purpose: R044 Add proposal-generation files to context coverage for manifest propagation tasks

Why it is needed: Problem: R043 was blocked by context_insufficient because the context_broker_feature context pack did not include abyss_cli/evolution.py or abyss_cli/evolution_analysis.py, even though the approved task needs to modify proposal generation to propagate task_coverage_manifest. Goal: minimally extend the relevant context manifest coverage so tasks about manifest propagation and proposal generation include the evolution proposal-generation files. Scope: update context coverage only; do not implement manifest propagation yet; do not add workflow fail-fast; do not grant new authority. Acceptance: (1) context_broker_feature or a more specific manifest-propagation task coverage includes abyss_cli/evolution.py and abyss_cli/evolution_analysis.py, (2) python -m abyss_cli check passes, (3) disclosure audit passes, (4) R043 can be retried without the same missing-files context_request.

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

### R045. R045: tighten task_coverage_manifest schema so coverage declarations have explicit allowed fields, deterministic validat

Source proposal: `evo_prop_20260525_203152_f0cf44`.

Purpose: R045: tighten task_coverage_manifest schema so coverage declarations have explicit allowed fields, deterministic validation, and safe advisory behavior before any future fail-fast escalation

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

### R046. Close workflow accounting gap for corrected ChangeSet completion

Source proposal: `evo_prop_20260525_205159_a0a765`.

Purpose: Close workflow accounting gap for corrected ChangeSet completion

Why it is needed: R045 was implemented through corrected ChangeSet chg_r045_corrected_task_coverage_manifest_schema and executor exec_20260525_204446_a06ee7, but the original workflow wf_20260525_203413_8036fd remains true_blocked because Abyss has no exposed/recognized way to classify a workflow completed by an applied corrected ChangeSet. Add the smallest governed status-accounting capability so summary/workflow accounting can classify such cases as superseded/completed-by-corrected-changeset without falsifying execution history or bypassing Owner/Harness.

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

### R047. Formalize Request Semantics / Rule Propagation V0 candidate patch

Source proposal: `evo_prop_20260526_003346_5b4a9f`.

Purpose: Formalize Request Semantics / Rule Propagation V0 candidate patch

Why it is needed: Formal intake for artifacts/drafts/candidate_patch_request_semantics_v0.md. Background: an external assistant directly changed source/rules/docs for Request Semantics / Rule Propagation V0 without the Abyss self-evolution workflow. Treat current source state as candidate material only, not as approved governance output. Classification: governance_mutation / meta_evolution_request because the patch touches request lifecycle semantics, governance routing, Context Broker selection, integrity checks, rules/contracts/schemas, and user-facing governance docs. Required old-rule review: use the rules accepted before the ungoverned candidate patch and before any new rule can legitimize itself. Scope to review: rules/request_types.v1.yaml, rules/contracts/request_envelope.v1.yaml, rules/schemas/request_envelope.v1.schema.json, abyss_cli/request_rules.py, abyss_cli/request_envelope.py, abyss_cli/__main__.py, abyss_cli/context_pack.py, abyss_cli/integrity.py, README.md, SYSTEM_MAP.md. Required decision: preserve useful candidate work through formal governance if it passes review, or quarantine/revert if it weakens governance. Risk assessment: prevents request_id from acting as semantic authority, adds explicit request_type semantics, but may expand governance surface and must not grant execution/approval authority. Owner authority impact: normalization and classification must grant no execution, approval, roadmap, or activation authority. Rollback plan: revert candidate patch commit(s) or apply a follow-up ChangeSet that removes request semantics files and integrations while preserving incident record. Validation plan: run python -m abyss_cli request types --all --json, request normalize/validate sample envelopes, request governance-core detection, python -m compileall -q abyss_cli, python -m abyss_cli check, python -m abyss_cli summary --check. Activation policy: if accepted, activate only as accepted governance in a later cycle after Owner approval, validation, and report; do not retroactively legitimize the original direct mutation. Required output: governance incident record, candidate patch review result, explicit Owner decision, and post-change report.

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

### R048. Implement Rule Source Registry and Consumer Contract V0

Source proposal: `evo_prop_20260526_005510_217e64`.

Purpose: Implement Rule Source Registry and Consumer Contract V0

Why it is needed: Owner decision after R047 blocked_result blk_20260526_005342_191fcc: preserve the useful Request Semantics / Rule Propagation V0 candidate patch as candidate material, do not quarantine/revert it, and create a bounded follow-up implementation to add the missing minimal Rule Source Registry + Consumer Contract mechanism. Scope: start from artifacts/drafts/candidate_patch_request_semantics_v0.md and existing request semantics files, then add a lightweight registry declaring rule sources, source files, affected scopes, consumers, context task inclusion, validation commands, and hard boundaries. Minimal target: add rules/rule_sources.v1.yaml, rules/contracts/rule_source_registry.v1.yaml, rules/schemas/rule_source_registry.v1.schema.json, a deterministic abyss_cli/rule_registry.py reader/validator, CLI commands to list/validate rule source registry, Context Broker integration so rule sources declared for a task type are automatically included in context packs, Integrity integration so missing registry files or invalid consumer contracts fail check, and README/SYSTEM_MAP documentation. Non-goals: no event bus, no daemon, no real-time propagation, no hot reload, no broad rule engine, no automatic approval/execution authority. Governance boundaries: registry grants no execution/approval authority; it only makes accepted rule sources discoverable and checkable. Validation plan: python -m abyss_cli rules list --json, python -m abyss_cli rules validate --json, python -m abyss_cli request types --all --json, python -m compileall -q abyss_cli, python -m abyss_cli check, python -m abyss_cli summary --check. Rollback plan: remove the new rule registry files and integrations via ChangeSet while preserving R047 incident record and candidate patch document. Activation policy: bounded implementation may be produced after this explicit Owner preserve decision; governance-core rule changes remain subject to Harness review and Owner approval before executor apply.

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

### R049. M001 integrity check structure maintenance

Source proposal: `evo_prop_20260526_014518_ccef53`.

Purpose: M001 integrity check structure maintenance

Why it is needed: request_type=maintenance_request; maintenance_kind=refactor; task_context=system summary health check maintenance; target_file=abyss_cli/integrity.py; allowed_modification=abyss_cli/integrity.py only; goal=extract focused helper functions from run_checks; preserve=public behavior, return value, message ordering, and command results; no_other_files_may_change=true; validation=python -m compileall -q abyss_cli; python -m abyss_cli check; python -m abyss_cli summary --check; rollback=revert this changeset if behavior differs

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

### R050. Unblock maintenance request target file context

Source proposal: `evo_prop_20260526_014755_878525`.

Purpose: Unblock maintenance request target file context

Why it is needed: request_type=maintenance_request; maintenance_kind=stability_hardening; observed_block=R049 Implementation Agent requested missing abyss_cli/integrity.py; target=Context Broker request coverage for maintenance_request target_file/target_module; goal=Ensure maintenance requests disclose explicitly declared target file before implementation; scope=smallest governed fix to context coverage only; validation=retry R049 or equivalent M001 workflow, python -m abyss_cli check, python -m abyss_cli summary --check; non_goal=do not complete full structured task detection refactor

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

### R051. M004 shared parser utility for agent output blocks

Source proposal: `evo_prop_20260526_094539_ae1b2b`.

Purpose: M004 shared parser utility for agent output blocks

Why it is needed: request_type=maintenance_request; maintenance_id=M-004; target_file=abyss_cli/fenced_blocks.py; callsite_files=abyss_cli/agent_runner.py,abyss_cli/patch_compiler.py,abyss_cli/changeset.py; objective=Create a small shared utility for parsing JSON from named fenced output blocks and wire these three call sites to it; scope=equivalent parser refactor only; non_goals=no status machine changes,no provider changes,no context pack changes,no policy changes,no broad formatting changes; acceptance=compileall passes,check passes,rules validate passes,summary check passes,embedded triple-backticks in JSON string values remain parseable

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

### R052. Meta M004 evolution analysis parser reuse

Source proposal: `evo_prop_20260526_095954_dfe38d`.

Purpose: Meta M004 evolution analysis parser reuse

Why it is needed: request_type=governance_mutation; meta_evolution_request=true; maintenance_id=M-004-meta; target_file=abyss_cli/evolution_analysis.py; dependency_file=abyss_cli/fenced_blocks.py; objective=Reuse the already existing shared fenced JSON parser for abyss-evolution-analysis and json fallback block extraction in evolution_analysis.py; reason=remove duplicated fenced JSON scanning/repair logic from self-evolution analysis parsing while preserving existing behavior; scope=parser utility import plus local extraction helper simplification only; non_goals=no approval gate changes,no permission boundary changes,no workflow state changes,no context disclosure changes,no roadmap rules changes,no policy changes,no activation behavior changes; risk=L3 governance-core-adjacent because file parses self-evolution agent output; rollback=git diff/manual revert of evolution_analysis.py only; validation=compileall, abyss check, rules validate, summary --check, regression parse abyss-evolution-analysis with embedded triple backticks and json fallback; activation_note=behavior-equivalent parser refactor effective only after normal Owner approval and Executor apply under prior rules

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

### R053. Diagnose and reduce corrected ChangeSet dependency in Implementation pipeline

Source proposal: `evo_prop_20260526_100807_55f571`.

Purpose: Diagnose and reduce corrected ChangeSet dependency in Implementation pipeline

Why it is needed: Focused maintenance request: diagnose why recent workflows increasingly require corrected ChangeSets instead of Implementation Agent generated executable ChangeSets. Scope: add or improve read-only/diagnostic instrumentation and minimal pipeline fixes for Context Broker -> Implementation Agent -> Patch Compiler failure classification. Must not continue unrelated source maintenance items M-004/M-002. Acceptance: system can report recent Implementation pipeline failure categories including context insufficiency, task_type misclassification, edit-plan JSON parse errors, symbol/anchor resolution failures, old_content match failures, Harness violations, provider empty/timeout, and expected governance blocks; any code change must be minimal and must preserve Harness/Owner/Executor gates.

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

### R054. Reduce Implementation pipeline symbol-resolution invalid ChangeSets

Source proposal: `evo_prop_20260526_104449_9247cd`.

Purpose: Reduce Implementation pipeline symbol-resolution invalid ChangeSets

Why it is needed: Scope: continue R053 corrected-ChangeSet dependency reduction only. Problem: recent diagnostics show symbol_resolution_failure remains the top invalid ChangeSet category, especially replace_symbol target too large and symbol/anchor resolution errors. Goal: make Patch Compiler/workflow return recoverable local_edit_context or precise retry guidance instead of terminal invalid ChangeSet when replace_symbol targets are too large, without broadening permissions or touching unrelated source-maintenance items. Acceptance: summary diagnostics still pass; compileall/check pass; a large replace_symbol failure can be classified as context_insufficient/recoverable rather than true failure where safe.

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

### R055. Reduce edit-plan parse and missing-edits invalid ChangeSets

Source proposal: `evo_prop_20260526_105510_cb24a9`.

Purpose: Reduce edit-plan parse and missing-edits invalid ChangeSets

Why it is needed: Scope: continue corrected-ChangeSet dependency reduction only. Problem: implementation_pipeline_diagnostics still shows edit_plan_parse_error=6 and missing_edits=6 historical failures. Goal: improve deterministic handling when Implementation Agent output cannot be parsed as abyss-edit-plan or contains no edits: preserve parse diagnostics, classify as recoverable context/format feedback where safe, and provide explicit retry guidance instead of opaque MISSING_EDITS. Out of scope: M-004/M-002, governance policy changes, prompt rewrites, broad refactors, or permission expansion. Acceptance: compileall/check/summary --check pass; invalid edit-plan records include useful diagnostics/retry guidance; normal valid edit-plan parsing remains unchanged.

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

### R056. R056 improve invalid edit-plan retry feedback

Source proposal: `evo_prop_20260526_125246_510b2d`.

Purpose: R056 improve invalid edit-plan retry feedback

Why it is needed: Maintenance request for Implementation pipeline diagnostics. Target: invalid edit-plan outputs where anchor text does not match or generated content contains placeholders. Improve parse diagnostics and retry guidance in patch_compiler.py and agent_runner.py so the next implementation attempt receives actionable feedback: choose an exact unique anchor visible in context, request local edit context if no safe anchor is visible, and replace placeholder text with complete concrete code. No broad refactor.

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

### R057. R057 smoke verify invalid edit-plan feedback recovery

Source proposal: `evo_prop_20260526_131023_f00670`.

Purpose: R057 smoke verify invalid edit-plan feedback recovery

Why it is needed: Probe/smoke request for the Implementation pipeline. Verify that after R056, recoverable invalid edit-plan feedback for placeholder content and anchor mismatch can be consumed by the next implementation attempt. Acceptance: run through the governed workflow path; if the first attempt emits placeholder content or a bad anchor, the invalid ChangeSet must carry recovery_classification and retry_guidance, a recoverable feedback/context request must be produced, and a later attempt must either produce a valid ChangeSet or block with a clearly classified non-placeholder reason. This is a diagnostic probe only; avoid broad refactor.

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

### R058. R058 runtime probe: forced invalid-output retry recovery

Source proposal: `evo_prop_20260526_131706_950818`.

Purpose: R058 runtime probe: forced invalid-output retry recovery

Why it is needed: Create a governed runtime probe that forces the workflow to exercise invalid ImplementationAgent output recovery, rather than merely inspecting existing fields. Acceptance: (1) the probe must create or invoke a controlled workflow path that intentionally produces at least one invalid edit-plan containing placeholder content or a bad anchor; (2) the invalid ChangeSet must be recorded with recovery_classification and retry_guidance; (3) the workflow must emit a recoverable feedback/context request or equivalent retry event tied to that invalid ChangeSet; (4) a subsequent workflow attempt must consume that feedback and either produce a valid ChangeSet/done path or block with a clearly classified non-placeholder reason; (5) reporting must show the exact workflow id, invalid changeset id, retry/context request id, and final status. This is a diagnostic probe/smoke item, not a broad refactor. Do not satisfy this request by static code inspection or by citing prior invalid changesets only.

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

### R059. R059 make placeholder format_feedback actionable

Source proposal: `evo_prop_20260526_133320_1c209f`.

Purpose: R059 make placeholder format_feedback actionable

Why it is needed: Narrowly improve Implementation Agent retry behavior after placeholder format_feedback. R058 proved that invalid ChangeSets and context_requests carry retry_guidance into the next Prompt Package, but the Agent still repeated placeholder output such as 'existing code'. Acceptance: (1) when recent context_request/retry evidence has request_kind=format_feedback and placeholder retry_guidance, the next Implementation prompt must present it as a hard corrective constraint, not passive evidence; (2) the prompt must explicitly require a fresh concrete edit-plan and forbid copying prior failed placeholder operations or using markers such as existing code, placeholder, omitted, ellipsis, TODO, other code unchanged; (3) include a focused runtime or compile-level regression check that demonstrates placeholder feedback is rendered in the corrective section of the prompt package; (4) do not change governance policy, external interfaces, owner approval rules, or broad prompt architecture; this is a bounded implementation-pipeline reliability fix.

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

### R060. R060 deterministic repeated-placeholder handling

Source proposal: `evo_prop_20260526_135427_d8376b`.

Purpose: R060 deterministic repeated-placeholder handling

Why it is needed: Narrow reliability fix for Implementation pipeline. R058/R059 proved placeholder format_feedback and mandatory corrective prompt rendering can be recorded and carried forward, but Implementation Agent may still repeat placeholder edit-plan output after receiving placeholder retry_guidance. Acceptance: (1) when a workflow emits a placeholder-related format_feedback context_request and later emits another placeholder-related format_feedback context_request for the same workflow, classify it deterministically as repeated placeholder output instead of a generic context-insufficient loop; (2) record the current context_request_id and prior placeholder context_request ids in workflow history; (3) summary diagnostics expose a repeated_placeholder_output category while keeping health checks clean; (4) no governance policy, external interface, owner approval, executor, or broad prompt architecture change.

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

### R061. R061 source maintenance: add deterministic placeholder preflight in edit-plan handling

Source proposal: `evo_prop_20260526_142327_6d6e66`.

Purpose: R061 source maintenance: add deterministic placeholder preflight in edit-plan handling

Why it is needed: Request type: source maintenance. Target files: abyss_cli/agent_runner.py and abyss_cli/patch_compiler.py only. Goal: add a deterministic preflight around edit-plan handling so placeholder-like edit operations are rejected with a clear reason before invalid ChangeSet import. Non-goals: do not modify prompts, rules, governance policy, context manifest, owner approval, harness permissions, workflow states, ROADMAP, or external-client behavior. Acceptance: python -m compileall abyss_cli passes; python -m abyss_cli check passes; python -m abyss_cli summary --check remains green; one minimal runtime probe or existing callable demonstrates placeholder edit-plan rejection before ChangeSet import; R060 repeated-placeholder behavior is preserved.

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

### R062. R062 narrow: patch_compiler anchor failure diagnostics only

Source proposal: `evo_prop_20260526_144826_4993a3`.

Purpose: R062 narrow: patch_compiler anchor failure diagnostics only

Why it is needed: request_type=maintenance_request; maintenance_kind=stability_hardening; target_file=abyss_cli/patch_compiler.py; allowed_modification=abyss_cli/patch_compiler.py only; observed_from=R061 second attempt anchor match count 0 and oversized replace_symbol patterns; objective=improve deterministic classification and retry diagnostics for anchor match count and replace_symbol target too large inside Patch Compiler invalid ChangeSet records; scope=small changes to existing error strings/recovery classification/parse_diagnostics only, preserving existing edit-plan compilation behavior; non_goals=no context_pack,no agent_runner,no prompts,no rules,no workflow,no governance policy,no new disclosure,no broad refactor,no permission expansion,no local context extraction; acceptance=python -m compileall -q abyss_cli,python -m abyss_cli check,python -m abyss_cli summary --check,probe bad replace_anchor returns recoverable context_insufficient with retry guidance naming exact unique anchor requirement,probe large replace_symbol remains recoverable with smaller-anchor guidance; risk=L2

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

### R063. R063 maintenance request coverage classification fix

Source proposal: `evo_prop_20260526_151258_da552a`.

Purpose: R063 maintenance request coverage classification fix

Why it is needed: request_type=maintenance_request; target_file=abyss_cli/context_pack.py; allowed_modification=abyss_cli/context_pack.py only; objective=ensure maintenance_request target_file drives coverage classification before generic keyword matching so single-file maintenance proposals do not inherit unrelated summary or agent manifests; scope=classification and advisory coverage metadata only; non_goals=no workflow change,no agent change,no prompt change,no governance policy change,no executor change,no permission expansion; acceptance=single-file maintenance request for abyss_cli/integrity.py includes integrity.py as target coverage and does not list unrelated agent or summary files; standard health checks pass; risk=L2

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

### R064. R064 integrity.py helper extraction only

Source proposal: `evo_prop_20260526_152546_a1df1a`.

Purpose: R064 integrity.py helper extraction only

Why it is needed: request_type=maintenance_request; target_file=abyss_cli/integrity.py; allowed_modification=abyss_cli/integrity.py only; objective=move one existing validation block from run_checks into a private helper in the same file; scope=behavior-preserving single-file refactor; non_goals=no behavior change,no schema change,no other files; acceptance=compileall abyss_cli,abyss check,abyss summary check,only integrity.py changed; risk=L2

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

### R065. R065 provider empty response diagnostics

Source proposal: `evo_prop_20260526_152939_1a3086`.

Purpose: R065 provider empty response diagnostics

Why it is needed: request_type=maintenance_request; target_file=abyss_cli/llm_executor.py; allowed_modification=abyss_cli/llm_executor.py only; objective=improve provider empty stdout or empty response diagnostics so workflow failures expose provider name, interface, attempt count, and whether stdout was empty after filtering without changing provider behavior; scope=diagnostic-only single-file maintenance; non_goals=no provider config change,no model change,no retry policy change,no workflow state change,no prompts,no rules,no external interface expansion; acceptance=python -m compileall -q abyss_cli,python -m abyss_cli check,python -m abyss_cli summary --check,empty response errors remain failures but include clearer diagnostic text; risk=L2

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
