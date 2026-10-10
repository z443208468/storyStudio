# C10/C14 Chapter 与 Arc 有限验证

日期：2026-10-11。固定官方来源和操作说明见 `docs/CNW_CHAPTER_ARC.md`。本增量没有付费调用或新增生产正文。

## 改动与消费者

- 普通 Chapter 的 Plot → Cards → Brief → Prose → 五 Lens/反证/Completeness → Refine → 受影响 Re-review 实际函数运行；测试只替换 provider、NK/CritiCS 边界，不替换岗位执行器。两场顺序、续写、Refine 整章容量、过短恢复携带基稿/Brief，以及不变身份重入均有断言。
- `cnw_arc.py` 按项目 Range 选择完整实际 Arc；`cnw_maintenance.py` 读完整固定方法、全范围正文和项目资料，实际生成七节 pass/revise 审查，Canon 不改，既有交接字节归档。重复执行复用成功回执。
- 五个不同 Episode 的 Sprint orchestration 生产边界被 mock；真实 Arc executor/provider receipt 消费正常执行。旧 Sprint ep000 与本批 ep001–ep005 进入同一次 Arc review。批量 PASS 而 Arc revise 的总结果仍待修订。
- 独立 Controller 最初 RETURN：只检查末话会漏跨 Arc 审查、未知边界被吞错。按最小修复选项增加生产前全批范围核验，跨 Arc/缺失/歧义/未知明确拒绝。合法中 Arc 可跳过末端审查。新增反例验证无 provider、无 produce、无 Sprint 目录。
- 保留日志原字节追加；Arc 缓存允许后续操作追加完整旧日志前缀，其他输出篡改仍拒绝。

## 实际验证

```powershell
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_chapter_arc tests.test_cnw_pipeline tests.test_cnw_maintenance tests.test_cnw_recovery tests.test_cnw_role_inputs -q
# 53 tests / OK
.\runtime\envs\critics-api\Scripts\python.exe -m unittest tests.test_cnw_runner tests.test_cnw_generation tests.test_cnw_adapters tests.test_cnw_project_import -q
# 64 tests / OK
```

合计 117 项离线通过。系统全局 Python 因外部同名 tests 包导致模块加载失败，改用既有 critics-api 环境后运行通过；失败无模型调用。PowerShell 入口语法另核。

Controller 对上述源码修复及离线验证设计限定 ACCEPT；候选精确 C/T 仍须独立记录。不是 Chapter/Sprint Live、J19 全链或整体 Atom 终验。费用保持保守占用 CNY 4.615061 / 10（包括历史 UNKNOWN_NOT_ZERO 预留），本增量费用为零。`USER_CREATIVE_ACCEPTED` 未记录。
