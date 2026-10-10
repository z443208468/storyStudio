# C12/C13 官方维护职责：有限实现与真实验证

日期：2026-10-11。依据 `plans/CNW_PUBLIC_REPLICATION_GOAL.md`；唯一固定来源 `MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。

## 源码职责

- Workflow 04 的四类交叉来源、三种严重性、双侧文件/原行定位、说明与建议，实际完整提示及文件全文进入模型请求。默认 full，light 指定新正文并保持基准来源，targeted 跨源核指定子系统。
- 报告原样保存，行动项只作文本/空白归一去重追加到 unresolved questions，保留既有作者问题，不自动改锁定 Canon。
- Workflow 05、完整官方指令、交接模板及 `docs/HANDOFF.md` 进入请求；跨当前主题、设计、Arc、正文、Canon、审稿、当前状态和索引。八节交接及可选 Pipeline Context Pack，真实文件/字符统计与不确定性明确。
- 旧 handoff 原字节身份归档；原子发布及日志按 project lock + source snapshot + pre/postimage transaction 恢复。复用验证原 request/raw、合法来源 postimage、方法及实际请求适配/模型配置身份。
- 实际入口见 `docs/CNW_MAINTENANCE.md`。`cnw_project.py` 薄调用 `cnw_maintenance.py`；Python/PowerShell 均转发对应 scope/pipeline 选择。维护操作不加入 `CNW_STAGES`。

## 代表性真实运行

私有项目 `workspace/FICT_CNW_MAINTENANCE_20261011`：明确标记的静态虚构 fixture，不是苍歧原稿，不是新增模型正文。两份短稿预先固定，Canon/Plot 的 day5 与 draft day6 供正常审计；不要求模型产生特定数量 Findings。

| 操作 | Private run | Provider ID | Usage input/output | 估算 CNY |
|---|---|---|---|---|
| full Canon Audit | `a959d20902e781afadbaed45` | `db6bfb03-8fc1-4e8c-87ec-9c32ac66524a` | 13308 / 1711 | 0.040506 |
| pipeline Handoff | `658fdb44e0d83625c98d684e` | `c101e3a1-ecd0-4df6-9471-2e3c06ee41e8` | 18790 / 1951 | 0.053454 |

均真实 `deepseek-flash / stop / SETTLED`，合计 0.093960 CNY；既有 campaign committed 为 4.615061 / 10 CNY，包含前次未知预留，不等同确认实收金额。

实际 Audit 识别 day5/day6 矛盾，输出双侧来源、严重性、说明与建议；四项行动记录追加并保留原 banner color 问题。锁定 Canon、设计、Arc、Plot、正文 hash 全不变。

实际 Handoff 消费新增 Audit/未决问题，引用当前 Arc/固定节点/知情限制及未完成最新稿，八节及 Context Pack 有内容；正确区分正文/Brief/索引，报告可见非空白 Unicode 字符数 263，并保留完成比例未知。

- Report SHA256：`56eac07a8f09c8d46cda9b452b392e4f63b0945280da672ad666261273728b2a`。
- Handoff SHA256：`d72844b50294a504fed1d2eeb3b9e097a021ecfd771ed5c831e7187827124ac0`。
- 原旧版 SHA256：`88e30269287e6f17199b45235fc30a292bf8b89dea28171c5e0171ac947f4162`，archive 字节相同。
- 原 request/raw/journal 在 `94_runtime/maintenance/<run>/`；project root 的 `diagnostic_fixture_identity.json`、两项 result 和 `diagnostic_consumption_check.json` 记录源身份及消费。
- 禁网络、新 reserve 后正常入口重复 Handoff 返回 `reused`，账本字节未变。没有重新付费生成，也未手改模型产物。

## 观察和有限验收

Audit 也有模型过度判定：把当前无矛盾的知情约束标 HARD CONFLICT、把没有禁止的同日事件推成碰撞、把已能从时间线推知的连续性列成缺项。Handoff 尾部对旧 current brief 路径的措辞不准确。上述原样保留；不冒称审计准确率保证，不把这些瑕疵转成无限返工门。

独立只读 Controller 先 RETURN 缓存身份不足；最小修正后运行前限定 ACCEPT。真实结果审阅后 **限定 ACCEPT C12/C13 此次实现及代表性职责**：跨源 Audit 实执行，Handoff 消费审计/当前状态且旧版归档；未发现观察缺陷由漏读、岗位替换或消费断链造成。按有限准则保留模型局限，不手改样本或重复付费。

full Audit / pipeline Handoff 为 Live；light/targeted、零发现、文本去重、半写恢复、外部冲突、请求 tamper、适配变更与配置失效为离线。新维护 10 项、import 9 项、pipeline 10 项通过；PowerShell AST 参数解析通过。没有生产第二场、调用新正文或改变预算；整体 C01–C15、J19 全链和创意亲读未据此签收。
