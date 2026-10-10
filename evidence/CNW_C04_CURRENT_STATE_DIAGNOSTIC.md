# C04/C05：同一插点当期资料纠偏

固定方法：CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`，`templates/CLAUDE.md` Canon Extraction / Never overwrite source material、Canon policy、Character Bible / Timeline / Plot / Scene Cards / Writing Brief 模板。对应有限余项第5组；不是新创作阶段，也不是整体终验。

## 用途与停止范围

固定主线和关键情感转折之间的日常，依 Plot 的 breather/character beat、场卡的当下 WANT/Start/End/Required beats 和 Brief 的行动指令设计。验人物如何行动、选择、回应以及产生的局部变化。当前时点的亲历、他人告知、关系变化与未来禁区进入现有 Canon/人物资料/时间线；后续相关 Lens 按自身来源审查。玩家省叙不等于角色失忆。

官方未提供全部角色×时点×分支自动状态库，也不保证模型每次提取正确或玩家一定喜欢角色。局部资料和真实消费闭合后停止此项，不扩写第二场、不为一般文学瑕疵反复付费、不手改生成正文。

## 两次真实来源操作

当前私有项目的同一工作单元 `CQ-J19-INSERT-01`，选定三份完整既有原来源，复制字节核对后调用已有 Canon Extraction。原 SHA 分别为 `53c4f9c4f79aed2537928bf5c350d8c253c5783c7cc5d29536c9aa259b689223`、`7475dd87d6953d5dba6e6c09a5f3db0af69db18aeebf174b169bb31f7cbeadcc`、`9e412727dc19c28d10cf28a1467fe9e5b25cfd1c36d6880b1c2224b2b0bddbad`。全文和 raw 保留在 ignored 私有目录。

| 操作 | Run | Provider | input/output tokens | CNY |
|---|---|---|---|---|
| 来源提取 | `b6bfccb2de97bcbd1961d88f` | `e0e05e88-ff1a-453d-9da1-d0c3e0240f61` | 31652 / 6178 | 0.113292 |
| 独立审查后的有限勘误 | `1a4f7d6fba12669bd292e41e` | `3e33d330-8ce4-4919-990d-323534d428bd` | 35914 / 5123 | 0.113377 |

首次提取真实发现缺陷：认错旧表行目标、未有效取代笼统知识结论、无来源扩展跨场时空、把未来条件兑现写成当期完成。独立 `story_state_fit` RETURN。按官方提取职责加强 no-invention/确切旧句定位，重新追加有限有源勘误；没有删除或手改首次 raw/段落，没有改故事。第二次独立 **限定 ACCEPT**：必要自知与他人未知、已发生关系变化、当前插点及未来未兑现边界可供同一插点消费。少量编号/引用措辞和不依赖的伪待决保留诊断，不继续付费追零瑕疵。

## 真实身份与消费边界

- 两轮都追加到**既有** `90_canon/character_bible.md`、`90_canon/timeline.md`；两轮旧字节前缀与历史保留。不是仅写旁路报告。
- 当前人物资料 SHA=`f97352160ac5af35499574acbc98267cd625fbadad04a6b647ff3254b3262133`；时间线 SHA=`139f8b3d98a544454317dd05dede8d12c1ce4da639cdc4202eab4821f2b54e84`。
- master Canon 原 SHA=`a40c67b8d16c08a22caf5c554509cb7b4adc9a9f9c0c26ed2d974fe73ddde391` 未变。原稿/设计未变，未批准新 Canon/创意。
- Plot 正常 builder 已读取新人物资料；相关 Lens builder 输入含新段落。Cards/Brief **正式执行待第6组**，读取表存在不能冒称已经消费。
- 首次标准操作原身份无网络/无 reserve 重入成功。勘误成功回执的原请求身份也在禁止网络/reserve 下正常复用，账本不变。之后细纲用途澄清合法改变来源，不声称旧标准操作身份仍与新来源完全相同。
- 旧合同 SHA=`3196d3d326d1adab37c45a2caf7a652cf5fec9c3f173e2f99435051762b7781f` 与旧 run 保留。新合同 SHA=`f6310429e96522e083e35afb7178e9d9139a4a883991428ae7a5ce0c13145c4d` 指向当前人物资料；限定当前可见姿态不抹除既往亲历，用途加入有意义行动/选择/回应。前后锚、单场范围、篇幅、玩法保护不变，无冻结必需节拍。旧细纲字节已归档；新 run 才能证明读过新资料。

## 实际机械修正

`append_sections` 避免模型转抄已有混合换行字节。真实首次输出的保护性政策说明又触发了旧全文 LOCKED 正则，故将判定改为明确记录状态：保留 master/原稿独立保护，状态字段/标题/表格 LOCKED/Canon-promoted/锁定，以及官方人物表 `Canon Status=Canon` 均拒绝；一般政策说明和 Provisional/Deprecated 不误锁。不增加自动解锁或逐条改锁定事实的机制。

当前 138 个相关离线检查通过，涵盖标准操作11、Chapter/Arc4、pipeline16、maintenance10、recovery12、role inputs11、runner22、generation22、adapters11、project import9、incremental entry10。一次测试模块名称误写导致 import error，正确完整命令重跑138通过；不把失败隐藏为成功。

本组总新增 CNY0.226669；共享活动账本计入历史未知非零预留后 CNY5.129472，仍使用同一 CNY10 护栏。`PUBLIC_METHOD_EQUIVALENCE_VERIFIED=NO`（第6组尚未闭合）；`USER_CREATIVE_ACCEPTED=PENDING_USER_READING`。
