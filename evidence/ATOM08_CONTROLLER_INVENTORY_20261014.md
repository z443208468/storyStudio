## ATOM08盘点结论

```text
CURRENT_ATOM=08
BASE_C=b93d0094003ca93428ab18fd5def6d29119543d0
BASE_T=8c4b97ac61092c9522a674c67625b88df19b8db7
ATOM08_VERDICT=NOT_YET_SUBMITTED
NEXT_ATOM_PERMISSION=WITHHELD
PRIVATE_MIGRATION=NOT_AUTHORIZED/NOT_RUN
CUTOVER_BLOCKED=true
```

07推送及冻结记录一致，原接受全文SHA为`f847c15d…9e852`。193份修改前公开文件的仓库外备份已独立重开核对，零SHA差异。这提供修改前保护，**不自动授权删除其中全部文件**。

### 本轮完整问题清单

以下均为b93中已有的文档／历史整理问题，本轮尚未引入代码改动。

| 问题、位置与证据 | 影响及最小修正 |
|---|---|
| **当前状态过时**：[README.md](D:/CangqiStudio/StoryStudio/README.md)、[CLI_COMMANDS.md](D:/CangqiStudio/StoryStudio/docs/CLI_COMMANDS.md)、[BOOTSTRAP_VERIFICATION.md](D:/CangqiStudio/StoryStudio/docs/BOOTSTRAP_VERIFICATION.md) | 仍将历史09接受当当前阶段背景，并称V2 Live路线／费用适配未实现。改为当前00–07冻结范围、08施工、09待当前顺序终验；区分“代码接口已接受”和“生产信任未部署／真实调用未验”。历史09裁决只能按原C/T引用。 |
| **正式包能力说明不完整**：[INPUT_PACK_ADAPTATION.md](D:/CangqiStudio/StoryStudio/docs/INPUT_PACK_ADAPTATION.md) | 只描述legacy插写、每任务单独实例，仍写`LIVE_ROUTE_NOT_READY`，遗漏原生V2项目组、ADAPT／JSON／ORIGINAL依赖与独立Live attempt。按实际parser和`execute_package_job`更新；来源`-Offline`与执行`-Mode`分开，用户只提供包／DataHome／job，内部身份仍由应用建立。 |
| **ADVISORY新旧语义混淆**：输入适配、Chapter/Arc、角色及Prompt合同 | 仍宣传新任务的4700字符容量硬门、欠产续写、超限重写或缩水比例拒绝。说明新V2的ADVISORY、旧无字段合同保留历史语义、真正遗漏继续修订；token、费用和截断门独立。不能删原包目标或改历史合同。 |
| **授权／费用文档落后**：[CNW_MAINTENANCE.md](D:/CangqiStudio/StoryStudio/docs/CNW_MAINTENANCE.md)、[CNW_STANDARD_OPERATIONS.md](D:/CangqiStudio/StoryStudio/docs/CNW_STANDARD_OPERATIONS.md)、[CNW_COST_ACCOUNTING.md](D:/CangqiStudio/StoryStudio/docs/CNW_COST_ACCOUNTING.md)、[W10_TRUST_INTERFACE.md](D:/CangqiStudio/StoryStudio/docs/governance/W10_TRUST_INTERFACE.md) | 把“未部署”写成“未实现”，或称批准修订尚无授权适配。写清Controller预检、独立Owner许可、注册operation／辅助作用域、共同RunAccount／slot／账本及UNKNOWN；Creative approval不授Provider权限。历史campaign无上限记录保留为历史，不能成为新项目默认。 |
| **CLI表与实际分支不符**：[studio.ps1:251](D:/CangqiStudio/StoryStudio/tools/studio.ps1:251)与CLI表 | `prepare-live/live-call`已有V2受检整阶段分支，不能整体标为仅legacy；`accept-role`仍应明确V2拒绝。维护prepare-only是实际Python接口，未见同名PS开关，文档不得发明参数。 |
| **Bootstrap缺实际测试依赖／隔离说明** | 新真实Node shim测试在缺Node时明确失败：[test_cnw_nk_input_limits.py:51](D:/CangqiStudio/StoryStudio/tests/test_cnw_nk_input_limits.py:51)。指南应声明Node及实际验证版本／能力，区分无需常驻NK服务与不需要Node。普通`pytest`命令本身不是断网机制；说明清凭证、网络／子进程边界及记录要求，不宣传系统全断网。 |
| **开写门仍指向旧单场合同**：[implementation/CNW_ROLE_INPUT_OUTPUT.md](D:/CangqiStudio/StoryStudio/implementation/CNW_ROLE_INPUT_OUTPUT.md)、[CNW_PROMPT_CONTRACTS.md](D:/CangqiStudio/StoryStudio/implementation/CNW_PROMPT_CONTRACTS.md)及三份P2 SPEC | 含固定项目、中文、单场许可、旧长度门和旧预算。后两份是AGENTS明确消费者，必须保留岗位职责并提供通用当前版本；五份原稿先原字节归档。不得把旧文献中的“尚未执行”或旧许可当当前状态。 |
| **历史入口仍自称活动计划**：`MASTER_PLAN_FROM_EMPTY/P2/P3/P3_1`、旧reviews／Controller正文 | 先外部归档，再按入出消费者决定正常提交替换／移除。保留历史原文、SHA及来源索引；活动入口只指当前R5。R5仍引用`P3_1_CONTROLLER`的保护规则，可保留该路径为明确的历史索引／通用保护转介，避免断链。 |
| **managed导出说明固定offline**：[cnw_export.py:225](D:/CangqiStudio/StoryStudio/tools/cnw_export.py:225) | 未来Live job仍会收到固定模拟说明和offline恢复命令。08可做现有说明／manifest的最小准确性修正，按已核实际执行信息描述；不能凭`mode=live`自报已验Live。真实包Live导出效果留09／最终产品门。 |

