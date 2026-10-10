# 当前 J19 正常链：真实消费、预算中止与有限收敛

日期2026-10-11，固定 CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`，有限目标为 `plans/CNW_PUBLIC_REPLICATION_GOAL.md` C01–C15。本文不含私有正文、原稿或密钥，不以手改诊断稿、删 Finding 或补票完成验收。

## 当前终态

余项组1–5各有独立限定 ACCEPT、正常main推送及远端精确回读。最新组5 C=`d909473479143e831956d48280156a95828b2b2b`，T=`87b9404ea37589cca7880b976bb86db3aa2bd04f`。仅组6当前J19最终闭环未完成，不增加第二场、规模生产或文学质量门。

- `PUBLIC_METHOD_EQUIVALENCE_VERIFIED=NO`；`CNW_FULL_PRODUCTION=NOT_VERIFIED`
- 单场 `EXECUTION_INCOMPLETE`；修订稿 `UNREVIEWED_CANDIDATE`
- `EPISODE_LIVE_NOT_RUN / SPRINT_LIVE_NOT_RUN`；Chapter/Sprint/Arc-end只复用已签离线证据
- `USER_CREATIVE_ACCEPTED=PENDING_USER_READING`；Atom外部当前ChatGPT源码/结果审仍待

前10阶段实际materialized；Re-review五Lens及部分Verifier已付费成功，共享CNY10护栏中止后未提交最终阶段报告，不能记完整LiveE2E。

## 身份及真实消费

私有项目 `workspace/cangqi_cnw_public_restore_20261011`，同一工作单元 `CQ-J19-INSERT-01`，run `CNW-RESTORE-J19-CURRENT-20261011-02`。新合同SHA=`f6310429e96522e083e35afb7178e9d9139a4a883991428ae7a5ce0c13145c4d`；旧合同/run/原稿历史保留，未重写旧freeze。

| 当前来源/产物 | 字节SHA256 |
|---|---|
| Character Bible | `f97352160ac5af35499574acbc98267cd625fbadad04a6b647ff3254b3262133` |
| timeline | `139f8b3d98a544454317dd05dede8d12c1ce4da639cdc4202eab4821f2b54e84` |
| 未改master Canon | `a40c67b8d16c08a22caf5c554509cb7b4adc9a9f9c0c26ed2d974fe73ddde391` |
| Plot artifact | `e27240c5291dd402bf750278bc672e01f26373bf98b97df1f38ac68513299f01` |
| v0，1609可见字符 | `53ae037f5a8925200a87d0217c7072405cc3669d758c92948fea7a2ebf1a3c9e` |
| v1，1422可见字符 | `bdc98b87b6a22ada12e550b284f0a9baee9c9f247fb582b4d100f498911dbc57` |

实际请求证明：Plot/Cards/Brief读取当前人物资料；Cards/Brief消费真实前岗产物；Brief读取最新timeline T5–T8、完整NK reflection；Prose仅Brief与依本场说话者选出的声线，不越权读合同/整份Canon。Plot无预冻结Required Beats，由实际Plot设计；四个连续Key Scene是同一讲堂的连续时刻。

五Lens精确消费v0及各自规定来源；Character当前人物资料、Canon当前时间线均相符。Refine精确消费v0/Brief、16项confirmed、7项Completeness候选和已验证native CritiCS候选表达；真实response与v1逐字对应。Re-review五Lens及已完成Verifier均消费v1全文，规定来源精确当前文件；Completeness本岗位可复用反馈在后续Lens正常加载。

私有核验：`artifacts/current_chain_consumption_checks.json`、`current_chain_partial_real_evidence.json`。已完成消费者检查全部为真。API/raw文本、Windows artifact字节SHA及发布副本终端换行规则分别核对，不声称字节全部相同。

## 分阶段真实执行

| 阶段 | 实际结果 |
|---|---|
| Plot | 1次成功；native CritiCS plan-critique另5次成功 |
| Cards | 1次成功，实际Plot/当前人物资料消费 |
| Brief | 1次成功，另1次native NK；完整当前资料压入行动指令 |
| Prose | 3次成功响应保留；首笔过长未发布，有限完整重生成及正常续写形成1609字v0 |
| Layer1/2 | 本地项目规则实际运行，各0命中，不代表正文0错误 |
| 五Lens | 5次成功，22条Finding |
| 三反证 | 22×3=66次成功，16条保留 |
| Completeness | 首次截断失败保留；容量修正后1次成功，7项遗漏入Refine/本岗位反馈 |
| Refine | native text-refine另3次既有成功；CNW Refine1次成功，1422字v1 |
| Re-review | 5Lens成功，20条新Finding；20个Verifier成功，6条完整三票、1条两票；尚缺40个Verifier，未提交最终处置 |

成功CNW体系回执105条（含NK support1条）；另native CritiCS8笔及截断Completeness1笔账本调用。当前run账本114条：113 `SETTLED`、1 `SETTLED_OVER_BUDGET`；不能将105混同所有付费次数。native leader含拒绝选择内容，请求成功不等于成功选出文学方案。

首轮Character Finding1的correctness raw有重复同ID两行，现有parser确定性取首行；另外两票均保留，16项结果不因此改变。原票保留，不声称所有raw严格符合单票协议。复审parser要求单票；未执行票不补造。

## 实际运行发现的最小工程修正

1. `create_only` 返回 `provider_call=none`，不将准备说成已调用。
2. Prose过长在既有总计3次上限内完整重生成，仍仅Brief/相关声线及长度校验元数据；不足正常续写保留。不手裁、不重置次数、不提前Refine。官方未规定本地长度合同/次数，此为执行适配。
3. Completeness容量依实际confirmed/rejected集合调整，最多8000 tokens，官方未规定2500 cap。首笔2501输出、`finish_reason=length`保留费用/raw，不当成功JSON。该笔 `SETTLED_OVER_BUDGET` 是token cap violation，reservation/campaign未超10元。
4. native三次fresh ConversationChain使用部署LangChain `DEFAULT_TEMPLATE(history="")`。AST读实际模板，整组三条精确比较裸格式或空历史包装，单user消息，不任意剥包装。子进程成功先持久化 `NATIVE_RESULT_PENDING`、run名和不可变输入，再校验；失败重入不重复付费。既有3笔经 `read_native_result` 核input/output/依赖/ID/build/receipt后绑定，账本不变，记录 `artifacts/support/native-text-recovery.json`。
5. 中断记录 `EXECUTION_INCOMPLETE`、失败类型/代码及保留回执数，避免部分请求被说成完成。
6. live导出先核合同/产物证据，实际源锚点进入MD/HTML，HTML转义；未完成复审候选明确标 `UNREVIEWED_CANDIDATE`，不晋升或填创意接受。

## 费用、重入及导出

当前run占用CNY4.744819；共享活动CNY9.874291/10，剩余0.125709。历史unknown0.028333继续非零占用，不清零。真实reserve报 `CAMPAIGN_ESTIMATE_LIMIT_WOULD_BE_EXCEEDED`，未绕护栏或扩预算。

随后仅缓存诊断：HTTP禁止、全部新reserve人为禁止；前10阶段 `STAGE_REUSED`，复审25条原成功响应同身份读取后到缺失请求停止。此为禁付费重入，不冒称第二次真实预算事件。回执仍105条，ledger字节不变，准确失败状态保存：`artifacts/current_chain_cache_only_reentry.json`。

正式export无API生成私有 `deliverables/cangqi/<run>/`：初稿、候选修订稿、真实前后文MD/HTML、运行状态、操作说明。未推Git。`verify-live`准确拒绝 `LIVE_PIPELINE_INCOMPLETE: re_review: EXECUTION_INCOMPLETE`，导出成功不替代验收。

## 独立实际功能判断与限制

Controller分别对容量修复、native恢复方案/实现、Refine23项消费与原稿/响应绑定限定ACCEPT，最终收尾C/T待核。`story_state_fit`对Refine消费ACCEPT、完整终验RETURN（复审未完成）；`convergence_audit`只保留组6余项，不增加场数/方法/质量门。

用途部分达到：具体行动/回应形成局部互动，主角与一位角色性格得到体现；另两位较薄，后段静态重复及私人体感误归他人知情等瑕疵仍在。固定主线、地点和后续秘密主要守住，不能证明玩家喜欢或质量保证。

当期资料仍有提取遗漏：Character Bible第15行仍将齐宣王当前身份/称呼记待确认，原稿J19却明确老师对应齐宣王。复审出现错误司业替换建议、把新对白当提前泄露等票。不能手改正文配合错误意见；官方承载点是已有来源驱动人物事实/称呼提取，不是新增创作步骤。预算停止后未追加提取，不能声称所有当期资料准确无漏。

不改票、不手工打磨或凑票冒充方法等价。后续须按兼容身份恢复必要调用、完成正常复审处置；确有源资料纠偏仅按已有提取职责和影响范围处理。用户亲读和外部源码/结果审不代签。

## 离线覆盖与停止范围

最终146项相关离线通过：operations、chapter_arc、pipeline、maintenance、recovery、role_inputs、runner、generation、adapters、project_import、incremental_entry、export。新增覆盖长度次数边界、Completeness容量、包装整组匹配/混合修改拒绝、paid native pending恢复、中断/预算不误完成、锚点变更拒绝导出、候选未验收标识。

本轮工程修改和证据可有限签收/推送，不关闭组6、不记整体通过。未取得新预算或其他兼容实证前停止新增付费，保留全部raw与历史。
