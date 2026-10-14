# CNW 原作者公开资料：固定来源、提取范围和方法身份

**审查范围**：截至本工单编制时核查到的原作者公开 GitHub 固定提交，不依赖 README 的最新变动。

- 项目：`MintoTsukino/claude-novel-workflow`
- 固定 Commit：`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`
- StoryStudio 当前固定 Git 子模块：`third_party/claude-novel-workflow`，Gitlink = 上述 commit。
- 重构前StoryStudio回归基线：`26b72cea21dce45eede21cffddd4e75307d75652`，Tree `535496ba3b8a331e12d0e5e161b15bf21a25393e`。冻结副本只读；当前候选以实际main及独立精确签收为准，不回退工作树。
- 参考资料必须通过 `tools/capture_cnw_reference.py` **从本机固定子模块按字节复制**至 `runtime/reference/cnw_97ad71fe5e5e/`，输出逐文件 Git blob、SHA256、字节数、manifest 的 SHA256。不复制作者小说正文到公开仓库。
- 下表保存固定原件blob身份。实际本地提取/验证由capture工具、manifest及当期证据证明；干净clone须重新bootstrap。本文不是生产或最终包验收。原历史措辞在08修改前原字节归档中保留。

## A. 权威级别和用途

| 优先领域 | 权威原文件 | 已核查的源文职责 | 在 StoryStudio 应产生的功能 |
|---|---|---|---|
| 作者总体定位 | `README.md` | 公开的是方法、模板、示范项目和文档，不承诺开箱即用的自动小说工厂 | 实现自己的驱动器；不能假装拿到了作者的私有 89-agent 工具链 |
| 原作者实际单话 SOP | `example_project/00_meta/episode_production_manual.md` | 单话 Plot、Scene Cards、Brief、正文、Review、必要 Revision、状态/索引；作者日文项目普通一话约 5,000 字，短约 4,000，长约 8,000；不凑字数 | 为当前项目的 **scene/episode** 各自明确规模、节拍分配、作品验收；日文字数不是直接套用的中文字数 |
| 通用角色职责 | `templates/config/ai_roles.template.yml` | Plot Agent / Scene Card Agent / Brief Agent / Prose Agent 读什么、写什么，审稿岗位留待项目扩充 | 分离生产阶段与模型上下文，Prose 只接 Brief + 需要的声音样本 |
| **完整通用流水线** | `templates/config/workflow.template.yml` | `plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review`；5 lenses；3 verifier；阈值 2 | 作为 W04–W09 的执行状态机合同，不删关键阶段 |
| 章 Plot 数据设计 | `templates/06_plot/plot.template.md` | 章节角色、3–6 key scenes、hook、required beats、forbidden items、foreshadowing、前后衔接、target length | `plot.md` 带任务长度与必须发生事件；先检查 Plot 再下传 |
| 分场卡数据设计 | `templates/05_scene_cards/scene_cards.template.md` | 每场 identity、长短、start/end state、required beats、forbidden、sensory anchor、tone/pacing、next-scene | 每一场有独立规模和动作节拍，合计到章目标；不因“禁止增设定”删光可演细节 |
| Writing Brief | `templates/07_draft/writing_brief.template.md` | 本章唯一执行包，`Target length`、按 Scene 具体分量、当前 Canon、称呼、POV、voice samples、禁写条款 | Prose Agent 不直接乱读整份隐藏后文，不自行改写任务长度 |
| 正文方法 | `docs/GETTING_STARTED.md` + `docs/PHILOSOPHY.md` | Canon 优先、先人工小批验证后自动化；Prose Agent 在规范范围内自由成文，Review 去抓缺陷 | 正文由 Brief 驱动；不得把临时脚本的 500–700 字当正式生产目标 |
| 三层审稿 | `docs/THREE_LAYER_REVIEW.md` | Layer1 简单 lint，Layer2 带上下文 lint，Layer3 五独立 lenses；随后三方反证、Completeness、Refine、受影响部分 Re-review | CritiCS 是**新增插件**，不替代 CNW 原审稿岗位 |
| 批量验收 | `templates/08_review/batch_review.template.md` | 每 5 话批评和分数/发现/反证/漏项/下批注意事项 | 实际支持 5 话批次合同与批量审阅，第一轮只做离线验证，不越权生成五话 |
| 修订与晋升 | `templates/_workflows/03_revision.md` + `templates/09_revision/*` | P0–P3、保留旧稿、单独保存修订稿、经审核再晋升正本、日志 | 不用删掉动作/缩到百字的方式“修复”，不覆盖旧版本；章节正本在 `07_draft/episodes/` |
| Canon 校核 | `templates/_workflows/04_canon_audit.md` | 冲突/模糊/缺项，提供源行，不自动发明冲突的“真相” | 主审 lens 严格引用当前项目原稿，而不是凭故事猜测补设定 |
| 质量判定示例 | `example_project/00_meta/manuscript_review_rubric.md` | 致命问题→100 分→pass/revise/rewrite；80 分及以上通过、65–79 返修、低于 65 重写，为作者个人日文故事的标准 | 复用评审结构，但当前项目的评分指标/Reader Reward 必须按本项目剧情落地，不能套作者主人公专属指标 |
| 导入与交接 | `docs/EXISTING_PROJECT_IMPORT.md`、`templates/_workflows/01_first_import.md`、`05_handoff.md` | 保留源稿，CONFIRMED/INFERRED/TODO_CONFIRM，handoff 只记录事实 | 保留已完成当前项目Canon 导入与旧 P2 证据，续接下一个 run |
| 作者实际样板（仅本机私用） | `example_project/00_meta/sprint_goal_arc02_production.md`、`example_project/07_draft/ep001_writing_brief.md`、`example_project/05_scene_cards/ep001_scene_cards.md` | 看实例如何做篇幅和分镜分配；内容专属其他小说 | **仅学字段粒度和方法**，不得把人物/世界观/句子复制成当前项目内容 |

