# CNW Chapter 与 Arc 完成审查

固定依据：CNW `97ad71fe5e5e` 的 `docs/ARCHITECTURE.md`、`templates/config/workflow.template.yml`、Arc 模板及示例生产手册的「部単位チェック」。示例作品人物、20 话长度与其评分轴不是本项目规则。

## 执行

`produce -Unit episode` 的普通 11 阶段支持 Plot 决定的多个有序场景。Prose 只消费 Brief 和选中声线；Refine 使用整章范围和确认问题。新 V2 明确冻结 `unit.length_policy=ADVISORY`：保留用户目标和上下参考值，超出参考范围不触发纯长度续写、重写或拒绝。Completeness 查出的真实遗漏仍进入修订和新稿复审，不能靠新增无关事件补字数。旧无该字段合同保留原有长度/容量及续写恢复语义；不改旧合同、请求或阶段收据。传输截断、token/费用上限及空产物仍是独立硬门。

```powershell
pwsh -NoProfile -File tools/studio.ps1 arc-review -ProjectRoot '<selected absolute project root>' -ArcRef 04_chapter_design/arc_01.md -LastEpisode ep020
pwsh -NoProfile -File tools/studio.ps1 sprint -Mode live -ProjectRoot '<selected absolute project root>' -SprintId SPRINT01 -SprintPlan '<explicit plan path>'
```

Arc `## Range` 用实际项目的两个同前缀、同位宽端点（例如 `ep001 – ep020`）。只有明确处于范围中且未到末话时跳过 Arc-end review。完成时读取该 Arc 全部实际正文，包括以前 Sprint，及计划、细纲、Canon、项目目标与审稿资料；写入 `08_review/arc_NN_review.md`。Canon 更新只列候选；独立入口生成并归档一次交接。

五话 Sprint 在任何生产前核五份合同的所属 Arc 与范围。未知/缺失/歧义范围、范围外话号或跨 Arc 批次明确拒绝。剩余不足五话时用普通逐话入口完成当前 Arc，然后运行 Arc review，才能准备下一 Arc。每话及批量审稿通过不替代 Arc 完成审查。批量报告/当前稿先保存，适用时 Arc review 再进入同一次 Sprint handoff；Arc `revise` 保持 `REVISION_REQUIRED`。不会自动开始下一 Arc/Sprint，也不代签用户创意接受。

上述是接口示例，不在文档核对中执行。生产须通过当前可信签收及独立 Owner Live/费用门；`EPISODE_LIVE_NOT_RUN / SPRINT_LIVE_NOT_RUN` 保留。当前完整三类项目与五话 Sprint 产品回归属于待执行的09，不把旧样本测试重新写成当前09接受。
