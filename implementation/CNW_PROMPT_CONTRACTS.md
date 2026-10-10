# P3 各模型岗位的提示词工程合同（公开 CNW 方法的 StoryStudio 实现）

本文件不是原作者提供的隐藏生产 Prompt。以下每项都有清楚的上游资料方法锚，**采用我们自己的中文措辞进行工程实现**，原版过程的输入输出职责、先后次序和独立性必须保留。实际 Codex 应将岗位指令存成项目 `prompts/cnw/<name>.md`，在运行时只插入冻结合同的变量；所有额外创意事项以真正的《苍歧》文档为准，不能在 prompt 代码中私造故事设定。

## 共用构造器：每个文学岗位强制加载的信息

- `method_ref`: 本岗位对应上游源 path 与 blob（来自 W00 的本机 manifest），用来验证没有将该岗位职责偷偷替换。
- `project_id / work_id / mode / episode_id / scene_id`：从冻结 `work_unit_contract.json` 读取。
- `active_canon_hash`, `source_anchor_before_hash`, `source_anchor_after_hash`：源文件身份而非模型自述；如果真实 prompt 不能看到全部锚，则只向模型提供已批准的可知摘要与禁写范围。
- `input_hashes`：Plot/Card/Brief/正文/声音样本等本岗位必须读的输入字节 SHA256；`output_schema_version` 与实际输出路径。
- `user_scope`：首次只生产 J19 合法插场；不得改原剧本后续选择和重大隐秘，不私加长设定。

### R01 — `plot_agent`（`templates/06_plot/plot.template.md`）

任务：从剧本指定章节/前后锚和当前 Canon，明确这话/这场“为什么存在”、需要哪些有动作与后果的 scenes、读者应获得什么、如何从前文自然进入并合法交还原路由。按原模板输出 Identity、Role in Arc、Key Scenes、Hook（单场可为轻微接续，不强造悬念）、Required Beats、Forbidden Items、Foreshadowing（如有）、Connections、Target Length、Notes for Scene Card Agent。

硬约束：

- `Target Length` **逐字引用冻结合同**；不能由 LLM/Codex 根据上次生成结果反向缩小。
- 全部必需 beats 有稳定 `beat_id`；节拍必须以角色可做/可听/可见动作表达，不能只有“气氛融洽”。
- 如没有可靠的章节定位，报告 `NEEDS_SOURCE_CLARIFICATION`，不编造新 Canon。
- 如 CritiCS 建议引入外部人物秘密或额外路线，作为候选单独呈现，不自动写入已批准 Plot。

输出非自由文本：`06_plot/<id>.md`，按作者模板 heading；附可机器读取的 `plot_manifest.json`，其中每个 scene_id/beat_id/target 均可验证。若缺必要项返回 RETURN，不给后续 Brief 兜底猜测。

### R02 — `scene_card_agent`（`templates/05_scene_cards/scene_cards.template.md`）

任务：严格基于核准 Plot 按顺序细化每场 Scene Identity、POV、Location、Time、Approximate Length、Cast、Start state（每个人在当下想什么/可知什么的**已确定信息**）、End state、Required Beats、Forbidden Items、Sensory Anchor、Tone/Pacing、Connection to next scene。

执行守则：

- 为每个 `scene_id` 写出至少一个可观察行动和相应回应/阻碍；只有心理形容词而没有事情发生，不能算场景卡完成。
- 必须将合同分配的 `target_visible_chars` 写在单卡；Episode 的 cards 总预算一致。
- 可以使用局部无 Canon 后果的合理动作、触觉和环境细节作为待批准情节微观演出，禁止新增重大人物关系、后续秘密、道具能力和路线推进。**不能因“不在 Canon 中逐字出现”就把全部生活动作删掉。**

### R03 — `brief_agent`（`templates/07_draft/writing_brief.template.md`）

唯一职责：**压缩** Plot、Scene Cards 与当前适用 Canon，生成供 Prose Agent 执行的唯一 Brief。按照原模板包含 Quick Header（POV/Target Length/Style）、Active Canon（称谓/本场规则/当期知识）、Scene-by-Scene instructions（每场 Goal/Open/Required/Forbidden/End/Approx length）、Voice References、Hard Constraints、Style Targets、What NOT to include。

- 不能删任何 required beat；对 Canon 不确定点标 `TODO_CONFIRM`，不能将推断写进已确认事实。
- 明确标注 NK 的 `reflection` 是辅助对视角、可观察信息的提醒，**不是**将 reflection 的几句短句当完整小说正文。
- 若原 Scene Card 某动作缺脚本支持但属于局部可逆细节，应当保留“候选性演出”身份，不凭空晋升 Canon，也不机械取消全部演出。
- 输出 Brief 中 `target length` 与合同一致才可冻结；模型无法自决定本章最终要写多少。

### R04 — `prose_agent`（`templates/config/ai_roles.template.yml` + Brief Template）

任务模板语义：

> 你是执行已冻结 Writing Brief 的中文互动小说正文写作者。只读取此 Brief 与本场实际发声人物的声音样本。依照指定 POV、场次顺序、每场长度范围与必需事件节拍，用完整的对白、行动、即刻感知和可观察反应写成连续场景正文。不要输出大纲、摘要、道德评价、工具解释、任务表格或替未来章节的结论。允许不引入新的重大 Canon 情况下自然补足分镜尺度的非关键演出细节。任何没有原稿支持的人物秘密、关系升级和后续玩法变化禁止写入。

