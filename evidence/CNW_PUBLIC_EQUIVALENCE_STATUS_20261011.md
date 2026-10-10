# 固定公开 CNW：量化收敛与最终待修订证据

## 最新：C06 两条真实项目规则与离线补证

按用户定点要求，当前 J19 Layer 1/2 从各0条补为各1条项目可执行候选规则，原语义规则及Layer 3保留。现有加载器无需改动。保存的v0/v2各跑两层，四份新报告均1条规则、0命中；仅说明两种正则形状未匹配，不证明语义通过。12项离线测试通过，0新增付费；历史Lint/run_state/正文/账本哈希未变，Controller限定ACCEPT。详见 `evidence/CNW_C06_OFFLINE_LINT_20261011.md`。外部私有证据复核及整体终验仍待定。

## 最新：外部源码 RETURN 两项定点修复

外部对 `bcc73679db9d3c270591ae812ec22b85344db571` 返回 C02事实来源门、C08同Lens重复Finding ID 两项源码问题。现已定点修复，106项相关离线验证通过，独立Controller对源码修正限定ACCEPT；本轮精确C/T与正常推送回读随交付核验，外部复审待定。见 `evidence/CNW_C02_C08_EXTERNAL_RETURN_FIXES_20261011.md`。下方“尚未识别差异为0”是此前审查时点结论，不替代本次RETURN。私有包SHA、219账本/raw和版本消费保持本机核验、外部未核验；不因本次源码修复追认其已外部通过。

2026-10-11，方法基准 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。范围、停止准则始终为 `plans/CNW_PUBLIC_REPLICATION_GOAL.md` C01–C15；没有追加创作阶段或文学质量门。本文不含私有稿件或密钥。下列为各项实际验证范围，不是全规模Live或成稿通过声明。

独立Controller对本轮九文件工程/测试/交付证据限定ACCEPT；按冻结范围与累计审查，当前已识别、尚未修复的官方职责实现差异为0。这不是所有输入或模型结果无缺陷保证。模型调用已停止。工程签收对象C=`bcc73679db9d3c270591ae812ec22b85344db571`、T=`ff1069271d3a05f1a1655186b58c19afecb03878`已正常推送，远端C/T回读一致，凭据为私有run的`artifacts/final_release_receipt.json`。外部当前ChatGPT源码/结果审查仍未取得，Writer和Controller不得代签。

## 与上次停止判断的量化比较

| 项目 | 上次预算阻塞时 | 当前真实证据 |
|---|---|---|
| 已冻结方法清单 | C01–C15，6组有限差异 | 同一清单；组1–5兼容身份证据复用 |
| 当前复审缺失调用 | 第一轮缺40个Verifier | 第一轮20Finding×3完整，14confirmed |
| 确认意见后续消费 | 尚未证明 | 14项原意见全部进入正常Refine，发布v2 |
| 下一次复审 | 尚未真实执行 | 第二轮19Finding×3完整，15confirmed |
| 第二轮问题后续处置 | 尚未证明 | 15项进入v3有界长度恢复，3次尝试/2个唯一付费响应，第三次同请求缓存复用；1143<1200，拒绝发布v3 |
| 实际终态 | EXECUTION_INCOMPLETE，缺票 | REVISION_REQUIRED，完整末轮票/处置/15pending保留；v2仍未通过 |
| 金额阻塞 | 9.874291/10 | 用户取消金额上限，账本null；保留授权历史与费用，当前15.250129 |

实际方法验证差距缩小，不等于稿件质量同等改善。原错误票导致部分互动/格式退化，独立阅读意见照实保留；不手改正文/票，不重启一组追CLEAN。

## C01–C15验收映射

| ID | 官方职责 | 实现/代表性证据 | 验证范围与终态 |
|---|---|---|---|
| C01 | 项目结构、完整CLAUDE指令与标准操作 | `cnw_project.py`、`cnw_operations.py`；`CNW_C01_C11_STANDARD_DIAGNOSTIC.md` | 完整模板/正式路由；Extraction/Revision代表Live，decompose/JET/CharacterOS离线 |
| C02 | 全原稿First Import及九类产物 | `cnw_project.py`；`CNW_C02_C03_CURRENT_IMPORT_DIAGNOSTIC.md` | 当前完整方法一次正常虚构项目Live；来源/三类确定性/产物实际消费 |
| C03 | 只处理新增变化、保护旧结论与冲突 | `cnw_project.py`、`cnw_import_workflow.py`；同C02诊断 | 同项目真实增量，旧字节与无变化缓存复用；冲突分支离线 |
| C04 | 当前时点/Arc/细纲/前文/索引/人物资料 | `cnw_roles.py`、`cnw_operations.py`；`CNW_C04_CURRENT_STATE_DIAGNOSTIC.md`及当前链 | 同J19源提取/有源纠偏进入真实岗位；不证明全部时点或分支、所有提取准确 |
| C05 | 四岗职责、输入范围与声线选择 | `cnw_roles.py`、`cnw_runner.py`；`CNW_C05_BRIEF_INPUT_DIAGNOSTIC.md`及当前链 | 当前Plot/Cards/Brief/Prose真消费；Plot自主结构，NK支持，Prose只读Brief/相关声线 |
| C06 | 项目规则驱动两层Lint | `cnw_lint.py`；当前两层报告/规则正反例 | 本地真实执行，零命中不表示正文零错误 |
| C07 | 独立并行五Lens及各自来源 | `cnw_review.py`、`cnw_runner.py`；当前raw/请求 | 初审五路+两轮复审共10路，全文/来源身份核验 |
| C08 | 每Finding三反证与2/3默认反驳 | 同C07；当前原始votes/完整reports | 初稿22×3，复审20×3及19×3，均实际处置；原始重复票限制保留 |
| C09 | 全文Completeness、遗漏入修订/Lens反馈 | 同C07；当前Completeness/反馈文件/Refine请求 | 7项遗漏真实进入修订，后续本岗位反馈加载；截断失败及机械容量修正保留 |
| C10 | Refine/受影响复审/新确认意见后续处置 | `cnw_runner.py`；两份完整review、三次Refine版本尝试 | 完整真实意见消费至明确有界长度失败，独立Controller限定接受方法功能；候选未通过，不是CLEAN |
| C11 | 修订计划、保护、批准/晋升/归档 | `cnw_revision.py`、`cnw_operations.py`；标准操作诊断 | 普通Revision代表Live，保护/批准/晋升分支离线；没有创意/Canon自签 |
| C12 | 跨Draft/Design/Canon/Plot审计 | `cnw_maintenance.py`；`CNW_C12_C13_MAINTENANCE_DIAGNOSTIC.md` | full正常Live，light/targeted/保护等离线，不保证审计判断全对 |
| C13 | 八节当前Handoff与旧稿归档 | 同C12 | 真实输入/指针/日志/行动项/归档，不冒称规模Live交接 |
| C14 | 多场Chapter/五话Sprint/批量门/Arc | `cnw_generate.py`、`cnw_sprint_live.py`、`cnw_arc.py`；`CNW_C10_C14_CHAPTER_ARC_DIAGNOSTIC.md` | 正式可执行路由和多场/五话/门控/Arc离线；EPISODE_LIVE_NOT_RUN、SPRINT_LIVE_NOT_RUN |
| C15 | 恢复、身份失效、费用、导出、准确终态 | `cnw_recovery.py`、`cnw_export.py`、`p2_cost_guard.py`；恢复诊断及当前最终证据 | 缓存/保护/失效分支已验，当前待修订候选/费用取消正确；工程精确C/T已独立签收、推送回读，私有源码/结果包已生成；外部审查未通过 |