## B. 已核对的重点 Git blob 身份

下表 SHA 是原固定提交的 Git blob ID（不是文件的 SHA256）；W00 的脚本会产生真实 SHA256，二者不混同。

| 上游原始文件 | Git blob SHA-1 |
|---|---|
| `README.md` | `0e70b25492c0a43c94814a34a6b2f3a997fc2f32` |
| `CLAUDE.md` | `d8f7a27b1683614bd4a54aaa952049c3ccfc0f85` |
| `LICENSE` | `e900c48410bda2c2eb5a3d780d3c8ffc6e6d12ca` |
| `docs/ARCHITECTURE.md` | `89bdf2d8e4dabc223fcf91969ebaa5596ad51864` |
| `docs/GETTING_STARTED.md` | `3496d75c56bf13c5b9e834fbe98df9c539cdfec3` |
| `docs/EXISTING_PROJECT_IMPORT.md` | `25a28031c203f716fcb9c9e7b174acb445e66c94` |
| `docs/HOW_TO_ADAPT.md` | `5cbd6de30a6acfb1334e414dd747a74b96f3c88a` |
| `docs/THREE_LAYER_REVIEW.md` | `d03488d15f1a7841f442119237aff6d6148020df` |
| `docs/PHILOSOPHY.md` | `f45cb65f313e87ba7c46a0b1848f6bd25d6806e9` |
| `docs/CASE_STUDY.md` | `51319f90e79242f644c71e71e421d8f1dba1f0e` |
| `example_project/00_meta/episode_production_manual.md` | `fbc51bd35b347ee864d0ac938353e2ff524d0e55` |
| `example_project/00_meta/manuscript_review_rubric.md` | `c4dfc2c2e43e869d2be3da90661054efcd6bc2f0` |
| `example_project/00_meta/sprint_goal_arc02_production.md` | `be6e59623c2f742d286ee4dd48489c3e32218721` |
| `templates/config/ai_roles.template.yml` | `8ec31cb93cb0be1913579cc5cb05de45460988f8` |
| `templates/config/workflow.template.yml` | `146ea01a484cc0578cf290478b3941599ad7fb15` |
| `templates/06_plot/plot.template.md` | `8eb22fa6221351c2b614a3ae7d5dc4a53d3e8688` |
| `templates/05_scene_cards/scene_cards.template.md` | `b003a987ac1bd5eb1ae6f8dcf7dceffdfdfeaf5d` |
| `templates/07_draft/writing_brief.template.md` | `d67e3c4539eaea5bbcce904f3eb3ee42ff1e2fc5` |
| `templates/08_review/batch_review.template.md` | `24ba804c4807e0e535eee07a00c46d58ff10fd5a` |
| `templates/09_revision/revision_plan.template.md` | `759f418a3b89e2040e4228931ee81aa8baf365b8` |
| `templates/09_revision/revision_log.template.md` | `52076628d5431fb9a576faabd91b177d591a4219` |
| `templates/_workflows/03_revision.md` | `cae774e2582b09bdeaa7e80e6a7831ab4053dce5` |
| `templates/_workflows/04_canon_audit.md` | `da2afada0be6b6e66892bc2c9625b7fd70a0c5f5` |
| `templates/_workflows/README.md` | `afe16e553bef171f551c4f82c43a14f86c0aad71` |

