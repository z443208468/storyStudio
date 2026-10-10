# 独立设计审查：StoryStudio 空库重建的高影响事实/前提/风险

> 本文件是**研究者的静态设计核查**，不是Codex执行后的独立Reviewer验收，也不是用户Controller签收。仅根据实际公开GitHub原字节与官方文档得出；本地Windows状态、Downloads、运行费用与故事效果尚未观测。`FACT`=源文或真实远端可读；`INFERENCE`=有依据但未现场实证；`UNKNOWN`=证据缺失。审查只挑会致使目标无法实现、引起误解、造成费用/版权/功能质量风险的大问题，路径/拼写等执行AI能自行修的机械事不列重大缺陷。

## 1. 当前可验证的权威来源

| ID | 事实 / 证据原件 | 性质 |
|---|---|---|
| R01 | `storyStudio` main=`06c66de7c7f18263039ea19a47e84c29716cde4b`，empty tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`；提交信息 `Reset repository to empty baseline` | FACT（**远端**） |
| R02 | `mvp` main不含当前产品根`AGENTS.md`；`perf/r667-migration-20261008@2f3d6f9...` 含 `AGENTS.md` R66.9 现行计划指针，按当前说明AT07已FINAL、AT08运行中；该状态由AGENTS文本声明，不等于现场实证 | FACT（分支与文本）/ UNKNOWN（其当前本地运行） |
| R03 | `mvp/docs/governance/GOVERNANCE.md` 的 `00A`是 B01–B12 黑名单，`00B`分提交/Controller验收，`00C`工程与功能证据分离；当前R66.9另规定唯一Writer与仅消息只读Reviewer、逐Atom接受和远端SHA/tree核对 | FACT（文件原文） |
| R04 | CNW原仓 `MintoTsukino/claude-novel-workflow@97ad71fe...` `templates/_workflows/README.md` 明确5个MD不是scripts； `GETTING_STARTED.md`强调少量人工校准后才自动批量；具体篇章为Arc/Plot/Scene Cards/Brief/Prose/Review | FACT |
| R05 | CNW `LICENSE`把 `docs/`、`templates/`等规范授权为CC BY 4.0，但排除实质性示例剧情、场景卡、Plot、Canon等的复制/衍生授权 | FACT |
| R06 | NK原版 `lib/openaiServer.ts` = `createOpenAI({apiKey})`；`app/api/generate-perspective/route.ts` 调用 `openaiProvider("gpt-4.1")`；README要求OpenAI Key而非Flash | FACT |
| R07 | CritiCS原版 `critics/setting/chatsetting/gptsetting.py` 有 `verbose=True                       s`；`chatsettubg`默认`gpt-3.5-turbo`；`storygen/common/llm/llm.py` 将OpenAI api_base设到`https://api.openai.com/v1`；requirements含旧`vllm==0.1.7`和`openai==0.28.0` | FACT |
| R08 | DeepSeek官方文档当前Flash模型ID是 `deepseek-flash`、其OpenAI兼容base URL为`https://api.deepseek.com` | FACT（实时官方公开资料） |
| R09 | 本轮尚未读取用户 `D:\CangqiStudio\StoryStudio` 工作树、真实Downloads或当前API Key、显卡/驱动/WSL和供应商账单 | UNKNOWN |
| R10 | CNW研究/作者成绩只是另一条件下的实践，不构成《苍歧》+Flash+原版NK/CritiCS现在有效的内容质量证据 | FACT（证据适用域）/ INFERENCE（系统效果未知） |

原文入口：

