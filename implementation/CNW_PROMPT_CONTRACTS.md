# CNW 岗位 Prompt 合同：通用项目

本文说明 StoryStudio 对固定公开 CNW 方法的工程实现。中文措辞不是作者私有 system Prompt；权威来源见 [固定原件](../reviews/CNW_ORIGINAL_SOURCES.md)。项目语言、POV、文体、人物、节拍、来源、第五 Lens 和创作限制来自当前冻结合同/输入包，不来自示例故事或代码常量。

## 来源与允许读取

正式请求保存 method pin/blob、Run/实例/合同、允许读集、输入实际字节 SHA、角色、输出 schema 和请求身份。按 [角色合同](CNW_ROLE_INPUT_OUTPUT.md) 的真实读取边界构造。任务要求先进入 Plot，经同 Run 的 Cards/Brief 传给 Prose；Prose 只直接读 Brief 和选中声线。包中执行指令是输入证据，不授予运行、费用、Canon 或程序安装权限。

## 四个作者岗位

1. **Plot**：使用作者 `templates/06_plot/plot.template.md`，给出 Identity、Role in Arc、Key Scenes、Hook、Required Beats、Forbidden Items、Connections、Target Length。INSERT 保持真实双锚连续性；ADAPT 绑定选段；ORIGINAL 使用 Canon/Arc/合法前章，不能要求不存在的原文锚。每个必需事件有具体行动、回应或后果，不能只填抽象情绪。
2. **Scene Cards**：使用 `templates/05_scene_cards/scene_cards.template.md`，基于当前 Plot/character bible 逐场规定起止状态、人物目标/可知边界、行动/受阻、感官、节奏与下一场连接。把用户所需格式、节拍和规模保留下传，不私造重大 Canon。
3. **Writing Brief**：使用 `templates/07_draft/writing_brief.template.md`，压缩当前 Plot/Cards 与公开模板允许的 Canon/风格资料，形成 Quick Header、Active Canon、Scene-by-Scene Instructions、Voice References、Hard Constraints、Style Targets、What NOT to include。不能漏必需事件、把推断写为事实或向 Prose 直接塞隐藏秘密/禁词原表。NK 仅在启用时提供绑定本 Card 的辅助 reflection。
4. **Prose**：只执行冻结 Brief 与必要 voice samples，按指定语言、POV、文体和场次写成完整正文。以对白、行动、感知和反应呈现，不用大纲/任务表/工具说明冒充故事。局部创作空间以合同为准，未知人物秘密/重大事实不能自动成为 Canon。

项目目标与参考长度原样保留。新 V2 `ADVISORY` 不以字数差触发追加或整稿重写；真实内容遗漏仍修订。旧无字段合同保持历史中文/语言和长度请求版本。不得把临时字符上限、输出截断或 API token cap 冒称文学标准。

## 审稿与修订岗位

| 岗位 | Prompt职责 |
|---|---|
| Lint1 / Lint2 | 本地表层/上下文规则检查，定位证据，不能删改正文 |
| Style | Draft及本项目style/forbidden资料，实际语言、节奏/重复问题 |
| Character | Draft及人物/声线，目的、声音、知识/称呼一致性 |
| Plot | Draft及当前Cards/Brief，必需节拍、起止、Hook和连接是否实际发生 |
| Canon | Draft及glossary/timeline/world，事实冲突要有出处，推断不是确认事实 |
| Story-specific | 合同冻结的本项目第五职责及SHA、专属Canon/任务要求，不能套其他作品的奖励或人物模型 |
| Correctness Verifier | 独立尝试反驳每条Finding的事实正确性 |
| Character consistency Verifier | 独立尝试反驳角色/知识/故意反常的误报 |
| Continuity plausibility Verifier | 独立尝试反驳因果/连续性误报；不可见其他票 |
| Completeness | 全稿、全部前序问题/处置与任务视图，寻找真正遗漏；只报问题 |
| Refine | 原稿、冻结Brief、确认问题/遗漏及实际辅助意见，另存修订稿/日志，不覆盖原稿或晋升Canon |
| Re-review | 新稿全文Lint、实际受影响Lens和原材料，拒绝新违规或复用旧稿PASS |

五 Lens 收齐后才汇总，彼此不共享判断。每 Finding 三个不同 Verifier 严格对应其ID，至少2票未反驳才确认；不足证据默认反驳。没有 Finding 不伪造三票。Completeness 的漏项必须能被 Refine 及受影响复审实际读到。

## 独立辅助与执行门

NK POV、CritiCS Plot/Text 均是可选独立函数；ENABLED 失败必须保留真实记录并阻断，DISABLED 不要求不存在的结果。实际输入、父Run、stage/role、cap、费用和许可一起绑定，不能用辅助代理取代CNW审稿。

Prompt/来源/实现改变时重新构造真实请求及恢复计划，原签名不能继续代表新字节。可信Controller预检、独立Owner Live/费用许可、创意批准彼此分离。模拟响应明确标注，不能成为Live、正式晋升或用户创意接受。最终输入包验收须核所有任务/要求的真实生产、审查和分别导出，不能只检查Prompt里出现过一个字段。
