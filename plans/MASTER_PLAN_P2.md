# StoryStudio P2 完整执行总计划

## 0. 交付目标和本次范围

**结果：一套实际可用的本地开源文本生产工作流，以及它为《苍歧》生产的一场完整日常戏。** 不是只证明软件安装成功；不是只提供故事提纲；不是只生成几段角色独白。

本次继续使用 CNW 作为创作组织规程，NK 作为叙事视角生成工具，CritiCS 作为剧情和文字批评工具；新增生产 API 全部实际请求 `deepseek-flash`。工程由 Codex 执行，独立验收子智能体担任 Controller。第一场满足君天离单 POV、JUN-SINGLE-02.3、前后剧情衔接及可演出的文本要求。

初稿、实际工具反馈、同场修订、连读版、启动/恢复入口必须一起交付。用户读首场前不生产第二场或整幕；但“首场”包含其必要试写、校验和修订，不是只准发一次 API 请求。

## 1. 这次直接采用的工程决定

1. 不重建仓库；复用三个固定上游和现有 I01 原始失败记录。
2. 参考源码不动，生产版本允许补丁。将删 `s`、补漏传正文、修解析、升级必要依赖与 Flash 接入全部纳入正常修复工作。
3. Windows 原生 CPU + 远程 Flash API。使用独立 Python 3.11 环境；不为未使用的研究支路部署 vLLM、CUDA、Ray 或本地大模型。保留相关源代码，但不把“全仓所有可选功能都能跑”作为本场前置。
4. NK 直接配置 DeepSeek provider 和明确的 Chat Completions 模型入口，不设伪装 GPT 型号的代理网关。保留原路由、模板业务含义和 Zod 返回结构。
5. CNW 的模板用于填写本项目内容；其流程由薄脚本按文件执行，文学方法不另造。
6. 先解决源稿可获得性，再生产；源稿读取不再被 CritiCS 的 bug 锁住。工具、源稿两个独立问题分别处理。
7. 模型联调允许无版权敏感内容的小型真实请求，先验证真实出站，再进入项目试写；不再出现“必须先证明真实调用，才能允许第一次真实调用”的循环。
8. 每阶段由受委任 Controller 接受后自动继续。工程允许范围已在本版给定，不再逐个问用户。

这些是本版工程选择；不是三位开源作者共同提供过一个现成三工具流水线的声明。

## 1A. 阶段依赖与可继续的独立工作

| 阶段 | 必需前置已接受 |
|---|---|
| P2-00 规则接续 | 用户本条明确任务；无须再次批准旧 G00 |
| P2-01 源稿与 Canon 输入 | P2-00 |
| P2-02 CritiCS 修复 | P2-00 |
| P2-03 NK 适配 | P2-00 |
| P2-04 真实联调 | P2-02、P2-03 |
| P2-05 单场设计 | P2-01、P2-04 |
| P2-06 生产修订 | P2-05 |
| P2-07 交付复用 | P2-06 |

默认按编号施工，保持一个 Writer。P2-01/02/03 是独立前置支路：其中一个确实等待外部输入时，Controller 可切换到另一支路推进，不是越过尚未满足的消费者依赖。阶段验收针对本阶段产物及真实依赖，不把“上一编号没完成”作为普遍停工理由。任何与另一支路共用的文件修改仍由唯一 Writer 串行处理。

CritiCS 内部的五个/三个模型角色调用是原工具的功能，不是额外建立多名工程 Reviewer，也不违反只有一个独立 Controller 的安排。

## 2. 接续事实和复用规则

读取时远端候选为 `2586d378669b74d4fc9e4460aa80f2cd8a908038`，I00 提交 `47394d3432fe8b8fe0c0d52edba50c602099e9af`。现场出现更晚提交时先检查内容并复用，不退回旧 SHA。

| 已有内容 | 本版处理 |
|---|---|
| G00 治理及验收 agent 委任 | 保留历史与 agent；用 P2 替换已被纠正的现行条文，不从零再做 |
| G01 来源及固定上游 | 复用实查事实；旧矩阵不再要求逐命令扩列，旧 PENDING 不冒称新签收 |
| I00 子模块 | 现场核对 HEAD 和已有改动，吻合就直接复用，不再次 clone |
| I01 SyntaxError、环境记录 | 保留为修复前证据；在新版本实际消除错误后追加结果 |
| 本地 WIP/后续产物 | 按实际文件、输入身份、补丁身份判断；不盲丢、不盲信、不重跑已证实的成功步骤 |
| main 仍为空树 | 不影响当前工作分支施工；最后合法快进/PR，禁止强推 |