表内诊断名相对 `evidence/`。各组历史签收、C/T及回读在原诊断和当前对话保留，不重复付费证明。C01–C14已具各自冻结范围的功能证据；C15工程签收/推送/本地交付已收尾。外部当前ChatGPT源码/结果审是既定Atom门，单独待定，不驱动文学重跑；停止准则第5项的该外部门尚未满足，不记录整体目标完成。

## 当前真实身份与调用

同一 `CQ-J19-INSERT-01`；run `CNW-RESTORE-J19-CURRENT-20261011-02`。合同SHA=`f6310429e96522e083e35afb7178e9d9139a4a883991428ae7a5ce0c13145c4d`；原稿/设计/旧合同/全部版本与旧票未删除。

- 末版可读候选v2：1411可见字符，字节SHA=`96468c380f41da7c8ae353c21912e6d379de640b8b1632d82b01989c56aea200`。
- 两份末轮报告SHA：review1=`75b4c10382fd8dd21a3fd5bac641e28f23553716269c9a3367ff52ec596bb90a`；review2=`d7c72df11af9cf766736dc7b99e0e1cf7d2cf2fc472c111049f6d30f4307fbba`。
- 当前CNW体系成功回执210（含NK1）；复审共10 Lens+117 Verifier，39条Finding均有完整三票。另native CritiCS8、截断Completeness1；本run账本219笔，input4660786/output93579 tokens，估算费用10.120657 CNY。
- 用户授权解除上限前共享占用9.874291；续跑新增105笔，共估算5.375838；现共享15.250129 CNY，金额上限null。历史UNKNOWN非零0.028333保留，未知不改零。
- v3仅2条独立paid response：`79fe6db6-5ae7-4a4f-bf5a-98bcf00135e9`、`98b747e6-2279-4fa9-817c-398d9c89379a`，均1143字。第三次同内容/请求身份重用后一条缓存，在禁HTTP/reserve下证实ledger/回执数不变。v3未发布，没有把三次尝试记为三次收费。

准确核验：私有run `artifacts/current_chain_final_bounded_evidence.json`，候选全文/每票raw/判定、15pending、各次修订输入及第三次cache重入均核对。它证明明确失败/待修订功能，不能标 `LIVE_EVIDENCE_VALIDATED` 或 `CLEAN`。

## 为什么现在结束模型调用

停止依据没有变。官方确认问题入Refine、修后按受影响范围审查；本次已按方法真实发生。固定本地合同的三次长度恢复耗尽，Controller认为这是已实现明确失败分支，没有发现需要新创作步骤的实现差异。继续重启另一组只会追样本质量，不能增加公开方法等价证据。

独立 `story_state_fit` 确认v1→v2全部14项问题及原Brief真消费；同时报告部分行动回应被误票削弱、对白标签与Brief冲突、操作要求混入正文等实际退化。主要当期知识/固定主线仍守住，但效果仅部分实现。老师对应资料遗漏与错误司业意见仍在；不把它们当作者事实，不声称玩家喜欢或人物塑造充分。

现状态：`REVISION_REQUIRED`，15项待修订，候选 `UNREVIEWED_CANDIDATE`；不会自动晋升。`CNW_FULL_PRODUCTION=NOT_VERIFIED`（非CLEAN）；完整方法整体终验仍待本次治理/外部门。`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。外部源码/结果审查和创意亲读分开；本轮工程不继续扩写或付费打磨。

## 本次工程变化

用户取消预算金额上限的nullable支持、显式set-limit授权历史、有限旧账本兼容、dry-run无限额支持及AGENTS最新覆盖；具体使用见 `docs/CNW_COST_ACCOUNTING.md`。162项相关离线通过，包括新6项费用模式正反例，以及既有CNW Review10项；不将离线规模冒称Live。