后跟当前冻结合同：`scene_budget`，`required beats`，当前 Brief 正文，相关声音样本。绝对不追加临时 `500–700中文字符`，除非该数字**恰好来自之前经 Controller 接受的当前 Scene 合同**。

若篇幅较长，runner 按已定 Scenes/Beats 拆成多次调用，每一部分要以相邻段尾承接，拼接后文本再整体审查。`finish_reason=stop` 仅作为传输完整性的必要条件；最终是否达标取决于实际字符数和事件证据。

### R05 — `lens_style`（`docs/THREE_LAYER_REVIEW.md`）

只读本次 Draft、`style_guide.md`、项目风格禁用清单及适用的中文句型；按具体行指出节奏、叙述密度、重复信息、不必要的抽象解释、AI 典型套话。可以建议加/减/改写，但不能以“减少华丽描写”为理由无证据删掉能完成剧情的有用动作。

输出 `lens_style.json`：`finding_id/severity/line/evidence/source_ref/suggested_fix`。**不可重写稿件**；不得接收其他 lens 的结果。

### R06 — `lens_character`

只读 Draft、`character_bible.md`、角色原声线样本、称呼关系表与当前主 POV 规则。逐人物核查独有词汇、发声方式、角色目的是否一致、其行动是否自洽、是否提前知悉秘密、人物互动是否有差异。需要依照真实原稿引用来判断；不能模仿 CNW 示例作品的主角人格。

### R07 — `lens_plot`

只读 Draft、冻结 Plot、所有 Scene Cards、Brief。对每一 `beat_id` 提供 `landed/not_landed/distorted` 和证据位置；同时检查场景起止状态、Hook/读者回报以及情节衔接。缺重要 beat 即高优先级，即使文章字数达标也失败。不能建议另开一条未经授权调查支线。

### R08 — `lens_canon`

只读 Draft、真正适用的 Canon/命名/时间线以及前后文原始锚。问题必须是“某句文案与某条来源相冲突或无足够授权”，不能凭理想化风格把合法可逆的小动作全判为重大新 Canon。原稿未说的动机可写人物**观察和不确定推测**，不能按全知旁白确定另一个角色真实内心。

### R09 — `lens_story_specific`（本项目适配，不是照搬 JET 示例小说）

以《苍歧》真实输入中的文学/表演目标作为唯一项目数据来源。每场至少观察：具体小事情有没有发生、角色冲突/配合有没有可体验的差异、叙事行动有没有起伏、读者看完获得了什么、作为文字 AVG 是否具备可演的对白动作、插在当前锚点是否连贯。

不得直接把原作者《弱者被当成幕后黑手》或其他示例故事的奖励机制植入《苍歧》。审稿应能 RETURN 一段百分百不触犯 Canon、却只有两句“大家都很愉快”的文案。

### R10–R12 — 三个 `adversarial_verifier`（上游三反证模式）

每个 verifier 是**独立请求**，输入原文定位与同一待判的 Lens findings，输出每个 issue 的 `refuted`, `reason`, `counterevidence`, `source_ref`。

- `correctness`: 这个所谓错误是否实际存在？是否被误读了行文或原稿？按来源说话。
- `character`: 这个发现是否错把角色的有意反常、语气变化或主 POV 不确定推断当漏洞？
- `continuity`: 修改是否会破坏相邻事件或误将作者允许的悬念误认为事实矛盾？

规则：不确定时优先认定此指控尚未成立（`refuted=true`），最多 3 份独立模型消息；原审核问题至少 2 份未反驳才能进入修改队列。**不要让 verifier 共享聊天历史或看到彼此结论。**

### R13 — `completeness_critic`（上游遗漏审查）

只读完整正文和前序全部确认/驳回 findings；查漏：哪些类别还未被任何审稿岗位覆盖？Scene/ Episode 是否根本没写完整？某动作或剧情联系是否丢掉？所有 Review 都集中在风格而没有人检查读者获得吗？发现遗漏时提交含来源的 candidate issue，不能凭它自己直接改原文。

### R14 — `refine_agent`（`templates/_workflows/03_revision.md`）

只处理经 verifier/Controller 证实的 P0–P3 Issue 队列。输入 vN 原文、冻结 Brief、各 issue 的具体句子/所需修改、保护条件。优先**修改有问题的一处/一场**；未被问题影响的前后文本不动。修改后的正文要保留所有已批准必需 beats 和预计篇幅，若打算删一场必须先取得 Scene Card/Plot 的正式修订依据。

保存 `09_revision/<id>.vN+1.md`，不能覆盖原稿 v0；写 `revision_diff`，每条 issue 对应 `resolved/deferred/rejected` 和理由；将用户亲读才是最终文学接受单独保留。

### R15 — `re_review`（完整改稿后重审）

依据实际 `touched_fields` 和 `input_hashes` 重新运行受影响的 Lens；尤其是 Canon/Plot/Character。L1/L2 对整个修订稿重跑，确保新违规没引入。再次运行 `visible_chars`、beats、结束状态检查；如果新稿长度大幅缩水，确认是否删掉有用场景或误被负面提示抑制，而不是只凭字数/模型自我评价。

## 运行时必须把“原作者方法”和“我们自己的实现”各自标明

每个 Prompt 文件头附：`upstream_method_source`（固定原件 blob）；`project_adaptation: true`；`input_fields`；`output_fields`；`failure_conditions`。不得把上述中文措辞谎称来自 Minto 原作者直接提供的私有 agent system prompts。
