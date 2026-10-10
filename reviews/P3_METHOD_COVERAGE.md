# P3 原作者方法覆盖（施工状态）

固定来源：CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。本报告以本机按字节捕获的 `runtime/reference/cnw_97ad71fe5e5e/CNW_LOCAL_REFERENCE_MANIFEST.json` 为原件目录；manifest SHA256 为 `E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`，共 98 项。P3 工单包 SHA256 为 `E3D4E10B7C876A2F4F53B0BFC5560BB24419F975D4A88445FAED993A66BE3CAD`；包内 10 个文件的 SHA256 与 `MANIFEST_SHA256.txt` 一致。捕获过程无供应商请求，固定上游未修改；引用目录受 `.gitignore` 的 `/runtime/` 规则保护。

## 方法到项目职责

除标明已有证据外，施工状态先标 `NOT_IMPLEMENTED`。P2 的历史产物与工具调用不被冒充为 P3 正式流程；W00 原件捕获不代表其他阶段已实现。

| 原作者阶段 / 方法 | 固定源文件 | StoryStudio 对应职责 | 当前状态 | 目标验证 |
|---|---|---|---|---|
| 项目、Arc、Canon、Style 导入与持续维护 | `docs/EXISTING_PROJECT_IMPORT.md`; `templates/_workflows/01_first_import.md`; `templates/_workflows/02_incremental_update.md` | 支持任意私有项目根，维护来源与知识边界 | `NOT_IMPLEMENTED`（仅《苍歧》P2 固定导入存在） | A04、B01、E05 |
| Plot 规划 | `templates/config/ai_roles.template.yml`; `templates/06_plot/plot.template.md` | 独立 Plot 输入/输出、作用/Hook/节拍/长度合同 | `PARTIAL`：W04 Prompt/角色包/结构 gate 已实现；尚无新 run 的真实 Plot 角色结果 | B01、B04、D02 |
| Plot 的 CritiCS 项目扩展 | P2 `tools/critics_bridge.py`; `tools/p2_06_critics_run.py` | 原桥接的计划批评接入，结果不能代替 CNW Plot Lens | `PARTIAL`：既有 P2 live 证据可复用；W04 新 run 安全调用构造器已实现，尚未真实调用新 Plot | D04 |
| Scene Cards | `templates/05_scene_cards/scene_cards.template.md`; `ai_roles.template.yml` | 由已接受 Plot 生成多场或单场合同、起止与预算 | `PARTIAL`：W04 Prompt/角色依赖/beat 与预算 gate 已实现；尚无新 run 的真实 Card 角色结果 | B01、B04、B05 |
| Writing Brief | `templates/07_draft/writing_brief.template.md`; `ai_roles.template.yml` | 从 Plot/Card/当前 Canon/声线导出冻结写作合同 | `PARTIAL`：W04 Prompt/隔离输入包/beat 与长度 gate 已实现；尚无新 run 的真实 Brief 角色结果 | B01、B06 |
| NK POV hook | P2 `tools/p2_06_nk_live_probe.ps1`; NK 固定路由 | 当前 Card 到 NK 现有接口，反思结果映射入 Brief | `PARTIAL`：W04 按冻结 beats 构造 ordered `eventSequence`，且 Brief 映射需 receipt；本新合同尚未真实调用 | B06、E09 |
| Prose | `ai_roles.template.yml`; `templates/07_draft/writing_brief.template.md` | 仅用 Brief 和相关声线生成新 ID 正文、保存 v0 | `PARTIAL`：W04 Prompt/Brief+声线输入限制与长度 gate 已实现；无 Controller 接受的 Plot/Card/Brief 时禁止构造 Prose 包 | B06、B07、C01、C06 |
| Layer 1 表层校验 | `docs/THREE_LAYER_REVIEW.md` | 中文项目 lint，定位问题而不自动删文 | `NOT_IMPLEMENTED` | C09、D02 |
| Layer 2 结构校验 | `docs/THREE_LAYER_REVIEW.md` | 以上下文发现摘要化、重复等结构候选 | `NOT_IMPLEMENTED` | C03、C09、D02 |
| 5 个独立 Lens | `docs/THREE_LAYER_REVIEW.md`; `templates/config/workflow.template.yml` | Style/Character/Plot/Canon/Story-specific 隔离输入与记录 | `NOT_IMPLEMENTED`（工程 Controller/CritiCS 不等价） | D01、D02、D09、D10 |
| 3 个对抗 Verifier | `docs/THREE_LAYER_REVIEW.md`; `workflow.template.yml` | 三个独立上下文、优先反证及明确保留阈值 | `NOT_IMPLEMENTED`（CritiCS Inspector 不等价） | D03、D10 |
| Completeness Critic | `docs/THREE_LAYER_REVIEW.md` | 独立检查整场/节拍/审查类别遗漏 | `NOT_IMPLEMENTED` | C01、D05、D09 |
| Revision Plan / Refine | `templates/09_revision/revision_plan.template.md`; `revision_log.template.md`; `templates/_workflows/03_revision.md` | 按确认 issue 修订，保护 v0 与必需节拍 | `NOT_IMPLEMENTED`（P2 有一次性修订样本） | C04、C05、D06 |
| Re-review | `docs/THREE_LAYER_REVIEW.md`; `_workflows/03_revision.md` | 对受影响的 Review 角色复核完整新稿 | `NOT_IMPLEMENTED` | D07 |
| Promote / Manuscript Index | `templates/_workflows/03_revision.md`; `docs/ARCHITECTURE.md`; `templates/07_draft/episodes/README.md` | Controller 接受后晋升单一正本并更新索引 | `NOT_IMPLEMENTED` | D08 |
| 导出阅读版 | `templates/93_exports/README.md`; P2 `tools/studio.ps1` | 根据 run manifest 动态导出而非 EP001 硬编码 | `NOT_IMPLEMENTED`（旧 EP001 导出可复用作历史） | E07、E08 |
| 五话 Sprint 与 handoff | `templates/08_review/batch_review.template.md`; `_workflows/05_handoff.md` | 离线队列、批次审查及状态接续 | `NOT_IMPLEMENTED` | E02 |
| 费用与供应商 | P2 `tools/p2_cost_guard.py`; `tools/p2_06_critics_run.py` | 复用现有预算和 reserve/settle，不建第二账本 | `ALREADY_IMPLEMENTED_WITH_EVIDENCE`：账本/请求护栏存在；新调度器尚未接入 | E03、E04、E05 |