原始工具来源：
- CNW：`MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。
- NK：`zhangchaodesign/narrative-keyframing@b857f34b7d371ae82c30e00eb021884c14d08ae9`。
- CritiCS：`EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation@fbf66cbc913012c6f80af1687e27f0ce350475e3`。

## 3. 目录和执行接口

```text
StoryStudio/
  AGENTS.md
  CODEX_START.md
  plans/MASTER_PLAN_P2.md
  plans/MASTER_PLAN_FROM_EMPTY.md             # 只作 P2 跳转
  docs/governance/                           # P2 两份治理文件
  implementation/                           # 技术、生产、验收规范
  config/production.example.json             # 无 Key，公开默认配置
  patches/CritiCS/*.patch
  patches/narrative-keyframing/*.patch
  patches/PATCH_INDEX.json                   # 源 SHA、顺序、目标身份
  locks/critics-api-requirements.lock.txt
  locks/nk-package-lock.json                 # 若原锁有必要调整
  tools/                                    # 薄调用/重建/导入/导出
  tests/                                    # 有限功能检查；不得替 Controller 签收
  third_party/                               # 现有固定参考子模块
  evidence/P2_CURRENT_STATE.md               # 唯一当前阶段指针
  evidence/P2_ENGINEERING.md                 # 汇总，不为每次命令另造报告
  reviews/P2_ACCEPTANCE_LOG.md               # 指向真实 Controller 消息
  inputs/private/release/<source-sha>/       # 忽略
  workspace/cangqi/                          # 忽略；CNW 项目实例
  runtime/patched/<tool>/<build-id>/         # 忽略；可补丁的实际运行树
  runtime/envs/                             # 忽略；依赖、缓存位于 D 盘
  runs/<run-id>/                             # 忽略；请求、响应和恢复记录
  deliverables/<sample-id>/                  # 忽略；阅读版及本地交付包
```

下面命令是本次要实现的产品接口，不是已经存在的命令。先完成对应实现再运行；不要把“找不到还没编写的脚本”认作上游故障。

```powershell
.\tools\studio.ps1 doctor
.\tools\studio.ps1 prepare
.\tools\studio.ps1 import-source
.\tools\studio.ps1 verify -Mode offline
.\tools\studio.ps1 verify -Mode live
.\tools\studio.ps1 scene -Stage plot
.\tools\studio.ps1 scene -Stage draft
.\tools\studio.ps1 scene -Stage revise
.\tools\studio.ps1 export
.\tools\studio.ps1 resume -RunId <existing-run-id>
```

`studio.ps1` 只找解释器/配置、调用确定步骤、保存产物并返回状态；没有自创规划 Agent、自发扩样或“自己给自己签 ACCEPT”的逻辑。涉及下一阶段时由 Codex 将产物交 Controller，而非脚本自动裁定质量。

---

## P2-00：接续工作树并替换冲突规则

**目标**：所有活动入口一致执行“可修实现，保留方法”的新规则；从真实进度继续。

**输入**：现场 Git、原会话消息、本包、现有 WIP。**写范围**：本仓治理、计划、implementation、少量状态指针；不改工具或原稿。

**步骤**：
1. 用 `git status --porcelain=v1`、`git branch --show-current`、`git rev-parse HEAD`、`git ls-remote origin` 记录状态。只读列出本任务现有修改；不要用 reset/clean 获得“干净”。网络失败不销毁本地进度。
2. 原 Controller 阅读用户最新要求及 P2 全文，确认实际的依赖图、修复范围和产品终点。若先前 agent 已结束，建立独立接替者并读完整交接。
3. 将本包同路径新文件作为本任务的明确替换内容；已有本任务 WIP 先 diff 再合并，未知用户手工更改不覆盖。旧报告不动，旧总计划改为 P2 跳转。
4. `P2_CURRENT_STATE.md` 记录：实际分支/HEAD、当前 P2-00、旧 I01 失败的路径、已完成事实、待处理补丁。不得把“原候选尚未生效”的旧页头继续留作现行规则。
5. 按语义检查根 AGENTS、两份治理、主计划、启动文件，不得保留“修一字节即停工”“Controller 只能用户”“I02 必须等无法修的 I01”等有效条文。历史文件带明确历史标签即可，不要求全仓洗掉每个旧词。
6. 冻结候选，Controller 查是否有授权遗漏、范围扩张、双计划和丢 WIP；普通提交/推送并核对 C/T，记录接受，继续 P2-01。

**验收**：规则可执行；旧 I01 是待修故障而非永久封锁；没有重新建立 G00 循环。此阶段只做必要规则替换，不重建几百行来源矩阵。

---

## P2-01：找到真实源稿，建立私有输入与知识边界

**目标**：后续创作拿到正确的《苍歧》材料，不拿错误版本或空泛人物简介试写。

**输入**：用户已指定身份 `JUN-SINGLE-02.3`；已记录 ZIP SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`。这是定位依据，不是声称此刻已经找到。

**步骤**：
1. 优先复用本任务已经核实的本地路径/解压目录；尚未找到才读取 Windows Downloads 的 Known Folder 注册表。随后查本项目用户输入路径和会话中明确给出的路径，不扫描浏览器或无关隐私目录。
2. 对 ZIP 做 SHA256。相同哈希副本只读一次；大小/名称不是身份。不同包装版本不能凭文件名冒认为原版：只有可与已有权威解压件逐文件内容核对时才可作为同内容输入复用，否则保留差异。
3. 校验 ZIP 成员：拒绝绝对路径、`..`、盘符、符号链接、大小写冲突、同名覆盖和异常解压量；先建新私有目录，再解压。不得运行包内程序，不修改原始 ZIP。
4. 读取 `scene_manifest.json`、版本说明、场景及知识/机制合同。实际核对 J01–J32 和 `JUN-SINGLE-02.3`。若旧计划所说数量与真实同哈希源不一致，将旧计划前提改为事实，不伪造缺失场景。
5. 建立全篇场景索引：ID、入口/出口、时间、在场人物、地点、固定/行动驱动、前置条件、来源文件。J19–J32 如有条件分支，按原条件存图或表，不拉成强制线性串。
6. 私有保存人物知识表：每个角色在各候选插入点知道什么、能观察什么、称呼关系、不能提前获知什么；每项引用源文件和可定位段落。未知要保留未知。
7. 在 `workspace/cangqi/` 建立 CNW 的项目目录与 Canon/Style 文件实例。复制的是获许可的通用模板结构，不复制作者示例小说。已有原稿仍作为只读输入。
8. Controller 看真实源片段与索引，检查身份、知识边界和分支没有被改坏。私有索引的哈希写脱敏证据；不将正文推到公开 Git。

**产物**：`source_index.json`、`source_manifest.json`、CNW `90_canon/` 的事实底稿、`92_style_engine/` 本项目风格参考；详细字段见生产规范。

**验收**：输入身份可证明、原稿无改动、知识/分支可用于样本，私有目录确被忽略。不是要求用户再解释剧情。

**恢复**：若 Key/网络有问题，此步仍可做；若源稿暂缺，继续 P2-02/03 的独立工程工作，但不凭空生成《苍歧》正文。真正找不到唯一输入时才报告该具体缺件。

---

## P2-02：修复 CritiCS 实际要使用的生产路径

**目标**：原生三批评者/Inspector、改剧情函数和 Image/Voice/Leader 都能在项目适配版中真实执行；不部署无关论文全套实验环境。

**步骤**：
1. 将固定子模块导出到新的 `runtime/patched/CritiCS/<build-id>`。在根仓记录补丁次序和受影响文件；生产副本允许修，不改原始参考。
2. 保留旧 SyntaxError 证据，修复 `gptsetting.py` 中 `verbose=True` 后的多余 `s`；对实际入口及导入依赖做解析检查。
3. 建立独立 Python 3.11 API 环境。保留原 LangChain 0.2 系列的最小兼容依赖，消除 `openai==0.28.0` 与 `langchain-openai==0.1.19` 的依赖冲突。先解析依赖、安装、`pip check`，再冻结锁文件。不要强行全装原 requirements 中的 vLLM/Ray/训练依赖。
4. `chatsettubg`、实际 selector/改写用到的 LLM 构造都接到同一显式 Flash 配置；允许保留原函数名字和接口。不要通过环境变量把请求伪装为 GPT。旧 completion/instruct 分支不在本次计划调用路径，不能被默认走到。
5. 修复 Voice 模板漏 `{story}`：让真实输入正文出现在 Voice 请求中；保留 Voice/Image 的原评价维度。只改漏接文本，不另写批评理论。
6. 核查 persona、Question 和 Leader 的输出解析，修复会截空或误读的实现 bug；不把解析不到的问题填成“无问题”。保留原函数调用顺序与角色职责。
7. 对本次实际调用的 `Critic.three_critic()`、`modifiedStoryline()`、`Refinement.Two_refinement()` 建立固定离线返回样本；以捕获请求确认每个输入、批评结果和 Leader 选择真实传到下游。未用 selector 或未用死函数只标未启用，不无限扩修全仓。
8. 真实 API 本步不需要 Key；先确保可导入、接口参数正确、内容确实传入、错误不会造假成功。Controller 审查源码 diff 和这些证据。

**产物**：可重建 CritiCS 适配树、版本化补丁、API 依赖锁、入口 `tools/critics_bridge.py`、离线检查证据。

**验收**：语法/导入正常；原 5 次剧情批评角色链和 3 次文字批评角色链按源码到达；Voice 输入不再缺失；误格式明确失败；没有改成自制替代批评器。

**恢复**：发现新 bug 继续修实际路径。依赖问题换合理兼容版本并重锁，而不是继续冻结到失败的上游 requirements。技术参数见 TECHNICAL_SPEC。

---

## P2-03：修复 NK 并明确接入 Flash

**目标**：真实 NK 路由使用原模板/结构生成结果，输出通过原 schema 并可送入 Writing Brief。

**步骤**：
1. 从固定 NK 源生成补丁生产树；复用现有 Node 24/npm，先按现有锁安装。遇到确切兼容/安全问题才在适配版内修锁或小范围升级，不先重装系统。
2. 在服务端 provider helper 配置 `baseURL=https://api.deepseek.com/v1`、进程 Key 和 `deepseek-flash`；路由明确调用 Chat 模型入口。查全体会暴露的生成 route，不能只修一个页面而其他页面仍发 GPT。
3. `generate-perspective` 保留原事件/角色输入结构和 `ResponseSchema`，继续使用其实际模板渲染。以配置接入模型，不改叙事目标成另一项任务。
4. 使用已核查 SDK 的 JSON 兼容模式，保留本地 Zod 验证。必要的 JSON 格式提示只约束序列化，不改变故事设计；不以只返回合法 JSON 代替字段和任务语义检查。
5. 修复数量/位置对应：一项 perspective 请求应产生一项对应结果；空值、少项/多项、截断、解析失败均不得返回假成功。项目首次只有君天离一项，但接口检查也要真实。
6. Key 优先在本地服务进程读取，UI 不持久化真实 Key；清除或私有保存含完整 prompt 的调试输出。只监听 `127.0.0.1`。
7. Build、启动、HTTP 无 Key/坏输入错误、正确输入的离线响应路径都验证。通过请求捕获证明模型和 host 正确，不拿本机 mock 说“Flash 已经连通”。
8. Controller 审查补丁是否仍为原功能，并确定本次启用的 route 列表。没有用到的功能不声明通过，也不能从 UI 暗走未适配端点。

**产物**：NK 补丁、锁文件、可启动实例、明确输入输出合同、离线证据。

**验收**：原 route 和模板被实际执行；没有 GPT 出站风险；schema/数量不合格会退回；服务本地可用。下一阶段才验证真实供应商返回。

---

## P2-04：真实 Flash 联调与费用闭环

**目标**：把“配置看起来正确”升级为实际供应商调用成功，并证明原工具路径可以接上。

**前置**：相应工具 P2-02/03 已接受，Key 可用，费用记录可工作。源稿不必先外发。

**步骤**：
1. 从本任务已有环境变量/明确配置位置取 Key，不搜索整个磁盘；不打印 Key。账户余额检查只取必要返回，缺 Key 是真实外部缺项。
2. 保存当日官方模型与价格来源。请求始终写 `deepseek-flash`，返回 model/usage 原样保存；有官方别名时分开记录请求名与返回名，不伪造“供应商一定回了某全名”。
3. 做一次不含项目原稿的小型纯文本真实请求；再通过真实 NK HTTP 路由做一项短 perspective 请求，以实际 `generateObject` 和 Zod 校验接收结果。
4. 通过 CritiCS 的真实 `chatsettubg`/`ConversationChain` 发一条短的无敏感测试，确认其适配后的实际调用路径、返回 memory 和 usage 可以取得。完整 Critic/Refinement 的真实角色链在 P2-06 直接用本场素材跑，避免提前重复付费全套。
5. 将 model、host、请求身份、状态、供应商 ID、finish_reason、input/output usage、原始输出和估计费用挂到同一个 run。无 usage 如实 UNKNOWN，不能等于 0。
6. 网络/429/超时按有限重试策略处理；不能换 GPT；不能把 mock 响应存进 live 目录。修复后只补失败的边界调用。
7. Controller 核对 live 与 offline 证据区别、Key 无泄漏、输出经过真实消费、预算规则生效。通过后自动进入项目试写。

**验收**：真实 DeepSeek 文本、NK JSON、CritiCS chat 路径有证据；不宣称此时已经证明作品质量或完整 CritiCS 样本链。

---

## P2-05：按 CNW 设计一场合法、有内容的日常戏

**目标**：以真实源稿给 Flash 一个足够具体的创作任务，而不是“随便写段日常”。

**步骤**：
1. 按 CNW Existing Project Import 规程完善 Canon/Style，源明确事实、推断、新增候选分开；已有 source_index 直接复用，不再把 32 场重写一次。
2. 从真实剧情入口/出口找一个合法插入区间：人物确实共处、时间连续、允许小事件、不影响下个固定锚点、不提前泄密。优先避开尚未解释清的动作分支。
3. 选择一个具体的小事件，依据角色当时的目标、关系和行为习惯设计行动及反应。允许创造本场局部可逆细节；不把任何新背景、关系升级或重大承诺偷偷写成既定 Canon。
4. 建立 `sample_contract.json`：插入点、前后锚、角色、君天离可见信息、允许变化、必须恢复/保持的状态、事件目的和输出语言。缺少不影响原作的布景细节由 Writer 合理设计并标候选，不因此向用户追问。
5. Flash 按实际 CNW Plot 模板输出 `ep001_plot.v0.md`，场数只有本场；这里的 ep001 只是本次项目实例文件命名，不重编号 J01–J32。
6. Controller 读前后原文与 Plot，检查“有人想做什么→行动→对方回应/阻力→事件落点”可执行，不把纯设定聊天、空泛角色自述当完整戏。必要时定点修改当前 Plot，不批量扔候选。

**产物**：完整样本合同、前后原文引用、初步 Plot、项目风格输入。Scene Card/Brief 在 P2-06 经过实际 CritiCS 剧情反馈后定稿，避免先写完又盲目重写。

**验收**：存在合法位置和清楚的小事件；角色/知识/关系不越界；实际输入足以支撑成稿。Controller 不用量化假分数代替判断。

---

## P2-06：跑完整生产链，修订同一场直到可交付

**目标**：原方法及两个原工具真实参与产生可读成品。

**严格数据顺序**：

```text
真实 Canon + source anchors
  → CNW Plot v0
  → CritiCS Critic.three_critic (persona / structure / ending / originality / inspector)
  → CritiCS modifiedStoryline
  → Controller 核对 Canon，形成当前有效 Plot
  → CNW Scene Card
  → NK generate-perspective（君天离单项、实际事件和角色快照）
  → 用该输出填写 CNW Writing Brief 的 POV/表现材料
  → Flash 按 Brief 生成完整正文 v0
  → CritiCS Refinement.Two_refinement（本场选定的真实关键句段）
  → CNW Revision 接纳有效意见，Flash 输出同场修订 v1
  → Controller 全文连读、事实/节奏/人物动作核查
  → 合格后冻结本场交付
```

**具体动作**：
1. 对 Plot v0 运行真实 `Critic.three_critic()`，保存每个原角色调用和最终 Inspector 的选择，不让 Writer 代写意见。
2. 将原生反馈送入 `modifiedStoryline()`；项目边界作为显式上下文约束：本场局部细节可改，32 个原锚/角色知识不可改。保留原允许提出创意的机制，但不自动采纳越界建议。
3. Controller 对照源稿判改写是否合法。若提出新角色秘密、跨场大结局、额外场景，作为候选退回，让 Flash 只修这部分；不能因原提示允许加场就污染原作。
4. 按核准 Plot 生成一张 CNW Scene Card，写清每个动作的发起者、可见反应、角色局部目的、转折、结尾状态。用原模板实例，不新增一套情绪状态机。
5. 由 Scene Card 生成 NK 请求。事件输入是本场真实行动，不只是角色名字；单项 narrator 是君天离。保留原 request、NK 原 output、其映射到 Brief 的位置。
6. NK 的 reflection 是视角素材，不是最终正文。Controller 检查未发生读心或提前知道秘密；Flash 写作时实际使用核准结果，同时依据完整 Brief 写对话和行动。不可强行逐字照抄不适用的反思句。
7. 生成 v0 完整正文，检查 finish_reason、文件完整性与场景落点；截断不是成品。输出风格遵守用户源稿，不套用作者示例小说语言。
8. 在 v0 中选出承载本场转折/关系表现的真实连续关键句段，默认不超过原 Voice 模板所期待的五句；通过 `Refinement.Two_refinement()` 取得 Image、Voice、Leader 三份真实结果。记录原文范围，**不得声称它已经逐句审了整个场景**。
9. 按 CNW Revision 流程将意见分为采用、修改后采用、拒绝及原因；拒绝必须引用 Canon 或文本事实，不能笼统说“不适用”。让 Flash 实际修改同一场。保留 v0，产出 v1，不覆盖历史。
10. Controller 全文连读前文→v1→后文，审查内容覆盖、角色区别、行动因果、自然对话、结尾和下一锚点；这次是全场审阅，补足句段工具的范围边界。
11. 出现重大遗漏时定点修订同一场。依赖无变化的 Critic/NK 结果复用；如果改了 Plot/人物状态，重跑相应消费者，不拿旧输出硬拼。
12. 默认最多先做两轮内容修订以防盲抽；两轮后仍有同类缺陷，Controller 必须回到明确的 Brief/Plot/输入根因修正，而不是再随机重抽全文。预算不足只暂停新增付费，交付已产出的具体缺陷和草稿，不能签成功。

**验收**：完整初稿和修订稿可读；三工具的实际参与可定位；原作无实质冲突；没有工具意见被凭空替换；同场意见闭环；无截断/占位符/大纲冒正文。详细内容要求见 PRODUCTION_SPEC。

---

## P2-07：交付阅读版与可复用入口，结束首场验证

**目标**：用户能直接读到作品，下次不必重新部署或重新解释操作。

**步骤**：
1. 导出 `01_初稿.txt`、`02_修订稿.txt`、`03_前后文连读.html`、同内容 `.md/.txt`、`04_修改说明.md`；保留原文与新增场景清楚的边界。UTF-8，HTML 离线可读、无外部脚本。
2. `04_修改说明.md` 用少量具体文本位置解释 NK、剧情批评、文字批评各影响了什么；未采用意见给原因。不要只交工程日志。
3. 导出项目生产预设和运行说明：准备环境、启动 NK、导入源稿、生成当前场、恢复中断、导出阅读版各用同一个 `studio.ps1` 的命令；列明真实脚本和路径，不用空占位命令。
4. 验证非付费复用：关闭进程→从干净的新 PowerShell 启动→按 source+patch+lock 重建/定位环境→加载同场已有 checkpoint→重新导出同一阅读版。已有成功模型步骤不得再收费。
5. 校验 Key/原稿/原始响应/阅读产物不会进入公开提交；只提交补丁、锁、工具、治理和脱敏索引。Controller 将私有产物 hash 清单与远端代码 C/T 一并签收。
6. 普通推送工作分支。若当前远端 main 仍是本分支祖先、没有未知并行改动且仓库允许，正常非 force 快进发布已接受代码；否则使用 PR 保留冲突，不强推、不合并未知改动。远端发布受保护时不阻止本地可读作品交付，状态如实区分。
7. 向用户报告真实文件路径、实际总调用数/usage、估计费用与账单状态、哪些阶段已接受；提供阅读文件，不只给 SHA。
8. 结束在 `READY_FOR_USER_REVIEW`。用户满意后才记 `USER_CREATIVE_ACCEPTED`；用户未读不是工程失败，也不授权继续写第二场。

**验收**：可打开的完整作品、可再次启动/恢复的入口、私有材料安全、正确的事实性状态。完成这一步才可说“部署与首场交付完成”。

## 4. Controller 通用签收格式

每阶段只需一段原消息：阶段、ACCEPT/RETURN、被审 C/T、私有产物 manifest hash、实际检查范围、缺陷及下步。详见 `reviews/CONTROLLER_PROMPT.md`。不把同一条消息拆成 Reviewer/Controller/用户三层重复批准。

若修改只有状态索引，不重新跑生产；若修改实际代码或剧情输入，依据消费者关系重验。没有独立签收时不能谎称通过，但一般 bug 修复和资料准备无需每一行都新申请许可。

## 5. 本版明确不做

不做第二套创作理论、不做六槽/24候选、不做整幕批量、不建多代理商业平台、不训练本地模型、不为无关支路装 GPU 环境、不公开原稿、不许审查表替代作品、不以“改 bug 违反原版”停止。