原始源码 URL 统一形式：
`https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/<相对路径>`。

## C. 必须看清、不能靠猜的差别

1. **作者的示例作品文字数量 ≠ 全项目固定产量**：原实例单话 4,000–8,000 日文字符，单场实例分配 600–1,400 日文字符。数字是以故事目标为前提、先在 Scene Card/Brief 确立的规划，不能拿它自动覆盖中文 AVG 对话密度。
2. **作者的示例评分与通用配置不同**：`manuscript_review_rubric.md` 示例 pass=80；通用 `templates/config/workflow.template.yml` 的 `sprint.pass_criteria.min_score=75`。这两个文件层级不同，不能声称全部为同一个统一硬阈值。StoryStudio 项目质量阈值须在新生产配置明确选择，且“致命伤”一票否决。
3. **作者的五个 `_workflows/` 只负责导入/增量维护/修订/Canon 审计/交接，不等同于生产 Pipeline**。真正生产角色在 `templates/config/ai_roles.template.yml` 和 `workflow.template.yml`，审稿职责在 `docs/THREE_LAYER_REVIEW.md`。
4. **五个 lens 是独立看原文的评审角色**，不是 Writer 或工程 Controller 在一条消息里连续列五个观点；Verifier 3 个独立裁决来源，默认优先证伪主审发现。
5. **原作者不要求一直写到正好达到某个字数**：适用的安全语义是写作之前有分量规划、写作后检查欠产量与所需节拍、允许有预先依据的例外，不以水文凑数。
6. **JET 是可选的故事设计系统**（`docs/HOW_TO_ADAPT.md` 与 `docs/ARCHITECTURE.md` 都明确可以不用），不得把示例小说 JET 的人物心理模型未经适配直接装进当前项目。
7. **原项目以 Claude Code 为常见环境**，而当前 StoryStudio 的创作 API 限定 DeepSeek Flash：可以按公开操作方法构造“实现”，但不能宣称复现作者原运行器内部调度性能与文学成绩。

## D. 关键文本位置（行号固定于上述 commit）

| 文件与原始位置 | 实际方法/约束 |
|---|---|
| `episode_production_manual.md:9–17` | 每话 SOP：Plot→Scene Cards→Brief→Prose→Review→Revision→Index |
| `episode_production_manual.md:22–28` | 日文项目标准 5,000，允许 4,000/8,000，不为字数注水 |
| `episode_production_manual.md:575–594` | Scene Cards 中显示单话目标与分场长度预算 |
| `episode_production_manual.md:635–704` | Brief 中必须有目标字数、人物口吻、章节读者回报与必需信息 |
| `episode_production_manual.md:737–835` | Review 的合格/返修和 Revision Plan |
| `writing_brief.template.md:11–18, 49–65` | `Target length`、逐 Scene `Approximate length` |
| `scene_cards.template.md:10–58` | 每场目的/分量/开始结束状态/必须节拍/禁止事项 |
| `plot.template.md:11–73, 101–107` | 剧情范围、场次、必须节拍、hook、目标长度 |
| `workflow.template.yml:4–26` | 正式流水线 11 个环节、5 Lens、3 Verifier 与阈值 |
| `ai_roles.template.yml:3–36` | Plot / Card / Brief / Prose 单职能与源文件输入 |
| `THREE_LAYER_REVIEW.md:11–19, 63–77` | L1、L2、L3 及五独立审稿视角 |
| `THREE_LAYER_REVIEW.md:108–148` | 三路对抗复核、遗漏审查、Refine 与局部复审 |
| `manuscript_review_rubric.md:29–65` | 主题专属致命问题和 pass/revise/rewrite 机制 |
| `templates/_workflows/README.md:43–47` | 明确五工作流不是多智能体生产 Pipeline |
| `templates/_workflows/03_revision.md:8–57` | 先计划，旧稿保护，修改稿单独保存，再决定晋升 |

## E. 原文资料使用限制

原始源码/公开文档按各自 LICENSE 保留署名、固定来源、SHA，并只在本地私有 `runtime/reference/` 给开发系统读取。不要把其他作者 `example_project/` 的故事 Canon、对白、章节正文复制到当前项目生产内容。方法参考与示例小说内容分开；不把作者示例人物/正文安装成新项目模板或随故事交付再分发。用户输入包及最终产物的范围以实际声明任务和R5终验为准。
