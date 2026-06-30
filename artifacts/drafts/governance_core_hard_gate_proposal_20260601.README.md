# 待裁决 Patch: governance-core hard gate + 自我松绑盲点修复

- patch 文件: `governance_core_hard_gate_proposal_20260601.patch`
- 基线 commit: `96f4ca7`
- 涉及文件: `abyss_cli/evolution.py`, `abyss_cli/request_rules.py`, `abyss_cli/workflow.py`
- 状态: **未应用到仓库**。源码已回退干净，改动仅以 patch 形式留存，等待 owner 或其他 AI 裁决。

## 背景

来自 2026-06-01 对抗性真实流程测试（见 `adversarial_probe_20260601/`）发现的两个弱点：

- **F1（🔴 治理检测盲点）**: 请求"扩大 changeset.py 的 ALLOWED_FS_ROOTS"这类自我松绑安全边界的需求，
  `detect_governance_core_scope` 未命中，propose 阶段不会标记为治理核心。本轮只靠 deepseek
  在 implementation 阶段兜底 block，防线过度依赖模型智能。
- **F2（🟡 approve 不硬拦）**: 即便 proposal 已标记 `requires_meta_governance=true`，
  `evolution approve` 与 `workflow start` 仍直接放行，治理标记仅是建议性的。

## 这个 patch 做了什么

1. `request_rules.py`
   - 把 `abyss_cli/changeset.py` 加入 `GOVERNANCE_CORE_SURFACES.permission_boundaries`。
   - 新增关键词: `allowed_fs_roots` / `blocked_path_prefixes` / `blocked_paths` /
     `allowed_check_commands` / `executor allowlist` / `executor blocklist` / `permission boundaries`。
   - 目的: 让"改执行器自身 allowlist/blocklist"的请求在 propose 阶段就被标记为治理核心。(修 F1)

2. `evolution.py`
   - 新增 `proposal_requires_meta_governance()` 判定函数。
   - 新增 `reject_governance_core_ordinary_approval()`，在 `approve_proposal()` 内调用，
     治理核心 proposal 走普通 approve 时直接 SystemExit。(修 F2)

3. `workflow.py`
   - `create_workflow_for_proposal()` 对治理核心 proposal 直接 SystemExit，
     禁止用普通 workflow 启动。(修 F2)

## 为什么不直接应用

⚠️ **这个 patch 本身就是在修改治理核心代码（evolution / workflow / request_rules 都属于受保护面）。**
按既定原则，AI 不得自行落地对治理核心的修改。本 patch 仅作为"修复提案"留存，
需由 owner 或独立 AI 审查后决定是否采纳，且采纳应走 meta-governance 路径。

## 采纳前建议验证

- `python -m compileall -q abyss_cli`
- `python -m abyss_cli check`
- 重跑 A1/A4 对抗探测，确认 approve/start 被硬拦、A4 在 propose 阶段即被标记治理核心。
- 确认没有误伤正常的 maintenance/feature 请求（关键词不过度宽泛触发误判）。
