# CNW 生产角色、合同与产物边界

## 方法与当前范围

固定方法为 `MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。
权威原件是 `templates/config/ai_roles.template.yml`、`workflow.template.yml`、Plot/Card/Brief 模板与 `docs/THREE_LAYER_REVIEW.md`。来源/blob 对照见 [固定来源](../reviews/CNW_ORIGINAL_SOURCES.md)，工程不冒称取得作者的私有代理系统。

本文是 StoryStudio 当前通用工程合同说明；真正的 schema 和读取以 `tools/cnw_contract.py`、`cnw_roles.py`、`cnw_review.py`、`cnw_recovery.py` 和 Runner 为准。原单场文档已在仓库外原字节备份，见 [08盘点](../evidence/ATOM08_READONLY_INVENTORY_20261014.md)。本文不改变历史合同或收据。

## 项目、工作单元与 Run

- Project：用户选定 DataHome 下的注册实例；显示名可重复，实例身份不能串用。
- Scene：明确一场的事件、起止状态、人物、节拍及创作空间。
- Episode：完整章节，Plot 决定有序场景及章作用、读者回报、Hook、Arc/连续性；不固定场数或编号。
- Run：绑定同一实例、工作合同、来源/Canon/Arc、Policy、Workflow、Provider 和实现身份。各阶段由真实上游产物构造，产物路径、SHA、请求及恢复记录写在私有 Run 中。

新合同由 `cnw_project.build_work_contract_v2` 构造 `cnw_work_unit_v2`，保留用户 locale、POV、人物、节拍、目标、限制和第五 Lens 职责。显式第五 Lens 文本及 `responsibility_sha256` 冻结在 `review.fifth_lens`；项目名不决定审稿内容。

| work_intent | 合法来源依据 |
|---|---|
| INSERT_BETWEEN | 明确选定不可变来源修订、Manifest/Index 和实际双锚 |
| ADAPT_SOURCE | 明确选定来源修订及行范围/JSON Pointer；无需双锚。规范化选值身份与 wire excerpt 字节哈希分别验证 |
| ORIGINAL_EPISODE | 本项目 Canon/Arc；首章无伪来源，续章绑定合法受控前章文本/身份 |

原 V1 与旧无新政策字段的合同继续使用其历史合法语义；不会补造 locale/锚、重写原 SHA 或把旧请求当新请求。

## 四角色允许读取

| Role | 作者直接读集 | 职责与产物 |
|---|---|---|
| Plot | 当前 Arc、Canon、character bible | 合同/来源准备材料按 work_intent 补充；输出作者 Plot heading 的章/场设计与真实动作节拍 |
| Scene Cards | 同 Run 的 Plot、character bible | 输出每场 identity/cast/start/end/required/forbidden/sensory/tone/connection |
| Writing Brief | 同 Run 的 Plot/Cards、character bible、style guide | 按公开 Brief/Canon 模板补充当前 Canon/timeline/world/glossary，生成 Active Canon、每场执行、声线引用、硬边界与风格目标 |
| Prose | 同 Run 的 Writing Brief、选中发声人物 voice samples | 只通过 Brief 接收创作要求，输出完整实际故事；不直接读全部来源、隐藏 Canon、Lint 禁词或审稿规则 |

`cnw_roles.AUTHOR_ROLE_READS` 和 `AUTHOR_TEMPLATE_READS` 明确读集与额外公开模板依据。不同项目资料不能进入同一请求；先取得上游可读非空产物和身份，不能用手写成功状态继续。分量、文体、POV、必需/禁止节拍逐级传递，不用摘要替代对白、行动和后果。

## 固定11阶段与审稿独立性

`plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review`。

| Review role | 允许素材与效果 |
|---|---|
| Lint 1 / Lint 2 | 对完整稿作表层/上下文检查，产定位证据，不改正文 |
| style Lens | Draft + style_guide / forbidden_patterns |
| character Lens | Draft + character_bible / voice_samples |
| plot Lens | Draft + Scene Cards / Writing Brief |
| canon Lens | Draft + glossary / timeline / world_bible |
| story_specific Lens | Draft + 本项目专属 Canon、合同冻结的第五 Lens 职责及适用任务视图 |
| 三 Verifier | 每 Finding 三个独立立场 correctness / character_consistency / continuity_plausibility，实际 scoped 来源及稿件 |
| Completeness | 全稿、前序问题/处置及任务要求；真实遗漏进入问题队列 |
| Refine | 原稿、冻结 Brief、确认问题与遗漏反馈；另存新版和修订记录，原稿保留 |
| Re-review | 全新稿重跑两层 Lint、受影响 Lens；新稿不能沿用旧稿 PASS |

五 Lens 请求互不看别的 Lens 意见。每 Finding 要有三种实际独立票；重复、缺票、错配拒绝。至少2票 `not_refuted` 才确认；证据不确定按上游优先反驳。不把没有 Finding 时的伪调用记为完成。Completeness 不自行改稿，Refine 不晋升 Canon。

## 篇幅与质量

新 V2 冻结 `unit.length_policy=ADVISORY`，用户数字目标/参考上下界完整保留，字数统计报告具体 Unicode 算法；超/欠参考不触发纯长度请求或拒绝。真实漏节拍、错误、未写完仍按审稿/Completeness 修订。空产物、传输截断、token cap、费用和权限门独立保留。旧无字段合同保持原严格语义及请求/恢复身份。

人物差异、现场行动、目标与阻力、结果和读者回报由实际内容和项目要求验收。工程状态、模型自评或文件存在不能证明故事达标。用户亲读是最终创意接受；正式晋升须独立批准和当前审查证据。

## 可选组件、费用与恢复

NK DISABLED 不要求 NK 事件/runtime/响应；ENABLED 的实际 Card/POV 结果进入 Brief。CritiCS Plot/Text 为 Plot/Refine 的独立辅助意见，不能替代任何 CNW 角色；启用但不可用/失败保留记录并阻断。

章节、注册标准操作及辅助消费者共用实际 RunAccount、slot、账本、累计预算/次数；UNKNOWN/PENDING 不清零。独立 Controller 预检、Owner Live/费用许可和创意批准分别核验。模拟票必须 `MOCK_ONLY / SIMULATED`，不能过 verify-live 或正式晋升。

恢复按真实输入/输出/实现哈希求出受影响阶段；保留旧稿、请求、回执、失败和历史版本。没有有效授权不能借缓存、pending 或重新预留来调用 Provider。导出保存可读候选及状态，不自动宣布生产验收或用户接受。