## 捕获与审阅边界

- `tools/capture_cnw_reference.py` 只读 pinned submodule 的固定文档/模板与指定本地方法实例；脚本逐项核对 commit、Git blob、源/目标 SHA256，不下载或修改上游。
- 捕获记录证明本地原件可读、版本可复核；独立 Controller 仍需亲自读取工单指定完整原文并对 W00 签收。
- 作者实例仅作为字段粒度和方法样例，不将其人物、Canon、正文迁入《苍歧》。
- 源文件、用户文本、运行日志与完整模型响应留在 Git 忽略路径。公开仓只保存方法映射、代码和脱敏验收记录。

## 执行时必须保留的来源差异

- 原项目单话 rubric 的示例通过线是 80 分；通用 `workflow.template.yml` 的 Sprint `min_score` 是 75。项目配置必须明确选定适用阈值，并继续执行致命项一票否决，不能把两处数字写成同一个上游硬规则。
- 作者方法把 Lens 的 `pass / revise / rewrite` 用作后续动作判断；Sprint 示例、单话 rubric、handoff 对 revise/rewrite 的停止时点存在上下文差异。P3 执行配置要明确当前 StoryStudio 采用的门和下一状态，不能模糊地说“失败后继续”或声称上下文完全相同。
- 原作者公开的是工作方法、模板和示例，并未公开可直接复刻的内部专用多 Agent 执行器。P3 实现应称为固定来源的项目适配，不宣称复现原作者私有执行器、并行性能或读者成绩。
