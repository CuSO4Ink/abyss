# Real-Provider Agent Workflow Smoke/Probe — 2026-06-01

scope: real-provider agent workflow smoke/probe
expected_output: 测试报告、调用记录、失败分类、是否到达 owner gate

本目录是一次「真实 provider 端到端探测」的证据归档。探测目的：用一个虚构的小型
maintenance 需求（给 abyss_cli/utils.py 增加一个只读 helper `demo_hello_banner`）
真正喂给 implementation agent，分别用 deepseek 和 claude 各跑一遍，观察自迭代流程
在真实模型驱动下能否推进到 owner gate，全程不 approve、不 apply。

## 两轮真实模型调用结果对照

| 维度 | deepseek (v4-pro) | claude (cli / 4.6-opus) |
|---|---|---|
| Workflow | wf_20260601_205624_ce11a2 | wf_20260601_205831_a6ae27 |
| Roadmap (临时, 已回退) | R085 | R086 |
| 真实模型调用 | 是 (~34s) | 是 |
| 产出 edit-plan | 格式合法 JSON | 合法 |
| 编译成 changeset | 失败 (invalid) | 成功 (valid) |
| 失败原因 | EDIT_PLAN_CONTRACT_MISSING_ANCHOR | 无 |
| dry-run | 未到 | passed |
| harness 审查 | 未到 | verdict=ok |
| 最终状态 | failed | rejected (我们主动拒绝收尾) |
| 是否到达 owner gate | 否 | 是 (waiting_owner_approval) |

## 关键结论

1. claude 完整跑通健康路径并精确停在人工闸门：
   implementation_pending -> implementation_running -> changeset_proposed
   -> dry_run_passed -> harness_review_running -> waiting_owner_approval
   实证验证：真实模型驱动下，除 owner 审批这个设计内人工卡点外，流程不卡死，
   且不会自动 apply。

2. deepseek 暴露了一个真实的「edit-plan schema 契约对齐」问题（重要）：
   - deepseek 把 anchor 写在 target 对象里：
       "target": {"path": "...", "anchor": "..."}
   - 但系统契约 (patch_compiler.py 第 152 行附近) 取的是 edit 顶层的 anchor：
       edit.get("anchor")
   - 取不到 -> 判定 MISSING_ANCHOR -> invalid changeset。
   - claude 改用 replace_anchor + 完整 old_content 块的写法，恰好绕过该陷阱。
   说明：edit-plan 对 anchor 位置的约定存在歧义，不同模型直觉不同，
   会导致「格式正确的产出」仍被判 invalid。

3. 失败被系统正确归类为可恢复 (format_feedback)，且 no_action_executed=true，
   invalid changeset 不执行任何动作。再次印证：系统瓶颈在「上游模型产出/格式对齐」，
   不在流程编排本身。

## 安全与清理记录

- 真实 ROADMAP.md：R085/R086 临时条目已 git checkout 干净回退（恢复 302 行）。
- 源码：除用户单独保留的 patch_compiler.py 改动外，零改动。
- approve/apply：全程未执行；claude 那轮停在 gate 后由我们主动 owner reject 收尾，
  reject 只改状态不 apply 任何文件。
- 两个 workflow 均进终态：claude=rejected，deepseek=failed，无悬挂项。
- 本次探测的 .local/runtime 运行记录在归档本目录关键证据后被清理。

## 建议（下一阶段，未擅自执行）

修复 edit-plan 的 anchor 位置歧义：要么让校验同时接受 edit["target"]["anchor"]，
要么在 implementation prompt 里把「anchor 必须放 edit 顶层」写死，
否则 deepseek 这类模型会反复栽在同一个坑。

## 归档文件清单

- deepseek_raw_output_MISSING_ANCHOR.md  deepseek 原始模型产出（缺 anchor 那份）
- claude_raw_output_reached_gate.md      claude 原始模型产出（跑到 gate 那份）
- deepseek_invalid_changeset.yaml        deepseek 的 invalid changeset 记录
- claude_valid_changeset.yaml            claude 的 valid changeset 记录
- deepseek_workflow.yaml                 deepseek workflow 完整记录
- claude_workflow.yaml                   claude workflow 完整记录
