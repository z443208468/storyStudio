# StoryStudio 验收：真实消费者、原方法与最终输入包效果

唯一活动计划为 [R5](../plans/MASTER_PLAN_GENERIC_APP_R5.md)。固定作者方法为 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；旧实现回归参照 `26b72cea21dce45eede21cffddd4e75307d75652`，不得修改冻结副本。

## 三种事实分别验收

1. 离线确定性证据：实际生产函数/文件/请求/SHA/消费者及负例。模拟不证明真实网络、费用或故事质量。
2. Live生产证据：可信独立签收及Owner许可、当前请求和费用政策、真实Provider原回执/usage、实际下游消费及分别导出。工程Controller原始裁决不是运行签名。
3. 创意接受：用户真实阅读最终文本后的决定。模型自评、自动Review或工程ACCEPT不能代签。

## 逐Atom与集中收敛

Controller是独立只读子智能体；自行读取完整当期计划、固定方法、候选C/T、源码/调用链及真实证据。完成整体检查后一次汇报全部发现问题及位置、依据、影响、Git来源、依赖和共同复验范围。后续Atom问题也列明，不能提前施工。

Writer集中修当前Atom阻断、统一复验；返修新增问题回到同一清单。不得查一个报一个/局部通过宣告全Atom完成。明确实际检查范围、未检或缺证对象。全当期门通过并冻结、正常推送/远端回读、取得下一Atom许可后才能继续；原RETURN永不补造为ACCEPT。

## M01–M16与实效

| 门 | 所需实际证据 |
|---|---|
| 方法/四角色 | 固定原件身份，允许读集，Plot→Cards→Brief→Prose真实请求/产物SHA；不同意图与项目要求逐级消费 |
| 双Lint/五Lens | 不改原稿；五个独立请求，项目第五职责/SHA实际进入请求；越权/跨项目canary拒绝 |
| 每Finding三反证 | 三个不同真实消费者/票，逐项ID匹配与2/3阈值；缺/重复/错配票拒绝；不确定优先反驳 |
| Completeness/Refine/Re-review | 真实遗漏进入Refine；旧稿保留，新稿全文Lint和受影响Lens重新消费，不能借旧PASS |
| Canon/Workflow01–05 | 原始来源保护、事实/推断/候选区分、未决/冲突不自裁、普通审稿生成修订计划、批准修订另存、未经独立门不晋升 |
| Sprint/Arc | 五话75/0/2门、实际各话/批审和交接/Arc消费者，失败暂停，下一批真实读carry-forward |
| 扩展/辅助 | INSERT真实锚，ADAPT真实选段，ORIGINAL合法Canon/Arc/前章；NK/CritiCS禁用不需结果、启用失败阻断且不替代CNW |
| 恢复/权限/费用 | 中断保留、身份匹配不无故重跑，拒绝跨Run/资料/实现重放；真实账本PENDING/UNKNOWN保留，共享slot/累计费用/次数 |

详细逐项标准和反例以R5原表为准。文件存在、阶段名字不变、测试总数、Prompt中含字段不构成以上门通过。

## 冻结保护与允许复用

后续改动按影响图复验已收口功能：来源/合同改变重验依赖；请求/实现改变重新核签名和恢复；仅文档改动核链接、命令/消费者、状态与方法，不重付费。修改导出说明须核真实文件/manifest、V1/模拟边界、正文不变及恢复指引；旧实现许可不能移给新源码。

保留命令、退出码、原始输出、源码SHA、actual请求/文件SHA和Controller原件，失败批次保持失败而非摘取pass冒称全绿。旧基线缺私有文件时标BASELINE_EXECUTION_UNAVAILABLE，仅作固定源码/方法限定比较，不伪造重放。

## 当前08与最终硬门

08安全工程只做批准范围的文档/历史整理和最小导出说明修正。受跟踪历史文件先仓库外原字节+路径/SHA备份，核入出消费者后正常替换；不重写Git历史。旧私有项目、Run、账本和导出不移动、不删除、不切换；`CUTOVER_BLOCKED=true`，不能宣称CURRENT_HEAD_FULLY_SEPARATED或GIT_HISTORY_PRIVATE_SCRUBBED。

最终须用用户实际输入包的全部声明任务：材料/要求完整保留、映射到合法岗位、按真实CNW生产及审稿修订、消费可信Live回执、输出分别可读故事与状态。用户只提交包和DataHome/启动任务，不手工承担内部Run/合同/阶段编排。隔离三项目模拟及EARLY门不能替代这道最终验收。当前 `INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED`、`GENERIC_LIVE_PRODUCTION=NOT_RUN`，用户创意接受待亲读。
