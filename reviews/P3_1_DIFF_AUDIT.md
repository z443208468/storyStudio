# P3.1 对既有 W00–W05 的差异审计

状态：**修复候选，待同一独立 Controller 补验；不是 W06 签收。**

## 基线与权限

- P3.1 工单包 SHA256：`2550F43B266BFDCAC324F9C24E4DCC7E86B6AA38462B32310A203F54BD6FFDF3`；包内 12 项 manifest 校验全部通过。
- 审计基线本地 `main` C=`9464165c69825aaa01fefee83f019dd69b52e877`、T=`6eb7cd167ae159608375b28ba5815a4bfa7c79ff`；远端 `origin/main` 同 C。CNW、CritiCS、NK pins 与既有状态记录一致。
- 独立 Controller 首轮差异审查确认：W00–W03 可沿用历史验收；P3.1 W04/W05 不能沿用为新剧本导入已完成的证据。Controller 未审 W06 文件。
- P3.1 包内要求创建候选分支，与用户此前明确的“只要一个 main、不要分支”冲突。本工程继续只在 `main` 上增量工作，既不创建分支，也不强推、reset、clean 或删改既有历史。
- P3.1 作为当前活动施工合同，旧 `plans/MASTER_PLAN_P3.md` 保留为旧版历史；包内活动文件已逐字节复制并保留原 SHA，见 `AGENTS.md`。

## 差异与本次候选修复

| P3.1 项 | 原 W00–W05 事实 | 候选修复 / 当前证据 | 状态 |
|---|---|---|---|
| W04 / M04 新剧本导入 | `studio.ps1 import-source` 只验证固定《苍歧》包；不存在通用 `cnw_project.py`；角色输入限于 `workspace/cangqi` | 新增 `tools/cnw_project.py`：初始化私有项目、导入 UTF-8 `.md/.txt/.json`、保存原文件 SHA/字节/路径、行号或 JSON Pointer、source manifest/index、Canon 候选均为 `TODO_CONFIRM`；由显式人工输入生成 source-bound 合同草案 | 候选；两种格式链路测试通过，待 Controller |
| W04 → W05 数据贯通 | runner 固定按《苍歧》 release 目录验源；Studio 把 `ProjectRoot` 当代码根 | runner/角色包支持项目内 imported source identity；`studio.ps1` 从脚本位置推导仓库根、将 `ProjectRoot` 限定于 `workspace/<project>`，新增 `project-init/project-import/project-contract`，`produce` 使用导入项目合同和项目私有 runs 目录 | 候选；Python 集成测试和实际 PowerShell CLI 均通过，待 Controller |
| 两个原始剧本 | 旧测试从预制《苍歧》合同开始，不能证明导入器 | `tests/test_cnw_project_import.py` 实际导入不同 `.md` 与 `.json` 原件，核对独立 source SHA、索引定位、Canon 候选、source anchor、合同 hash、Plot/Brief role input hash，再从 Studio runner 创建各自 offline run | 候选；`MOCK_ONLY`、零模型调用 |
| 外部 Controller / promote | W05 的阶段 fixture 可记为 ACCEPTED，`review` 只回 `REVIEW_REQUIRED`，promote 没有明确外审证据门 | 离线阶段请求不能注册为 editorial candidate；仅非 fixture 的 live run 且 `verify_live` 通过完整请求/usage/hash/费用结算检查后，才可标 `READY_FOR_EDITORIAL_REVIEW`；promote 另要求外部审阅证据，CLI 不自签 | 候选；拒绝门测试通过 |
| W07 与 W10 | W05 live fail-closed；`verify_live` 只查请求列表非空 | W07 明确 `MOCK_ONLY`，不得有 provider ID 或冒称 live；W10 receipt 必须逐请求含独立 ID、DeepSeek Flash、HTTP/`stop`、usage、输入/输出 SHA、run 内原始响应文件及 SHA，并与现有 P2 ledger 中唯一 `SETTLED` 行、provider ID、usage、finish reason、结算金额相符；mock 记录会被拒 | 候选；mock 排除通过。真实 W10 未运行，必须等 W00–W09 门通过 |
| 分支治理 | 当前唯一 branch 是 `main`，本地/远端一致 | 遵循用户明确授权；不按 P3.1 包内规则创建候选分支 | 已按用户权限确定，不是 P3.1 候选分支流程已执行 |

## 验证

- `python -m unittest discover -s tests -v`：38 tests，全部通过（本轮完整 suite 包含历史 W00–W05、W06 未签收候选测试和 P3.1 导入差量测试）。
- PowerShell parser 检查 `tools/studio.ps1`：无语法错误。
- 实际 PowerShell：`project-init`、`project-import`、`project-contract` 与新项目 `produce -Mode offline -ProjectRoot workspace/P31CLI` 成功；run 位于该项目私有 `runs/`，返回 `provider_call=none`。测试工作区已移除。
- 未调用 DeepSeek/NK/CritiCS API；无新增费用；真实 W10 `NOT_RUN`。
- `git diff --check`、Python compile 与最终候选 C/T 将在 Controller 补验包中更新。

## 阶段决定

历史 W00–W05 ACCEPT 记录不变。P3.1 对 W04/W05 的新增功能目前是**本地候选**，须同一 Controller 对代码、测试、真实 CLI 行为和精确候选 C/T 补验签收。补验之前 W06 正式签收保持暂停；新剧本导入离线事实不等于 Canon 获确认、不等于模型写作或生产系统完成。