### 不能按名称删除的消费者

实际路径是`config/cnw_production_policy.json`，仓库没有`cfg/`。

- **保留**`config/cnw_production_policy.json`及原policy snapshots：角色V1读取、合同构造、W10旧预检、快照构建和兼容测试仍消费。
- **保留**`p2_cost_guard.py`、价格快照：当前共同账本、锁、slot、reserve／settle的实现。
- **保留**`p2_06_critics_run.py`、`critics_bridge.py`：Runner、W10、实现身份和实际native结果消费者仍引用。
- **保留**W10历史常量与`legacy_source_path_map.py`的受限旧身份；不把它们当新项目默认，也不为消除关键词改原SHA。
- **保留**CNW固定来源、C01–C15、M01–M16映射、许可证、当前测试及R5证据。`CNW_PUBLIC_REPLICATION_GOAL.md`含方法与历史项目范围，须明确当前范围覆盖旧项目限制，不能整体当垃圾。
- 原单场draft/revision及一次性probe可列为**归档候选**。公开代码引用检索未见当前通用入口调用，但还须逐文件记录import、动态加载、CLI、测试及输出依赖；字符串零命中不是完整无消费者证明。

旧P2/P3报告的内部互引应随归档一起保存。当前新Controller裁决、冻结和测试原件不能混入旧场景清理。

## 准许的08集中施工范围

1. 按上述清单更新活动文档、当前方法合同与历史索引。
2. 外部原字节归档已证明无当前必要消费者的**受跟踪公开历史文件**，再正常提交替换／移除；保留Git历史及可追溯清单。
3. 必要时仅修现有导出说明的模式准确性，不改授权、费用、生产职责或阶段调度。
4. 不改应用全局policy／W10旧身份，不做适配器改名重构，不碰旧私有项目、运行、账本、导出或未跟踪进度。

## 共同验收证据

形成一次完整08候选前，至少提交：

- 原路径→外部归档→原物理SHA／Git blob SHA→保留或替代路径→实际消费者的映射；两种字节有差异时分别记录。
- 所有活动文档的链接、命令／parser对应、当前状态及方法职责对照。
- 受影响冻结00–07功能清单。文档未改变实现的项按精确身份复用；若改导出说明，验证真实导出内容／manifest、旧V1及MOCK标签、恢复指引，正文和授权门不变。
- 新source-only clone的实际doctor／入口检查；必要bootstrap按固定源／lock执行。此前修改前doctor只是基线，不代替修改后结果。
- 修改后保护SHA、明确staging路径、精确C/T；Controller完整08接受并冻结、推送回读后才能申请09。

不要求因纯文档或未使用历史文件整理重跑完整native链。若改`cnw_export.py`，它属于签名实现身份输入，必须记录新实现身份及原许可失效，不能把旧签名移给新源码。

## 阶段边界

当前08安全工程可以独立收口；须明确记录：

```text
ATOM08_SAFE_ENGINEERING=<待精确候选验收>
LEGACY_PRIVATE_RELOCATION=BLOCKED/NOT_RUN
CUTOVER_BLOCKED=true
CURRENT_HEAD_FULLY_SEPARATED=NOT_ESTABLISHED
INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED
```

这不是把私有迁移门签成通过。§0.3a及07许可限定当前08不搬移、不删除、不切换私有数据；最终“应用目录无旧私有数据”仍须原危险门另行收口。

本轮未重新全文审读全部第三方及历史P2/P3正文，没有读取私有内容、运行测试或授予候选／推送权限。盘点引用只是辅助；归档许可须由实际消费者映射和精确候选证明。
