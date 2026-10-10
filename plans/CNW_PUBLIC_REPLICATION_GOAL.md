# CNW 本地完整复现：最终目标与停止准则

日期：2026-10-11。依据用户最新澄清、独立来源研究子智能体 `convergence_audit` / `story_state_fit` 和只读 Controller 的建议。

本文件限定本次工作的目标、必达功能和停止条件，不表示已经通过，不增加创作方法。P3.1/Atom 与历史签收保留；与“把样本打磨到零 bug”“持续提高文学质量”有关的旧验收解释，以用户最新指令为准。

## 1. 最终目标

**在 StoryStudio 本地完整复现固定公开 CNW 工作流的输入、岗位职责、生产次序、处理规则、产物、反馈和项目维护，使其能够在既定主线与关键情感转折之间，生成符合当前人物状态、有助于塑造角色的日常事件草稿。**

唯一方法基准：`MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。本地原件：`runtime/reference/cnw_97ad71fe5e5e/`；源身份清单已经捕获，不追逐后来版本。

一比一要求本地实现承担同样的公开职责，不能只复制阶段名、存放模板或导出提示词。公开的是方法、prompt、模板和实例，未公开完整内部自动化执行器；本地代码负责实际执行公开方法。未公开代码、原作者作品内容、速度、销量和个人文笔不作为可复刻对象。

### 本项目用途与官方承载位置

| 用户要求 | 官方承载位置 | 应观察的效果 |
|---|---|---|
| 主架构、主线和关键情感转折已确定 | Canon 的锁定决定/Hard Rules；Arc；Plot 的 Required Beats、Forbidden Items、Connections | 日常事件不改既定主线、节点和后续分支；未指定的事件结构仍由 Plot 设计 |
| 日常情节有意义，能够塑造人物 | Plot 的 Role in Arc 明示 breather 可以承担 character beat / world detail；Cards 的 WANT、Start/End state；Brief 的行动指令 | 具体事件中有行动、选择和回应，能表现人物性格或关系；不只是人物轮流讲话，也不强制每场打斗或重大冲突 |
| 此时各角色处境、关系和知情范围正确 | timeline 的事件次序/章节时间范围；人物资料；Cards 的 Time、Start state、POV knows/not knows；Brief 的 Active Canon | 区分作者知道、角色此时知道/误以为、读者可知；不借用后续阶段信息或关系 |
| 让玩家喜欢角色 | 本项目人物与读者体验目标；Character、Plot、Story-specific Lens；实际阅读 | 工作流提供可理解、可辨认的人物行为及审查机会；玩家喜爱与情绪落点由实际体验判断 |

上述字段依据官方 `templates/90_canon/`、`templates/04_chapter_design/arc.template.md`、`templates/06_plot/plot.template.md`、`templates/05_scene_cards/scene_cards.template.md`、`templates/07_draft/writing_brief.template.md` 和 `docs/THREE_LAYER_REVIEW.md`。

**公开项目没有完整的“每个角色 × 每个时点 × 所有分支”自动状态数据库或自动推导算法。** 必须从已有原稿、Canon、时间线和角色资料提取本次插点的状态；缺失或矛盾保留 `INFERRED / TODO_CONFIRM`，不能猜成事实。工程工作状态文件不能冒充故事内角色状态。

如果某项用途当前不能支持，报告缺少的来源或实现，先完成可完成部分，但不得把部分完成记为完整终验。官方不能保证每次故事好看、情绪准确命中或所有玩家喜欢；这些限制不由手工打磨诊断输出来掩盖。

## 2. 有限必达功能清单

以下源路径相对固定官方版本。每项须有本地执行映射、规定产物及验证范围。C01–C15 冻结后，不因样本的新瑕疵自动增加项目。

| ID | 必达功能 | 官方依据 | 有限通过证据 |
|---|---|---|---|
| C01 | 项目结构、完整操作指令；Canon/设计/正文/审稿/修订分离，已有资料保护 | `templates/README.md`；`templates/CLAUDE.md` Core Mission / Absolute Rules / Folder Map；`docs/ARCHITECTURE.md` | 新项目实际文件与正式请求中的完整指令；模板可复制或等价建立，不要求所有可选模板已经填写 |
| C02 | Workflow 01：全部选定原稿、三类确定性、九个指定文档、问题与日志 | `templates/_workflows/01_first_import.md` The Prompt / Expected Outputs / Pass Order | 原稿字节、真实整理调用、规定文件及消费；不强制逐句抄写、原句相等或自创分类前置流水线 |
| C03 | Workflow 02：新增/变化资料，保留旧结论；矛盾保留双方供作者决定 | `templates/_workflows/02_incremental_update.md` The Prompt / Critical Rules | 同项目一次真实增量；未变资料复用、追加保护、冲突及恢复的确定性证据 |
| C04 | 写作前定位当前阶段、所属 Arc/章节细纲、前一话与必要资料 | `docs/ARCHITECTURE.md` Stage order matters / Why 04 Has Two Layers；生产手册读取顺序 / current_sprint 运用 | 实际请求来源和身份；首话、多个 Arc、前一话及当前知情时点的选择分支 |
| C05 | Plot→Cards→Brief→Prose 四岗；作者规定的基础表及模板补充读取职责；Prose 只读 Brief 与本话实际说话者声线 | `templates/config/ai_roles.template.yml`；Plot/Cards/Brief/Canon/timeline/world 模板 | 同一 J19 真实产物和消费；当期状态及任务边界经 Brief 传递；多场 Chapter 组装离线证据 |
| C06 | 项目禁止规则驱动确定性 Layer 1/2，行号及上下文定位 | `docs/THREE_LAYER_REVIEW.md` Layer 1 / Layer 2；`forbidden_patterns.template.md` | 真实正文两层报告，不同项目规则离线正反例；检测本身不删改正文 |
| C07 | 五 Lens 按职责读资料，独立并行，不互看意见 | `docs/THREE_LAYER_REVIEW.md` The five lenses / Key principle | 同一真实正文的五组请求、各自来源、结果与调度；Story-specific 使用本项目目标 |
| C08 | 每 Finding 三种立场反证；不确定默认反驳，至少 2/3 未反驳才保留 | `docs/THREE_LAYER_REVIEW.md` Adversarial Verify；`workflow.template.yml` adversarial | 真实 Finding 请求；投票组合与零 Finding 离线分支，不制造意见凑请求 |
| C09 | Completeness 读全文及存活意见；遗漏入 Refine，反馈对应 Lens | `docs/THREE_LAYER_REVIEW.md` Completeness Critic | 正常真实调用；入队及下一次 Lens 加载反馈的确定性证据，不要求模型每次发现遗漏 |
| C10 | Refine 消费确认问题，Re-review 复查受影响范围；新问题继续处理或明确未完成 | `docs/THREE_LAYER_REVIEW.md` Refine / Putting It Together / Common Failure Modes | 真实修订/复审消费链；受影响 Lens、再次修订、无问题与有界停止离线分支；不能未完成却标完成 |
| C11 | Workflow 03：P0–P3 计划、Canon/核心保护、原稿保留、修订另存、批准后晋升及归档 | `templates/_workflows/03_revision.md` The Prompt / Promotion Step / Priority Discipline | 当前审稿协议到计划消费；保护、待决策、批准与晋升正反例，不伪造作者批准 |
| C12 | Workflow 04：跨 Draft/Design/Canon/Plot 审计；三类严重性、双方文件/行范围、建议、不自动解决、问题去重 | `templates/_workflows/04_canon_audit.md` The Prompt / Audit Targets / Frequency | 小项目一次真实正常审计、Canon 未改身份；全量/轻量/定点选择离线验证，词表局部比较不等价 |
| C13 | Workflow 05：当前项目的八节紧凑交接；状态、核心、问题、下一动作、指针及旧交接归档 | `templates/_workflows/05_handoff.md`；`docs/HANDOFF.md` Archiving Old Handoffs | 真实正常交接及输入，统计/指针/归档核对；固定套话不等价 |
| C14 | 逐话、多场、五话 Sprint、批量审稿、推进/修订/重写门、carry-forward、索引/状态；适用时 Arc-end review/交接 | `workflow.template.yml` sprint / handoff；`batch_review.template.md`；`docs/ARCHITECTURE.md`；生产手册 | 多场 Chapter、五个不同虚构 Episode 的离线端到端及门控分支；正式执行器有真实调用路径，不能仅回放 fixture |
| C15 | 正式入口、恢复、精准失效、已付费身份复用、准确状态、可读导出；NK/CritiCS 职责分离 | `templates/CLAUDE.md` Always log work / Output Style；生产手册索引/状态；本项目成本及治理授权 | 实际 run 重入/导出，费用回执及影响范围验证；独立精确 C/T、正常推送和远端回读 |

生产手册来源：`example_project/00_meta/episode_production_manual.md`；只取公开操作职责，不把示例作品设定迁入本项目。

核心顺序保持：`plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review`。Workflow 01–05 是触发式维护，不是逐话额外创作阶段。NK/CritiCS 不冒充 CNW 岗位。

### 标准操作和可选内容

`templates/CLAUDE.md` Standard Commands / Safety for Long Projects 中的手稿分解、Canon 提取、JET 诊断、Character OS 提取等，纳入 C01–C05/C12/C13。必须可执行、获得完整指令及相应上下文、写入正确位置；可以复用实现与证据，不为每个自然语言措辞另建模块或重复付费。仅展示 prompt 而无人/执行器实际能运行，不等于已经自动实现。

JET 在 `docs/ARCHITECTURE.md` What Lives in 91_jet_engine 中明确可选。保留其操作能力，仅本项目选择时使用公开框架。示例主角规则、误认模型、禁句、人物和评分不自动移入本项目。Sprint 门应按公开配置及本项目明确选择执行；通过、修订、重写、待作者决定都是有效功能状态，不要求样本无限追求高分。

新项目访谈、最初 3–5 章人工练习、Canon 决策、创意批准、人类润色属于适用时作者动作；实现相应输入/待决策/批准机制即可。本轮不为这些建议额外生产小说。

## 3. 最小有限验证组合

1. 复用身份未变的固定原件、NK/CritiCS 原生能力、账本与组件证据。旧 P2 不冒充新全链。
2. 一个小型虚构维护项目：导入、一次增量、审计、修订计划、交接。未证明的模型职责补必要正常调用；冲突、保护、统计、归档等确定性分支离线。
3. 同一 J19 完整正常链路，分阶段审真实请求、产物及后续消费；兼容身份阶段可复用，输出保留原样。遇到问题先查官方处理，只修对应实现。
4. 一个虚构离线 Chapter/Sprint 组合：多场、五个不同 Episode、批量门、carry-forward、Arc-end、恢复和失效。不标成真实模型生产。

保持同一 J19、不生产第二场/批量正文、DeepSeek Flash 与既有剩余预算约束。测试授权不等于增加创作数量或预算。

条件分支（包括 C08 反证、C09 遗漏反馈、C10 修订/复审）在授权真实运行中自然触发时，审其真实消费证据；未触发时，复用兼容历史真实证据，或以受控离线证据验证并明确标注。不得为获得 Finding、修订或特定评分反复付费，也不将未触发分支冒称 Live 已验证。

每次补验须指出 C-ID 与缺证。源/提示/输入/消费语义未变则复用；只验证受影响职责。提示/读取变化后，旧调用保留历史，不证明新输入。解析/判定变化可用真实 raw 验证新消费，不自动重付费。组合证据须依赖兼容，不相干产物不能拼称一次 Live E2E。

## 4. 处理差异与样本问题

Controller RETURN 必须写明：**C-ID → 官方条款 → 实际实现偏差 → 最小修正 → 受影响复验范围。**

- 漏读当期状态、Prose 越权读合同、上游未被消费、审稿或反馈缺失等是实现差异，修工作流。
- 请求、资料、职责与处理均符合官方后，某次称呼错误、漏判或文学欠佳保留为诊断；不自动增加工程门或全链重跑。
- 没有事件、没有规定产物、输出无法被消费，仍须检查功能是否实际执行。不能只验接线和请求数。
- 官方允许拒绝发明事实的输出或交作者决定，应实现相应处理；不要求所有随机失败在本轮消失，不手改输出制造通过。
- 玩家喜欢、情绪落点与日常趣味记录实际观察，不能承诺所有玩家反应。

## 5. 工程停止条件

**全部满足即停止本次工程整改和付费诊断：**

1. C01–C15 全部有固定来源、实际可执行映射、规定产物及消费者，没有只有名称/模板的空职责。
2. 必要模型职责有代表性真实正常运行证据；确定性分支及未实跑规模的离线覆盖、验证范围明确。
3. 同一插点的主线边界、逐角色当期处境/知情/关系限制、人物塑造用途能进入 Plot→Cards→Brief→相关 Lens；Prose 保持官方范围。缺来源明确标记，未冒充事实或自动能力。
4. 独立 Controller 无剩余、能指出官方依据的实现差异；修复后完成影响范围验证，无阻碍授权入口的功能缺陷。
5. 正式入口、恢复、可读交付可用，源身份/费用/隐私/历史状态准确；精确 C/T 独立签收、正常推送、远端回读一致，完成既定源码/结果审查门。
6. 分别交付方法工程等价、Scene Live、Chapter Offline/Live、Sprint Offline/Live 与创意亲读状态。

满足条件可记 `PUBLIC_METHOD_EQUIVALENCE_VERIFIED`；未真实运行的 Chapter/Sprint 继续标 `EPISODE_LIVE_NOT_RUN / SPRINT_LIVE_NOT_RUN`，不宣称所有规模实产验证。本轮不为消除这两个未运行状态扩写小说。

`USER_CREATIVE_ACCEPTED` 由用户亲读决定，不代签，也不使工程无限继续。完成后只有新用户目标、来源版本改变或可复现实现缺陷重开对应项；普通文学反馈进入另一个明确创作任务。

预算不足、证据缺失或功能未闭合时报告未完成，不能提前记完整通过。可完成部分先收敛，剩余明确报告。

## 6. 定义目标时的已知状态

- 导入源码增量限定 ACCEPT 并推送：C=`fe3733ea208b243755a35c730d5a4c34da7253d3`；T=`0b7abfee3ac7fc72cf3fcfef9e9d975585c0bda6`；远端回读一致。这只证明本次导入方法修正。
- C12 Canon Audit 当前只是局部词表比较，C13 Handoff 仍为固定内容，尚未承担完整官方 AI 职责。
- C05 Brief 的相关 Canon/时间范围/世界/术语读取，以及依 Brief 实际说话者选择声线，仍有有限输入缺口。
- 当前私有资料有相对时间/分支/知情基础，但尚未证明逐角色当前状态全链接通；工程 current_state 不是角色状态快照，不声称全路由自动推理已完成。
- 完整新 J19 方法终验未闭合，Episode/Sprint Live 未运行，创意亲读待定。

**本文件是目标收敛结果，不是完整复刻已达成的声明。**