- MVP活动：[AGENTS.md](https://github.com/z443208468/mvp/blob/perf/r667-migration-20261008/AGENTS.md)；[R66.9 MASTER](https://github.com/z443208468/mvp/blob/perf/r667-migration-20261008/plans/packages/G3BB_R66_9_ARCHITECTURE_EXECUTION_20261009/MASTER_PLAN.md)；[R66.9 STRICT](https://github.com/z443208468/mvp/blob/perf/r667-migration-20261008/plans/packages/G3BB_R66_9_ARCHITECTURE_EXECUTION_20261009/STRICT_SEQUENCE_AND_BUDGET.md)；[旧到新版治理参考](https://github.com/z443208468/mvp/blob/perf/r667-migration-20261008/docs/governance/GOVERNANCE.md)。
- CNW：[许可证](https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/LICENSE)；[Getting Started](https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/docs/GETTING_STARTED.md)；[三层审稿](https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/docs/THREE_LAYER_REVIEW.md)。
- NK：[原Provider](https://github.com/zhangchaodesign/narrative-keyframing/blob/b857f34b7d371ae82c30e00eb021884c14d08ae9/lib/openaiServer.ts)；[原视角Route](https://github.com/zhangchaodesign/narrative-keyframing/blob/b857f34b7d371ae82c30e00eb021884c14d08ae9/app/api/generate-perspective/route.ts)。
- CritiCS：[原gptsetting](https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/setting/chatsetting/gptsetting.py)；[原API实现](https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/storygen/common/llm/llm.py)；[原依赖](https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/requirements.txt)。
- 供应商：[DeepSeek首次调用](https://api-docs.deepseek.com/zh-cn/)；[DeepSeek模型/定价](https://api-docs.deepseek.com/zh-cn/quick_start/pricing)；[vLLM官方Linux/Windows适用范围](https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.md)。

## 2. 必须先纠正的重大设计缺口

### C01｜**已确定的根本兼容性矛盾：零上游修改 + Flash-only + 原版工具直接执行**

- FACT：NK当前Git源码硬编码`gpt-4.1`，原版仅传入OpenAI Key，不显式传Flash端点。CritiCS使用OpenAI旧模型/端点，还存在很可能导致原程序无法导入的错误语法。
- INFERENCE：不修改上游时，NK或许可经SDK的环境变量/纯传输协议中转使用Flash，但**没有验证其实际锁版SDK是否支持环境变量以及结构化输出响应完全兼容**。CritiCS SyntaxError如果经原字节编译确认，则不存在“只改配置就修复语法”的办法。
- UNKNOWN：当前Windows是否具备WSL/Linux/CUDA；可否找到另一**经用户新批准且同样原版**的兼容上游修订版本；单场实际运行结果。
- 结论：**原计划若直接保证三者都能按Flash原版跑通，是事实前提错误。** I01必须成为付费/生产前门；发现本体缺陷只记录B11，不改厂商代码。
- 其他解释：原版CritiCS某独立路径可能不导入问题文件，但其原`critics/plan/plan.py`确实导入chatsetting；具体需编译+import原版确认，不凭推测裁决每个入口都失败。

### C02｜工作流与软件混淆，曾导致自建流程替代权威

- FACT：CNW官方自己声明 `_workflows` 是提示词/人工操作文件而非可执行软件。完整章节审稿包含5 Lens、三反驳者等；作者明确初期先人工做少量章节。
- 逻辑跳跃：把“需要 Codex 执行 Markdown”错误等同“必须另起多Agent框架并在首个小样本运行全套多轮审稿”。
- 修正：**原版文档决定创作方法**；工程治理只监管权限和Git；适配只做传输；首次用户授权是完整一场而非完整 Episode。报告中不得称“原版CNW全章节流程已复现”，除非实际按原版完整链执行并审。

### C03｜空仓库状态不能代表本机状态

- FACT：远端main确实空树。
- UNKNOWN：本地D盘仍可能保留未跟踪目录、用户下载的剧本、旧Key/虚拟环境、正在运行的命令和未推送改动。
- 风险：按“我已经清零”直接 `git clean -fdx` 或重初始化会破坏用户数据。
- 修正：先只读核Git、Untracked、进程和源目录，再非破坏性治理导入；不得reset/rebase/force。

### C04｜“只读上游”的含义必须覆盖代码、配置、Prompt、依赖锁和构建副作用

- FACT：Next.js `npm ci`、`npm run build` 与Python导入/编译可生成本地文件；不一定修改Git跟踪字节，但可能将缓存放进上游checkout。
- 用户硬约束：原版工具与工作流一个字节都不能改；这比“允许小兼容patch”更严格。
- 修正：以Git子模块锁HEAD；必要运行在 `runtime/build` 原字节镜像，安装产物留镜像；用Git blob/dirty+哈希比对检查原版源文件未变。若程序必须直接修改配置才能运行，B02/B11停。

### C05｜下载目录找到资源包这一关键输入仍是UNKNOWN

- FACT：用户过去提供过版本和一份约定的SHA，但是当前并未从Windows Downloads读取任何文件。
- 风险：路径猜错、同名但版本不同、压缩包内有目录穿越/恶意脚本、原文被错误公开、手动拿旧R02代替。
- 修正：已验证Windows Downloads Known Folder路径 → 枚举ZIP → 精确SHA对照 → 内部J01–J32+玩法Contract核验 →私有解压；不执行原型内脚本，不上传原稿到公共仓库。

### C06｜证据分层不清会掩盖实际质量失败

- FACT：原版CNW自己强调最终情绪落点、长篇节奏、角色声线需要人类审稿；CritiCS论文中的创意评价不等于当前《苍歧》效果。
- 修正：技术证据、原版执行证据、用户可读完整一场、连续上下文、Controller主观质量裁定分开。用户没看过不得 `QUALITY_ACCEPTED`。真实NK/CritiCS调用链必须能追到当前单场实际被使用的位置，不允许“装着不用”。

### C07｜成本结论此前与账本预留混淆

- FACT：历史`$12`是旧项目测试阈值；用户已经回退之前的工作，不能当本轮新资金授权，旧数值更不能当新的余额凭证。
- INFERENCE：原版CritiCS每次评审可能多次请求，即便样本是一场也可能比单次Flash调用昂贵；模型的最大上下文不是应该全部填满的输入目标。
- 修正：在真实完整兼容性与用户当前范围获批前，不进行付费试验；首次只授权一场，不自动失败重试/多篇。实际账单与本地估算、在途预留分别标记，使用当前官方计费口径，不自行拍美元预算值。

### C08｜把MVP的27权威面/130业务义务复制进StoryStudio会造成反向污染

- FACT：那些是MVP黑板/EMA/Host/性能业务专属数据，非通用创作流程；本轮MVP的有效治理源分支与main不同。
- 修正：仅取**可迁移的治理原则**（唯一Writer、Reviewer只读消息、同Atom签收、远端读回、黑名单、证据与效果分离）；StoryStudio的五层权威与B01–B14是**本任务用户授权的新治理**，不假托为原MVP原条文。

### C09｜版权/许可与作品归属可能影响未来商用

- FACT：CNW授权的文档模板和受保护示例小说有明确区别；NK/CritiCS许可为MIT。
- UNKNOWN：《苍歧》原剧本杀原始作品的电子改编/商业发行许可链当前未在本次任务中验证。
- 修正：此处仅做内部私有质量验证，不在公开仓库储存脚本原件或公开传播；未来商用权利另作专项核验。**不因此阻碍本轮允许的内部静态调查**。

## 3. 总体验收结论

| 项目 | 本次静态审查结论 |
|---|---|
| 远端空仓库 | `FACT_VERIFIED`，不代表本地空 |
| MVP有效治理在哪里 | `FACT_VERIFIED`，当前R66.9在performance分支 |
| 原工作流可以原样阅读使用 | `FACT_VERIFIED`，MD规范本身可读，但不等于自动执行软件 |
| 上游零字节改动方案 | 可通过Git子模块/只读源+运行镜像**治理**，尚未在本地实施 |
| NK原版+Flash无修改兼容性 | `UNVERIFIED`，存在硬编码模型及API兼容问题 |
| CritiCS原版代码可原样运行 | `BLOCKER_EXPECTED`，源文有明显语法问题，须现场原字节py_compile确认 |
| 用户下载目录2.3文件 | `NOT_OBSERVED` |
| 首个日常故事的真实质量 | `NOT_RUN` |
| 新治理已获Controller签署 | `NOT_ADOPTED` |

**不能把以上写成“所有大问题都已修复”。** 本审查已经确定旧流程的两个前提错误：一是“工具不可改却一定可直接Flash运行”，二是“工程可跑即创作有质量”。新治理和计划已阻止再次越界；但目前无法在未取得机器现场证据、又禁止原版源码改动的条件下，预签全部工具成功部署。**必须按计划在原版静态/原字节原生兼容性核验处给出真实成功或明确阻塞，不能自行补全缺失能力。**
