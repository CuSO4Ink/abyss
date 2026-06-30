# Real-Provider Agent Workflow Smoke/Probe — RE-TEST — 2026-06-01

scope: real-provider agent workflow smoke/probe (re-test after anchor contract fix)
expected_output: 测试报告、调用记录、失败分类、是否到达 owner gate

本目录是「真实 provider 端到端探测」的第二次执行（重测）。与首次探测
(artifacts/drafts/real_provider_probe_20260601) 相比，本次代码库已包含一组新提交：

- 96f4ca7 Align edit-plan anchor contract        <- 关键：修复首次探测暴露的 anchor 契约歧义
- d50c48d Harden self-iteration governance and implementation prompts
- 374c284 docs: archive inactive roadmap items   <- ROADMAP 302 行 -> 510 行

探测目的不变：用虚构的只读 helper 需求真正喂给 implementation agent，
deepseek 与 claude 各跑一遍，看流程能否推进到 owner gate，全程不 approve / 不 apply。

## 两轮真实模型调用结果对照（本次）

| 维度 | deepseek (v4-pro) | claude (cli / 4.6-opus) |
|---|---|---|
| Workflow | wf_20260601_220123_9faa9c | wf_20260601_220318_353a14 |
| Roadmap (临时, 已回退) | R085 | R086 |
| 真实模型调用 | 是 (~38s) | 是 (~13s) |
| edit-plan anchor 写法 | 顶层 anchor（正确） | replace/append（正确） |
| 编译成 changeset | 成功 (valid) | 成功 (valid) |
| dry-run | passed (MATCH_COUNT=1) | passed (MATCH_COUNT=1) |
| harness 审查 | 通过 | 通过 |
| 是否到达 owner gate | 是 | 是 |
| 最终状态 | rejected（我们主动收尾） | rejected（我们主动收尾） |

## 与首次探测的关键差异（最重要结论）

首次探测中 deepseek 因 EDIT_PLAN_CONTRACT_MISSING_ANCHOR 失败：它把 anchor 写进了
target 对象 ("target": {"path": "...", "anchor": "..."})，而校验取的是 edit 顶层 anchor。

本次 deepseek 的原始产出（deepseek_raw_output_anchor_FIXED.md）显示，anchor 已放在
edit 顶层：

    {
      "id": "op_001",
      "kind": "append_after_anchor",
      "target": {"path": "abyss_cli/utils.py"},
      "anchor": "    return proc.returncode == 0\n",
      "new_content": "..."
    }

=> 提交 96f4ca7 "Align edit-plan anchor contract" 的修复生效。首次探测暴露的
   会反复绊倒不同模型的 anchor 位置歧义，本次未再复现，deepseek 顺利跑通。

## 健康路径（两个 provider 本次均一致）

implementation_pending -> implementation_running -> changeset_proposed
-> dry_run_passed -> harness_review_running -> waiting_owner_approval

实证再次确认：真实模型驱动下，除 owner 审批这个设计内人工卡点外，流程不卡死，
不会自动 apply；dry-run 全程只读 (no_action_executed=true)。

## 安全与清理记录

- git HEAD 基线：96f4ca7（探测前后未变）。
- 真实 ROADMAP.md：基线 510 行，探测中临时增至 558（R085/R086），探测后 git checkout 回退到 510。
- 源码：零改动。
- approve/apply：全程未执行；两轮均停在 gate 后由我们主动 owner reject 收尾，
  reject 只改状态不 apply 任何文件。
- 两个 workflow 均进终态 rejected，无悬挂项。
- 本次 .local/runtime 运行记录在归档关键证据后被清理。

## 归档文件清单

- deepseek_raw_output_anchor_FIXED.md  deepseek 原始产出（anchor 已修正，决定性证据）
- claude_raw_output.md                  claude 原始产出
- deepseek_valid_changeset.yaml         deepseek 的 valid changeset
- claude_valid_changeset.yaml           claude 的 valid changeset
- deepseek_workflow.yaml                deepseek workflow 完整记录
- claude_workflow.yaml                  claude workflow 完整记录
