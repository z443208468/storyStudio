# StoryStudio 通用应用化与旧场景彻底剥离 — Codex 施工指令 R5（原作者方法不变量与独立只读子智能体验收硬保护版）

> **执行对象**：本机现有 `z443208468/storyStudio` 工作树及其已存在的私有运行资料。  
> **R5 基底（保留 R4 的已核实事实）**：2026-10-11 逐项重读 R3 832 行，复核 `z443208468/storyStudio` 远端 `main` 固定树 `26b72cea21dce45eede21cffddd4e75307d75652`（149 个 tracked 文件；该树不是用户本地 W10 工作树）、固定 CNW 作者提交 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`、上传的 v5 `prepare_inputs.py` 真正安装逻辑及 Python/GitHub 官方文件系统和 Git 历史说明。本轮额外核实多来源合同、来源清单版本、无双锚改编、单行 JSON、原创第二章、全项目并发写入及离线效果与 Live 效果之间的逻辑缺口。**R1/R2/R3/R4 仅为历史设计；本文件 R5 是本次唯一拟投入执行的施工文本。导入仓库并取得实际 SHA 前不冒称已安装活动计划。**本地未提交 W10、三个已安装项目的真实路径及 TS 失败栈、账本 Pending、磁盘与锁、Controller 可用性 **未被远端验证**，必须在 Atom-00 现场取证；不可把推测变事实。  
> **本次唯一任务**：先把 StoryStudio 从“围绕《苍歧》旧 J19/EP001 场景搭建的生产环境”改造成**可以创建、导入、生产、审查和导出任意独立故事项目的通用 CNW 应用**；旧场景及历史实验资产独立归档、可显式挂载，不再参与新项目默认启动。  
> **明确不做**：不执行 TS/DL/RH 历史场次生成；不为本任务优化任何小说；不重构上游 CNW/NK/CritiCS 算法；不删除或改写历史 Git 提交与私有证据。项目所有者已另行授权计划内、必要且经过精确候选审查后的通用输入包付费验收；该授权不包括真实 TS 恢复、旧私有数据迁移/cutover 或默认入口切换。
> **执行角色**：唯一 Writer 修改；**真实、单独启动的只读 Controller 子智能体**分阶段审原件、方法不变量、实际行为、候选代码 C/T 与证据，独立返回 ACCEPT / RETURN / EXTERNAL_INPUT_NEEDED。Writer 不得自签、代签或以单元测试绿色取代其结论；Controller 不得改文件、跑生产命令或发 API。  
> **治理（遵守仓库既有规则）**：以当前用户的通用化与“原工作流不被破坏”指令更新活动工作范围；持续遵守仓库 `AGENTS.md`、`docs/governance/GOVERNANCE.md`、`docs/governance/PLAN_AUTHORING_STANDARD.md`、`reviews/CONTROLLER_PROMPT.md`、`reviews/P3_1_CONTROLLER.md` 中未被新目标覆盖的保护、Controller、Git、费用、隐私及必要范围原则。旧 J19 单场和“马上生产三篇”的目标/生产范围不再生效，历史证据不涂改。仅现有 `main` 正常本地提交→子智能体读候选 C/T→ACCEPT 后正常推送→远端 C/T 回读；不建新分支、不强推、不 `reset --hard`、不 `git clean`、不删 WIP。**每次提交显式选择待提交路径、核 staging diff**，不得带入未提交的 W10、密钥或忽略数据。R5 与旧活动入口文本冲突时只更新“范围/计划指针”，不能取消安全与原作者方法边界。

---

## R3 已核实的历史缺口（由 R4 保留、补充与加严）

**已核实的源码事实**（可见于固定远端版本；不得把远端事实冒充当前本地 W10 现场）：

| ID/等级 | 可核实的当前行为 | R2 漏掉的后果 | R3 强制裁决 |
|---|---|---|---|
| C12 / P0 | `cnw_runner.produce()` 仅凭 `project_id.startswith("FICT_")` 即把 run 当 fixture，跳过部分真实来源/私有路径校验 | 即使两个非 `FICT_` 测试通过，生产绕验入口仍然存在 | 生产分支不得按名称取得 fixture 权限；模拟权限必须由**仅测试执行器**控制，任何真实 live 路由不得用 fixture 跳过来源门 |
| C13 / P0 | `execute_writing_brief()` 无条件调用 `_nk_pov()`；`_critics_hook()` 在 CritiCS 环境不可用时记录状态后可能继续 | R2 宣称 NK/CritiCS 可选与真实执行相矛盾 | 实际功能开关/三态治理、条件输入与身份哈希、禁用后的完整11阶段贯通；启用但缺依赖必须可靠拒绝 |
| C14 / P0 | `_planning_stage` 等先 `_write_project_output()`，后 `_persist_stage()`；`produce()` 创建新 run 时改写已有同 work_id 的旧 run 状态 | 中断留下未登记的项目候选，重复 run 可能覆盖前一产物/改变旧历史 | 所有新执行先写 run 作用域的不可变候选，原子登记成功，独立发布后才更新项目正本；旧 run 不被新 run 原地改写 |
| C15 / P0 | `cnw_runner.step` 对 `mode=offline` 只形成 `READY_FOR_EXECUTION` 请求包，并非执行11阶段 Provider 职责 | R2 两项目的“offline E2E”若只使用它，会是假 E2E | 使用真正的11阶段调度/读取/消费者，在 Provider、NK、CritiCS 边界注入**系统/传输级禁网**的确定性替身；模拟回执不能通过 `verify-live` |
| C16 / P0 | `cnw_runner.produce` 可能变更旧 run；多个同 work_id 项目公共文件覆盖前一版本 | 项目内多次生成/恢复不是幂等，原稿/Canon 即使没变也会污染 | 增加两 run 同 work_id、失败中断后重启、跨阶段发布与恢复的真实失败注入测试 |
| C17 / P1 | `cnw_project.build_source_bound_contract` 固定 `language=zh-CN`，`execute_prose` 续写 Prompt 含“中文正文”等文本 | 只改合同 language 并不能跨语言 | 搜索所有实际请求构造/长度校验/导出 UI 的语言硬编码；验证真实发送消息与输出语言一致，不只读配置 |
| C18 / P1 | 新数据目录若只靠 `project_id + run_id`，不同安装/数据根可出现相同字符串 | 同名项目迁入同一数据根后身份歧义，可能串用 Controller/收据 | 新项目引入不可变 `project_instance_id` 并在账本/运行/预检/导出绑定；旧合同经受限外部映射兼容，不改原字节 |
| C19 / P1 | 被忽略的 `runtime/reference`/构建/虚拟环境与代码发布分离；当前固定 Python `3.11.15` | 冷 clone 的来源引用/依赖不一定可用；Windows junction 检测不能假定有 `Path.is_junction()`（3.12 才加入） | 可复现来源 pin/bootstrap，逐项记录本地构建缓存；reparse-point 检测与现有 3.11 运行时兼容 |
| C20 / P1 | 当前全局生产配置金额上限为 `null`，历史取消上限是已授权的特定账本状态 | 把无限额度当所有新项目默认，可能造成不必要成本 | 历史策略保持字节不变；新项目 Live 默认为未授权，显式启用后才允许请求；不替旧用户重设已批准的上限 |
| C21 / P1 | GitHub 官方明确：只在新提交删除文件不清除历史 Git 对象 | “当前工作树没有旧故事”不等于公开仓库历史无旧内容 | 将“HEAD/干净 clone 不含旧依赖”与“历史仍可追溯”分别声明，不能冒充隐私擦除 |
| C22 / P1 | CNW 作者 `GETTING_STARTED` 推荐先手工做前几章，才考虑自动化生产 | “纯原创首章全自动”是 StoryStudio 扩展能力，不能标成作者原方法的已证明结果 | 原作者方法保真与 StoryStudio 新增 `ORIGINAL_AUTHORING` 扩展分别验收；完整原创链测试而非只过 Plot 请求 |

**事实与不确定性分类：** 上述源码行为和官方方法/文档为已核实事实；“当前本地正运行的 W10 文件如何锁 J19”“TS 的实际 path/未提交字节、账本 Pending、磁盘可用空间”等属于**待现场取证**，不能推定。多项目重名、阶段覆盖、越界和成本扩大是有具体机制支持的**风险推演**，并不是已经发生的数据事故。任何关于作品好看、生产质量达作者同等级的结论，**不得由本轮离线通用化测试推出**。

**验收优先级：** 此次限定为“通用多项目核心、有源插写/有源改编/无源原创连续章节三类工作意图、候选/审查/恢复/导出、旧数据可验证迁出”。**不扩展到多云 Provider、SaaS、多用户账号或真实小说质量保证**。若执行中发现这些功能可改进，不构成本 Atom 新工作项。

### R4 独立终审新增 P0/P1：不解决则不得宣称通用生产适用

| ID / 等级 | 已核实的事实 / 风险分类 | R3 中的设计缺口 | R4 要求的可观察结果 |
|---|---|---|---|
| D23 / P0 | **事实**：`cnw_project.build_source_bound_contract()` 直接选 `manifest["sources"][0]`；`import_source()` 允许追加多个来源 | “支持多稿导入”却不能保证新合同选中用户要改编的第二份稿，且其 `import_id` 在追加后仍沿用首份导入的值 | 新格式明确选择 source_id + source revision；A/B 顺序反转不改变已选来源，未选择多源则阻断；v1 历史原字节不改 |
| D24 / P0 | **事实**：追加来源会覆盖当前 `_INBOX/source_manifest.json`，旧合同以整份 manifest SHA 做身份 | 先发的合同可能因导入无关资料而全部失效；旧版本的精确 manifest 如果未留存则不能验旧合同 | 每次导入形成不可变 manifest/source-index revision 并在合同/运行中冻结引用；当前活动索引可更新，旧快照可按原字节验证；缺快照须明确受阻 |
| D25 / P0 | **事实**：目前所有有源合同需要 before/after 两条不同的源行；`import_source()` 支持 JSON Pointer，但合同器只接受行锚 | R3 只分“插写”和“无源首章”，没有“把整段现有稿改写成章节”，单行 JSON 更不可能有两条源行 | 将 **工作意图** 与 **来源类型** 分开：插写双锚、全段/选段改编用来源范围或 JSON Pointer、无源原创用 Canon/Arc；单行 JSON 与原始字节身份俱全 |
| D26 / P0 | **事实**：`cnw_runner._source_root/literary_source_freeze`、`cnw_export` 和来源 validator 按现行插写合同使用 `story.source_file`；Sprint 的 `_mirror_project` **仅在 imported_project 分支**读此字段，同时 Sprint 还要求前章关系 | 新增原创类型能通过首章 Plot 不等于后续章节、Sprint/Export 已处理好无源类型；**不能据此断言现有 Sprint 的每条路径都无条件取源文件** | 原创 EP001 与 EP002 走同一真实调度的断网模拟；EP002 消费受控前章结果；Sprint/Arc/Export 对原创类型不越权读取空原稿字段 |
| D27 / P0 | **事实**：`cnw_import_workflow._apply`、`cnw_maintenance._apply`、`cnw_sprint_live` 会更新项目文件/日志；当前存在各自的事务/写入流程 | R3 只规定生产候选的 CAS，未规定“维护/导入/Sprint 与生产发布”抢同一个项目权威版本时的串行化/冲突恢复 | 项目权威版本有统一项目级写入仲裁；维护、增量导入、Arc/Sprint/发布和项目登记均在其下验证前态/CAS 与 journaling；并发真实负例不丢更新 |
| D28 / P1 | **风险推演**：目录复制会复制 `project_instance_id`；R3 没规定移机与 fork 的身份冲突策略 | 相同实例 ID 的两个活跃路径可能被当成同一个项目，引发账本/审查/缓存混用 | `relocate` 保持身份且一次仅一个活跃写入者；`fork/clone-as-new` 新 ID 且不继承当前签收/活跃 run；重复实例注册 fail-closed |
| D29 / P1 | **设计事实**：R3 仅对模型/辅助接口注入模拟响应，不作真实 Provider 生成 | 模拟证明执行与消费者，不证明真实 API 可用、实际长文产能或文学效果；“产品已能自动写任何作品”仍不成立 | 交付拆成 `GENERIC_OFFLINE_FUNCTIONAL_VERIFIED` 与 `GENERIC_LIVE_UNVERIFIED`；公开 README 明确缺少的真实试运行，不许用 mock 假装真实创作；本次仍零 API |
| D30 / P1 | **设计遗漏**：`setup --data-home` 要求持久化，但 R3 未指定“下次启动如何找到该指针” | 用户每次重启可能失去项目定位，或执行器悄悄回退到系统盘 | 可读的用户级**小型本地配置**或每次显式环境/参数二选一；配置指针不写 Git/秘密，重启后新项目目录一致，失效时报错不改默认 |
| D31 / P1 | **风险推演**：合同语言可写任意字符串、长篇可要求任意长度，但适配器只实际验证部分语言与 token 上限 | 没有支持范围的“任意语言/任意长度”是产品过度承诺 | 锁定被验证语言/格式/篇幅的能力矩阵，未验证拒绝或标实验；中文与英语的真实组装请求、超限/不足时有明确结果，不冒称模型输出效果 |
| D32 / P1 | **事实**：v5 安装脚本把 F01 原稿复制到每个项目的 `_INBOX/originals/`，三份合同为 `imported_project`；旧 J19 则另有应用目录下的 private Release；CritiCS native 历史还使用 `ROOT/runs` | 仅设计“旧项目根→新项目根”一条映射无法覆盖旧 J19 的额外 source release/native 运行根；把 v5 当作必共享 Release 则事实错误 | 迁移依赖图按 **v5 项目内冻结源 / J19 独立 Release / 全局 CritiCS native runs / 账本** 分别记录旧根、新根、消费者与不可变哈希；每条映射必须有真实旧源 |
| D33 / P1 | **事实**：`cnw_recovery.verify_evidence()` 可能调用 `support_input_snapshot()`，后者在历史缺少 input snapshot 时写入归档快照并保存 `run_state` | “只读历史核验”不能直接等同于调用现有验证函数；可能在核验中改变旧原字节 | 历史核验建立纯只读验证器，或仅在外部临时复制工作集执行会补写的旧验证逻辑；原始 J19/TS 的状态、run artifacts、native evidence 在核验前后全量 hash 一致 |

### R5 方法保真及独立 Controller 新增 P0（E34–E40）

**这里列出的“缺口”是对 R4 验收设计的补强要求，不冒称这些风险在本地已实际造成损坏。** 已由远端源码证实的实现行为与需要未来试验验证的风险，应继续区分。

| ID / 等级 | R4 不能据此证明的事项 | R5 强制额外证据 / 不得通过条件 |
|---|---|---|
| E34 / P0 | 11 个阶段名字、次序正确，不等于实际读取、职责、下游消费与作者方法相同 | 以 **M01–M16 原作者方法不变量**作正式合同；每个受影响 Atom 交带来源与真实输入/输出/调用边界的 `METHOD_FIDELITY_DIFF`。仅比名称、计数或文档宣称，Controller 必须 RETURN |
| E35 / P0 | 四岗位互相串读、Prose 直接见隐秘 Canon/禁句、Brief 丢合法资料，仍可跑完11阶段 | 对 Plot、Cards、Brief、Prose 记录真实送入模型的消息内容结构及敏感来源哈希；Prose 仅获得经 Brief 传递的信息与实际相关声线；注入越权来源的负例必须失败 |
| E36 / P0 | 五 Lens、每条 Finding 三 Verifier 有“产物”，但共享上下文/改阈值/未处理遗漏 | 五 Lens 各有独立请求和规范允许的材料；三个反证独立，`refute_default` 且至少2票未反驳才成立；0 Finding / 0、1、2、3 保留票组合、Completeness→Refine→受影响 Re-review 形成真正消费证据 |
| E37 / P0 | 生成器可自动把推断事实/冲突推进 Canon，Workflow 03 自动覆写 07_draft | `CONFIRMED/INFERRED/TODO_CONFIRM`、来源/冲突、Canon 人工决定、独立修订稿、明确 promote 门全程测试；Canon Audit 不擅改；旧文本/未决项不能丢 |
| E38 / P0 | 声称有 Sprint 命令不等于作者五话批审/Arc 交接 | 五话真实调度的断网模拟、门槛 `score>=75、P0=0、P1<=2`、失败暂停、carry-forward、Arc-end Handoff 与完整 Workflow 01–05/标准操作回归；不把评分门当文学品质保证 |
| E39 / P0 | Writer 自测或 Writer 扮演 Controller 后签收，均不是独立判断 | **单独只读子智能体**必须首次完整读取 R5、仓库治理、固定作者原件、C01–C15 旧映射，独立建立预期矩阵；每 Atom 读实际差异/原始证据并返回有来源定位的 ACCEPT/RETURN；不可用时报 `CONTROLLER_UNAVAILABLE`，不得自签 |
| E40 / P0 | 按 Atom 在 `main` 推进，可能出现半成品新 CLI 已替换仍可用的旧入口 | 显式旧入口仅做迁移期间受控兼容，新入口以影子配置/特性路由验证；切换前用同一套回归证明原有效功能未退化；阶段 Controller RETURN 不推送、不切到新默认入口 |

**重要事实区分**：D23–D27 的“代码如何工作”由当前远端源码直接支持；“因此会造成某次已发生的数据损坏”**尚无证据**，只是可复现机制推演。D28–D31 是产品要求与可验证能力之间的设计风险。D32 对 v5 的说法来自附件 `prepare_inputs.py:213–250`；该附件已经展示本来就把 F01 原稿 `import_source()` 到每个私有项目，而非要求三个项目共用旧 J19 Release。真实本地安装需独立核验后才能接受。

### 参考事实来源（固定版本）

- 本地实现核查锚点：`https://github.com/z443208468/storyStudio/blob/26b72cea21dce45eede21cffddd4e75307d75652/tools/cnw_runner.py`、同一 SHA 的 `tools/cnw_project.py`、`tools/cnw_roles.py`、`tools/cnw_recovery.py`、`tools/studio.ps1`、`config/production.example.json`、`patches/critics/PATCH_INDEX.json`。Codex 开工必须重新确认 HEAD；现场若不同，以**实际代码**和完整差异为准。
- 作者公开方法：`https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/templates/config/workflow.template.yml`、`docs/HOW_TO_ADAPT.md`、`docs/GETTING_STARTED.md`、`example_project/README.md`（以上路径均固定于同一 SHA）。作者示例故事不是自由拷贝的模板。
- GitHub 关于删除与历史：`https://docs.github.com/en/repositories/working-with-files/managing-files/deleting-files-in-a-repository`。Python Windows junction API 版本：`https://docs.python.org/3.12/library/pathlib.html`（`Path.is_junction` 自3.12提供）；当前项目 CritiCS Python pin 以仓库 `PATCH_INDEX.json` 及现场为准。

---

## 0. 开工事实与证据边界

### 0.1 已知现场（不得冒充已在本机复核）

- 2026-10-11 检索到远端 StoryStudio `main` 包含 **149 个受 Git 跟踪的文件**；这是**远端参考**，不是本机工作树快照。远端查看时的 `main` ref 为 `26b72cea21dce45eede21cffddd4e75307d75652`，实际开工必须重新读取本机和远端身份。
- 上次执行报告：v5 三场已安装为**三个私有项目**；TS Live run 已创建、Plot `EXECUTION_INCOMPLETE`、本次 Provider 请求为 0；至少六个 W10 文件仍未提交。**所有这些均应由本机重新列证。**
- 已确认的活跃源码耦合（行号随版本变化；以函数/常量搜索为准）：

| 文件 | 需要清除的旧场景依赖/假设 | 允许保留的通用能力 |
|---|---|---|
| `tools/studio.ps1` | 默认 `workspace/cangqi`、固定 JUN Release 路径、`scene`/`legacy-scene`、内嵌 EP001/J19 专用导出、`doctor` 以苍歧文件判定就绪、旧 W10 专用入口默认路径 | PowerShell 统一 CLI、项目/运行/审查/恢复/导出命令 |
| `tools/cnw_runner.py` | `_source_root()` 与 `produce()` 对 `Cangqi_Jun_Release_2_3` 的回退；把应用默认配置当成所有项目同一份文学政策 | CNW 11 阶段调度、真实调用/回执、持久化、恢复与身份检查 |
| `tools/cnw_roles.py` | `_read_project_file()` 默认 `workspace/cangqi`；`build_role_packet()` 的固定 Release 路径 | Plot/Cards/Brief/Prose 官方角色读取和边界 |
| `config/cnw_production_policy.json` | `project_adaptation.project_id=cangqi`、固定 `zh-CN` 等项目属性放在全局生产政策中 | 固定上游公开方法 pin、通用结构/安全策略 |
| `config/production.example.json` | `D:\\CangqiStudio\\StoryStudio`、`JUN-SINGLE-02.3`、J19 来源 SHA、`CQ_P2_SAMPLE_001`、P2 第一场 `scope`、君天离和每轮场数限制 | 示例 Provider、费用保护、通用运行限制 |
| `tools/cnw_generate.py` | 读取全局 `runs/`、历史实验审批格式与 J19 私有前提 | 文字容量估算、Brief/合同身份校验 |
| `tools/cnw_critics_adapter.py`、`tools/cnw_runner.py` | 主生产调用仍依赖命名为 `p2_06_critics_run.py` 的历史试验入口 | CritiCS 真实桥接、来源与请求证据 |
| `tools/cnw_export.py` | 输出位置绑定仓库根 `deliverables/`，部分文案默认“插场” | 通过 `project_id/run_id` 的可读导出与 manifest |
| `tools/cnw_project.py`、`cnw_import_workflow.py`、`cnw_maintenance.py`、`cnw_sprint*.py`、`cnw_critics_adapter.py`、`critics_bridge.py` | 多处强制路径必须在仓库根 `workspace/`、`runs/` 下；阻止应用外部数据目录 | 私有路径保护、项目初始化、导入、维护、Sprint |
| `tools/p2_06_draft_run.py`、`tools/p2_06_revision_run.py`、`tools/p2_06_nk_live_probe.ps1` | 直接写死 EP001/J19/500–700 字的历史一次性实验 | **迁至历史归档**，不可作为新项目默认生产入口 |
| `tests/test_cnw_runner.py`、`test_cnw_adapters.py`、`test_cnw_generation.py`、`test_cnw_pipeline.py`、`test_cnw_recovery.py` | 测试前提直接读取 `workspace/cangqi/contracts/CQ-J19-INSERT-01...`；导致空仓库测试不可运行 | 改为纯虚构、测试临时目录构建的可复现 fixture |
| 既有 `plans/`、`evidence/`、`reviews/`、部分 `implementation/`、`tools/p2_*` | P2/P3/J19 特定施工史和单场诊断占用当前应用入口 | 完整移入**外部历史归档**；通用文档另行整理 |

以上为**首批必查**，不是穷尽清单。未提交的 `tools/cnw_live_executor.py`、`tools/cnw_live_provider.py`、`tools/cnw_w10_*.py`、`tools/cnw_w10_nk_live.ps1`、`tests/test_cnw_live_provider.py` 等必须按本机实际存在情况检查，不得因为 Git 中看不到就遗漏。

### 0.2 唯一可复用方法基准

- 作者：`MintoTsukino/claude-novel-workflow`。
- 固定参考提交：`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。
- 需逐项保留官方 `templates/config/workflow.template.yml` 的 11 阶段；参考 `templates/config/ai_roles.template.yml` 的四角色职责。
- 对照作者 `docs/HOW_TO_ADAPT.md`：**复制结构而不是故事内容**；人物、称呼、禁句、第五 Lens 的具体评价标准以及 JET 配置属于项目数据，不能进应用默认设置。
- NK 和 CritiCS 属于可选的已安装辅助组件，不得覆盖或改写 CNW 自身 11 阶段含义。

### 0.2a R5 不可降格的 CNW 原作者方法合同（M01–M16）

**权威来源**：固定 `MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的 `templates/config/workflow.template.yml`、`templates/config/ai_roles.template.yml`、`docs/THREE_LAYER_REVIEW.md`、`docs/HOW_TO_ADAPT.md`、`templates/CLAUDE.md`、`templates/_workflows/01_first_import.md` 至 `05_handoff.md`、`templates/08_review/batch_review.template.md`、`docs/GETTING_STARTED.md`；原版模板提供**公开方法**而非可直接调用的完整私有自动执行器。StoryStudio 的 Python/PowerShell/DeepSeek/NK/CritiCS 代码是我们的适配实现。不得声称源作者提供了那些本地函数，也不得复制作者受版权保护的示例小说实质内容。固定官方 `workflow.template.yml` 明确五话 Sprint 及 `min_score=75/max_p0_findings=0/max_p1_findings=2`。下述 M 标识是**本次工程保护规则**，不是作者原文件里的现成 ID。

**权威文件固定 Git blob（供 Controller 与本机 checkout 独立核对）**：`workflow.template.yml=146ea01a484cc0578cf290478b3941599ad7fb15`；`ai_roles.template.yml=8ec31cb93cb0be1913579cc5cb05de45460988f8`；`docs/THREE_LAYER_REVIEW.md=d03488d15f1a7841f442119237aff6d6148020df`；`docs/HOW_TO_ADAPT.md=5cbd6de30a6acfb1334e414dd747a74b96f3c88a`；`docs/GETTING_STARTED.md=3496d75c56bf13c5b9e834fbe98df9c539cdfec3`；`templates/CLAUDE.md=d4bfb370aaf6aadbbbbd4915422e7ceac673d0d6`；Workflow 01–05 依次为 `56148578d91d55e492a6913b4d73cbe529c34ecf`、`ae1c43eb249aa6fdbe7462bd6fd058222eb015fc`、`cae774e2582b09bdeaa7e80e6a7831ab4053dce5`、`da2afada0be6b6e66892bc2c9625b7fd70a0c5f5`、`a0349689535741e6a8a47e19a421922c7a1d53c4`；`templates/08_review/batch_review.template.md=24ba804c4807e0e535eee07a00c46d58ff10fd5a`。以上 Git blob 是**Git 对象身份，不是原始文件内容 SHA256**；现场应分别记录 Git blob 与文件 SHA256，不得混为一个字段。第三方方法之外的项目实例内容与 NK/CritiCS patch 仍需现场单独 pin。

| 不变量 | 必须保持的作者职责 / 信息读取边界 | 必须观测的真证据与反证（按相应 Atom 执行） |
|---|---|---|
| **M01 逐话阶段** | `plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review` 共11阶段。辅助服务、导入维护、晋升导出不冒充其中任一步 | 真实 stage DAG、实际调度 trace、输入→产物→下一消费者 hash；删一步、假输出或以 NK/CritiCS 代岗必 RETURN |
| **M02 Plot 职责** | 依 `ai_roles.template.yml` 读取当前 Arc、Canon、人物表，真正形成可用于下一步的 Plot；新 INSERT/ADAPT/ORIGINAL 的来源上下文由预检/角色边界合法提供 | 实际 Plot 请求所带 Arc/Canon/人物/合法 source identity，结构非空；不得用旧 J19 或别的项目补字段 |
| **M03 Cards 职责** | 读取**同一 run 的** Plot 与角色资料，具体化场景和事件，不读取无关项目审稿或新稿 | Card 实际请求包含被冻结 Plot 与 Character 的源 hash；篡改、缺失或跨 run 输入阻断 |
| **M04 Brief 职责** | 读取同 run Plot、Cards、人物、Style；按作者公开补充模板处理当前 Canon、time/world/glossary 等实际必要资料；压缩出唯一供 Prose 的 Brief；不能遗漏工作范围、必要节拍、POV/Voice | Brief 的真实请求、压缩内容、对上游节拍/知识边界的消费链；NK 禁用时同样成立，NK 启用时只能作补充 |
| **M05 Prose 信息隔离** | **真正发送给 Prose 的文学消息只能直接提供已通过的 Writing Brief 与本话实际相关声线样本**。完整隐秘 Canon、全套 source 原稿、`forbidden_patterns.md`、所有 Lens/Verifier 的意见不得绕过 Brief 直接输入 Prose；合同身份可存执行器元数据但不得成为额外文学阅读权限 | 在模型传输边界抓取脱敏消息与字段来源/hash：检查 Brief/Voice 允许集、敏感 canary 不出现；注入其他项目秘密、禁句文件或其他 Lens 结果须失败。因工作意图变化而需的新资料应先由合法岗位纳入 Brief，不扩大 Prose 白名单 |
| **M06 双层 Lint 与隔离** | L1 纯规则，L2 上下文规则；由当前项目当前语言有效 `forbidden_patterns.md` 编制，带行号/上下文；**Prose 不直接读这些规则**，Lint 不直接改正文。语义规则进入 Lens 而不假冒可执行 regex | 同一正文不同项目规则产生不同正/负命中；真实日志显示原文字节不变；零可执行规则时不得称通过所有写作禁句 |
| **M07 五 Lens 独立** | Style / Character / Plot / Canon / Story-specific 五个 Lens，分别接触作者规定的相关素材；story-specific 规则来自**当前项目**。Lens 只看原稿及自己允许的材料，互不看其他 Lens 的判断；结果在收齐后才汇总 | 五个实际 request/message hash、允许读集与隔离负例、五组各自 response/receipt（mock 明确标识）；伪并行、一个调用复写五份、共享前 Lens findings 必 RETURN。是否并行执行可受成本并发政策限制，但必须独立请求/上下文 |
| **M08 三反证判定** | 每一条真实 Finding 由 correctness / character-consistency / continuity-plausibility 三种不同立场独立挑战；不确定时默认反驳。**至少两名未反驳才保留**；无 Finding 时不伪造请求 | 对 0 Finding 与3种票数 `not_refuted=0,1,2,3`（其余 refuted/uncertain）自动测出正确结论；每 Finding×3独立请求、不可重复/串 finding_id、真实回执被下游使用 |
| **M09 Completeness 与反馈** | 查看完整正文、存活及被驳回 Findings，补查遗漏；新发现进入本轮修订与针对性 Lens 反馈，不自行宣告稿件合格 | 含有确定遗漏与无遗漏的对照；实际 `refine` 消费新 issue，下一轮对应 Lens 加载反馈；无用的空反馈不能算效果 |
| **M10 Refine / Re-review** | 仅依据真正成立及补充的问题修改独立稿，原 v0/vN 保留；Re-review 重新读取新全文并复查受影响 Lens/仍需处理的 Finding；未闭合不能标 CLEAN | 修改前后 SHA 和差异、问题→修改位置→复审消费；注入新缺陷或删必要内容导致 RETURN；不用旧审核票认证新正文 |
| **M11 First Import / Incremental** | Workflow 01 不覆盖原稿，来源事实分 `CONFIRMED/INFERRED/TODO_CONFIRM`；Workflow 02 仅处理新增/改动，保留既有结论和相互矛盾的双方来源 | 原文件 SHA、不确定事实无法升级、增量与冲突负例，实际产生/更新项目资料；声明来源与原作内容不混用 |
| **M12 Canon / Revision / Handoff** | Workflow 03 读审稿/正文/Canon 产生 P0–P3 修订计划，新版本放 `09_revision/`，经作者明确批准才晋升 `07_draft/`，受保护主题与 Canon 不被自动改；Workflow 04 Audit 只报告与未决问题、绝不自动改 Canon；Workflow 05 Handoff 提供可继续使用的指针/上下文 | 对 Workflow 03 **单独运行全新项目的真正修订计划并做拒绝自动晋升负例**；Canon Audit 后 Canon SHA 不变；Handoff 真被下一操作消费。工程 Controller ACCEPT 绝非 Canon 或文学批准 |
| **M13 Sprint 与 Arc** | `sprint.size=5`；最低评分75、P0=0、P1≤2 才通过原 Sprint 门；批审、carry-forward、必要 Arc-end Handoff/归档、失败暂停；五话不是写五个空候选 | 五个不同 Episode 的完整链及 review → gate → handoff/下一 Sprint 输入；分别注入低分、P0、P1超限、Canon 冲突/中断，拒绝越门推进；不随意改阈值救测试 |
| **M14 可选框架纯补充** | NK/CritiCS/JET 可选，不替代任一官方角色和门；`DISABLED` 不需要辅助服务也能运行完整 CNW；`ENABLED_BUT_UNAVAILABLE` 付费前拒绝 | 11阶段与辅助 hook 清单分开；开/关请求和内容差分，只因启用功能多了补充材料，而不是消失原始岗位 |
| **M15 新创作意图不侵权/不伪源** | INSERT 保留真实双锚；ADAPT 保留真实选段/JSON Pointer；ORIGINAL 真实 Canon/Arc/Style 与合法前章引用。三者只是 StoryStudio 产品接入方式，不是擅改作者 11 阶段 | 三意图分别经 M01–M14 中适用链路贯通；作者示例剧情和旧苍歧设定不泄漏；原创功能/文学效果不假托作者背书 |
| **M16 方法/证据分层** | 上游 pin、方法、项目资料、工程 Controller 签收、作者对 Canon 的批准、用户创意接受分别保持独立；离线 mock 不冒充真实生产 | 独立阅读实际阶段输入/文本/审稿链，状态精确到 `SIMULATED_OFFLINE` 或 `LIVE_NOT_RUN`；没有外部 Controller 原消息一律不可 ACCEPT |

**必须同时保住作者所设的两条隔离**：① Prose 与审稿规则/隐秘 Canon 的直接读边界；② 五 Lens 及同一 Finding 的三个 Verifier 彼此独立。这两条是**不可通过新项目配置关闭**的结构约束。原作者 workflow 本身与项目个性化规则（第五 Lens、风格、人物、语言/长度、合法来源选择）必须分开；允许适配信息字段及路径，但无权改变角色职责、票数阈值或将 Canon 决策交给执行器。

### 0.2b 方法一致性的验收证据，不以名称、文档或单测总数代替

1. **权威源冻结**：Atom-00 为上游上述资料列出 commit、文件路径、Git blob 与本机字节 SHA；`third_party` gitlink 和模板发布身份不因后续工程改动而漂移。若上游文件缺失/不匹配，报告 `UPSTREAM_METHOD_BASELINE_BLOCKED`，不得声称已证明方法保真。
2. **基线分层**：`UPSTREAM_NORMATIVE_BASELINE`=作者公开明确写出的职责/阈值；`PRE_REFACTOR_IMPLEMENTATION_BASELINE`=仓库旧源码和可以真实取证的旧行为（可能含 bug）；`POST_REFACTOR_BEHAVIOR`=新代码实际请求/消费者。不能把旧代码里已存在的绕验 bug 当应保持的“正确方法”。旧实现若因缺私有文件无法断网重演，明确记 `BASELINE_EXECUTION_UNAVAILABLE`，以作者规范及固定旧代码证据判断，不伪造重演。
3. **每个受影响 Atom 的唯一方法差分清单**：`METHOD_ID | UPSTREAM_PATH/BLOB/CLAUSE | BEFORE_FUNCTION+OBSERVED/UNAVAILABLE | AFTER_FUNCTION+ACTUAL_REQUEST_OR_ARTIFACT_SHA | CHANGE_CLASS(PATH_OR_IDENTITY_ONLY / ADAPTER_EXTENSION / METHOD_SEMANTIC_CHANGE) | PERMITTED_OR_RETURN | NEGATIVE_CASE | CONTROLLER_VERDICT`。将它汇入该 Atom 既有报告即可，**不另建庞大自证系统**。
4. **真正比较输入与职责**：冻结同一个虚构项目材料后，能在旧代码受控运行的职责比较路径/字段/消费者；对旧版不可运行的模式以作者明确规则为 oracle。白名单允许根路径、实例 ID、来源修订键、脱敏回执格式等**纯工程身份差异**；禁止为让快照一致而删除 Prompt 约束、借用其他 Lens 结果或将原方法步骤整段替换。新的 ADAPT/ORIGINAL 没有旧版行为参照时，必须以规范角色边界及实际 11 阶段消费者证明。
5. **失败触发**：M01–M16 任一适用项证据缺失/行为反例、把 `PATH_OR_IDENTITY_ONLY` 写成实际语义变更、修改了上游 pin/三票阈值/四角色权限而无公开源或用户授权，Controller 必须 `RETURN_METHOD_DRIFT`；若原始资料确实不可获取，则 `EXTERNAL_INPUT_NEEDED` 而不是签通过。Writer 只修受影响代码与下游，不得修改测试 oracle 或弱化 M 合同求绿。

### 0.3 真正的成功定义

一个没有苍歧原稿、没有 J19 合同、没有旧 v5 项目数据的新工作环境，仍可创建/导入独立项目并按以下门禁工作。离线模拟证明通用消费者链；最终产品验收还须用所有者提供的实际写作输入包走通经批准的真实生产路径，不把模拟冒称 Live：

1. 完成受控 bootstrap 后，`doctor --app-only` 明确显示引擎/方法/依赖是否就绪，且不以“没有项目”误报故障。纯源码 clone 如缺第三方构建只能返回明确 `RUNTIME_MISSING`，不得冒充 `ENGINE_READY`。
2. 从零创建一个**不带任何苍歧事实**的项目。
3. 导入 Markdown/TXT/JSON 原始稿并保留来源及未确定事实；同一项目多个来源和多次修订可以明确选源，旧来源快照不因新导入丢失。
4. 在新项目中按自己的语言、人物、篇幅、来源、Arc、角色规则创建合法工作合同；至少支持 **三种不同的工作意图**：① `INSERT_BETWEEN`（在两个确实存在的源位置之间插写，验证前后锚）；② `ADAPT_SOURCE`（把既有完整章节/选定段落/JSON 节点改编为新正文，按源范围或 JSON Pointer 验证，不虚构双边锚）；③ `ORIGINAL_EPISODE`（已有经确认的项目 Canon/Arc/Style，但没有待改编原稿，允许原创首章及续章）。新增后两项是 StoryStudio 产品扩展，不是作者已公开证明的“自动量产同级质量”。
5. 使用真实的通用生产调度/读取/消费者执行 Plot → Cards → Brief → Prose → 两层 Lint → 五 Lens → 三反证 → Completeness → Refine → Re-review；离线门以隔离网络的模拟模型响应验证角色间实质消费和可读产物。产品验收另以所有者指定的实际输入包验证要求/材料完整映射、真实 Provider 生产、审查和导出；不得把模拟冒称 Live，也不得把工程验收等同于用户对故事质量的接受。
6. 生成并校验项目独立的 source/contract/run/review 证据；多 run 同作品候选必须并存、已接受正本只在明确晋升后变动，能够中断恢复和导出。
7. 同机两个完全不同项目运行互不串资料、互不误用凭据。
8. 旧 J19 和三场 v5 数据完整：J19 只有**显式只读挂载**才可访问；v5 项目经验证迁入外部数据根并由明确实例身份选择，未授权不自动创作。新项目不读取任何旧场景资料。
9. 同一份冻结的官方工作流不变量 M01–M16 在新项目**真实消费者**中得到逐项证据；四角色直接可读资料、Prose 输入隔离、五 Lens/三反证独立性、Canon/Revision/Sprint 门不被改写或绕过。
10. Atom-00 至 Atom-10 均有实际**独立只读子智能体**读取原始材料后的完整 ACCEPT 或阻断记录；危险 cutover 前额外核对，最终方法差分与完整操作回归无未处理 RETURN。

**只删去“J19”字符串或把目录重新命名不算完成。** 必须以原八项以及以上两项的实际行为证据验收。

### 0.4 R2 已发现的十一项缺口（保留且由 R3 加严）

**以下 B01–B11 为 R2 已核实的代码行为；本轮新增 C12–C22 以上述 R3 独立审查为准。修复要求比原 R2 更严格；未知本地行为不可直接算已证实。**

| 编号 | 现有源码事实 | 必须修复的根因 | 不能接受的假验收 |
|---|---|---|---|
| B01 | `cnw_runner.literary_source_freeze` 以 `script.relative_to(ROOT)` 写 `source:`/`manifest:` 键；其验证器以 `ROOT / 旧相对路径` 回读 | **仓库外项目不能用这种键，且旧 TS run 已保存旧键**。新增 V2 项目相对身份；旧键要用仅凭明确旧根映射的只读兼容解析，核对原始字节 | 只改 `workspace` 默认值，或修改旧 `run_state` SHA |
| B02 | `cnw_roles.REFERENCE_ROOT` 及 `cnw_project.init_project` 从 Git 忽略的 `runtime/reference/cnw_97ad71fe5e5e` 读模板 | 全新 clone 必须有确定性 bootstrap/校验；源码就绪与环境就绪分别报告 | 没有模板还把 `doctor` 判绿；暗中读取本机旧运行目录 |
| B03 | `cnw_roles.build_role_packet` 比较旧合同 `policy_sha256` 与**当前单一政策文件** SHA | 旧 J19 历史、**尚待继续执行的 v5 三份合同**都需要版本化政策读取；新旧证据精确匹配 | 只保留旧读档、但让 v5 被拒绝；直接替换旧 SHA |
| B04 | `cnw_runner.produce` 遇 `project_id.startswith('FICT_')` 会走 fixture 特例 | 两个虚构项目可作为数据，但**通用生产路径测试必须使用非 `FICT_` ID**，再注入断网 Provider 测试替身 | 两个 `FICT_` 测试通过就宣布真实项目通用化 |
| B05 | `cnw_project.build_source_bound_contract` 目前写死 `unit.language='zh-CN'` | 语言必须从项目明确设置进入 contract，回读到角色请求与长度策略 | 用英语材料，却在合同中仍生成中文语言 |
| B06 | `p2_cost_guard` 固定 `ROOT/runtime/private/p2-cost-ledger.json`；CritiCS/Bridge 固定 `ROOT/runs` | 全部活跃写入者共享单一真实账本与锁；CritiCS 本地命名空间按项目隔离、旧原生收据可回放 | 数据文件搬出去而适配器仍写入仓库；两个同名 run 误串 |
| B07 | `studio.ps1` 入口默认旧项目、`-ProjectRoot` 还使用 `Resolve-Path` | 无项目时项目命令拒绝；新建项目允许目标路径尚不存在；`doctor` 不要求旧项目 | 用历史 J19 工作区测试 `doctor` 通过 |
| B08 | CNW `stage_identity` 包含函数代码哈希，策略/代码变动会影响旧运行身份证据 | 区分旧历史只读复核、v5 原 run 的迁移后可继续、全新 run；每类明确验证行为 | 把旧已完成阶段重跑后替代原证据 |
| B09 | 原计划最终段先要求 Controller ACCEPT 再“提交”，但 Controller 又需核对候选 Commit/Tree | **先本地正常提交形成 C/T → Controller 只读审查 → ACCEPT 后推送 → 远端回读** | 无候选提交的假 C/T 或 Writer 自签 |
| B10 | `cnw_contract.check_required_fields` 强制所有工作含 `before_anchor/after_anchor`，`cnw_project.build_source_bound_contract` 强制已有原稿和行号 | “从零创作新小说第一章”不应伪造源文件或前后锚。新增 `INSERT_BETWEEN` / `ADAPT_SOURCE` / `ORIGINAL_EPISODE` 三种工作意图与各自严谨的来源/Canon 约束；详见 Atom-03 | 新建空项目后必须先编造两行原文才能生成第一章 |
| B11 | 公开 `studio.ps1` 暴露 `prepare-live/live-call/accept-role/w10-*` 等命令，但部分调用的 `tools/cnw_live_executor.py` 等目前仅见于本地未提交 W10 | 逐个命令解析其真实实现与本地消费者：要么提炼进已提交的通用组件，要么清晰迁出并从活动 CLI 移除。冷 clone 禁止留下悬空派发 | 本地靠未提交文件能用，干净 clone 命令调用却 `FILE_NOT_FOUND` |

**交付级别必须分开：** `ENGINE_SOURCE_READY`、`CORE_RUNTIME_READY`、`OPTIONAL_NK_READY/UNAVAILABLE/DISABLED`、`OPTIONAL_CRITICS_READY/UNAVAILABLE/DISABLED`、`GENERIC_SIMULATED_OFFLINE_E2E_VERIFIED`、`LEGACY_READ_ONLY_VERIFIED`、`V5_EXISTING_RUN_MIGRATED`、`V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK`、`GENERIC_LIVE_PRODUCTION=NOT_RUN`。后一状态是确定性的可恢复性预检，**不是**重新开启生产或宣称 `LIVE_EVIDENCE_VALIDATED`。不得以一项替代另外一项。

**不可变约束的冲突裁决：** 若“原 TS run 字节不变”与“将它移出仓库”发生冲突，先通过迁移映射和冻结状态校验；若不可能则保留原件并标 `V5_CUTOVER_BLOCKED`，不得伪称已迁完。本计划不授权以新 run 取代旧 run 或为消除 TS 阻断执行付费生产；通用输入包必要付费验收依 0.3a 单独分层。

### 0.3a 输入包生产目标与既有 Atom 有限依赖补充（项目所有者授权）

最终产品标准是：用户提交写作输入包，应用解析并完整保留其要求与材料，由应用自行建立内部项目/合同/Run/来源身份，将每份材料送入 CNW 正确岗位，按固定原作者工作流真实生产、审查并导出故事。用户不应手工填写内部 SHA/Run ID/合同或逐阶段操作。输入包描述作品和要求；StoryStudio 决定并执行固定 CNW 流程。

本补充纳入现有 Atom，不新增 Atom、不改变公开阶段/岗位或 M01–M16：

1. **ATOM-04：**现有输入包入口须表达并传递执行意图；将来源获取策略与模型执行模式分开。应用自行管理项目、合同、Run、来源选择、阶段身份和输出。包清单、必需材料、写作要求和工作意图必须在 Provider/费用边界前完整验证；缺项、冲突或不能映射时报告具体问题，不静默丢弃。
2. **ATOM-05：**新通用项目每次 Provider 操作显式携带绑定项目实例的费用上下文，接入既有单一账本、锁和 accounting primitives；不得靠请求间改模块全局 `LEDGER/config` 选择项目账本，不得复制多个可写全局账本或增加共同 Provider 并发额度。历史费用、`PENDING`、`UNKNOWN_NOT_ZERO` 和原字节保持不变。
3. **ATOM-06：**输入包生产复用既有正式 `execute_checked`、真实阶段消费者、审稿反馈、Refine、受影响 Re-review、恢复与导出；不得另造简化生成器。完整保留四角色读集、两层 Lint、五 Lens、每 Finding 三个独立 Verifier、2/3 门槛、Completeness→Refine→新稿 Re-review、Canon/晋升和 Sprint 约束。`MOCK_ONLY/SIMULATED` 不得冒充 Live、正式前章或用户创意接受。
4. **ATOM-07：**分开核验项目/Run/合同/来源/Policy/Workflow 身份及可信独立签收，与对具体操作有效的用户 Live/费用授权、Provider 配置、额度/期限及费用上下文。不得把工程 Controller ACCEPT、CLI 开关、拥有 Key 或普通 JSON 当成生产授权；不得把已签收结果 `provider_call_authorized=false` 改为 true。旧 J19/TS 预检身份不解锁新项目，TS 恢复/迁移/cutover 仍须原危险门。
5. 受影响 ATOM-08 只做不删除、移动或切换旧私有数据的安全工程；ATOM-09 对适用实现执行隔离离线 E2E。此前对精确候选已接受且身份未变化的证据可按原计划规则复用，不追认历史 RETURN。

**验收分层：**离线工程门证明通用身份、权限/费用边界、正式 CNW 消费链和负例已实现；实际故事交付门使用项目所有者提供的输入包，核对包内要求与材料完整映射、真实 CNW 生产/审查/导出、Provider 回执与适用费用证据。项目所有者已授权计划内必要付费验收，无需再次询问或把未检查凭证当作阻塞；仍须等待活动计划及真实代码候选的精确独立 ACCEPT，并满足可信签收、项目/合同绑定、Provider 和费用政策。密钥内容与来源仅限本机受控使用，绝不写入 Git 或公开证据。模拟结果不得通过 Live 验收。实际故事和创意是否满足用户要求，以产物及用户阅读为准。

本补充不授权真实 TS 生成/恢复、私有数据迁移、危险 cutover、新生产默认启用或历史证据改写；`CUTOVER_BLOCKED=true` 维持，直到原有危险门单独接受。保持原批准源 SHA 与全部历史裁决不变。

---

## 1. 总体施工纪律（所有 Atom 均适用）

1. **一个 Atom 的“当期独立完成门”通过、独立 Controller ACCEPT 后，再进入下一个 Atom。** 不得把必须依赖**后续 Atom** 才能实现的集成测试提前当作当前 Atom 前置门；整体总验仍统一要求 Atom-09 的全部真实模拟成果。Writer 只负责施工和提供候选、原始证据；Controller 只读，不修改产物。对涉及源码的 Atom：**Writer 先在本地 main 正常提交，获得真实 C/T；Controller 只读审该 C/T 和未提交保护清单；ACCEPT 后 Writer 正常推送；Controller/Writer 分别做远端回读。** RETURN 用追加修复提交产生新 C/T 再复审。归档清点而无源码变动的 Atom，可按归档 manifest SHA 验收，无须制造空提交。
2. 每一轮先读取实际 Git HEAD/Tree、工作树、现存私有运行记录，再定点修改。已验证且身份兼容的证据复用，不重复付费。
3. 保护优先级：原稿原字节、私有输入、历史 Provider 原始响应、账本、运行日志、已有 Controller 原消息、未提交 W10 工作，高于目录美化。
4. 只允许**复制→验证→切换引用**，不允许未备份就移动/删除私有文件；本任务禁止清理既有私有工作区。
5. 不允许通过跳过来源校验、使用通配的伪造审查凭据、写 `pass=true`、删除失败收据等方式让程序变绿。
6. 禁止自动将新项目角色资料、口吻、语言、字数、声线、禁句、剧本胜负或个人偏好设成苍歧默认值。
7. 不额外引入必须联网的运行依赖，除非已用当前冻结实现证明必需；所有新初始化/测试均先离线。
8. `main` 上按 Atom 正常追加提交，不重写旧历史；依用户原有规则由 Controller 复核候选 C/T，再正常推送并核对远端回读。禁止 Writer 自签。
9. 未被触发的分支不要求额外真实付费运行；只核对源码、固定原始回执和离线负例。发现执行结果缺失，明确标 `NOT_RUN`。
10. **迁移作业互斥**：在复制/切换工作区和账本时确认不存在活跃 Writer、NK/CritiCS 子进程和未落盘结算；取得必要的文件锁/迁移锁。若运行未停或无法确认，保持只读/停止迁移，不通过覆盖解决竞争。
11. **跨 Atom 的“影子配置”规则**：Atom-02 新 schema 可以创建、验证和打快照，但旧活动配置/账本消费者未完成改造前，不得切换它们的读取路径；Atom-03/04 才逐消费者转接；Atom-05 仅在全部转接验证后执行数据切换。不能让中间 Atom 自己破坏下一 Atom 的正常入口。
12. 项目所有者已授权计划内必要的通用输入包付费验收，但实际调用必须等待活动计划及代码候选的精确独立 ACCEPT，并通过身份、可信签收、Provider 与费用政策检查。离线/定点测试仍对 Provider、NK、CritiCS 网络使用明确断网防护和可审计替身；不得因 `FICT_` 特例绕过通用生产合同。此授权不包括 TS Live/恢复。
13. **模拟绝不等于 Live**：模型离线模拟产物只能作为通用流程功能证据；真实小说水准仍为 `NOT_VERIFIED`。真实 Provider 调用在全套离线测试与旧数据迁移期间强制拒绝；仅计划内、精确候选获准后的通用输入包验收可按 0.3a 调用。
14. **项目公开正本不能被试稿覆盖**：任何新 run 的阶段写入/编辑计划先进入本 run 候选区，保留原始历史；只有经指定接受/晋升门与原子 CAS（期望版本）才更新项目正本。出错不能留下“已更新正文但无凭据”。
15. **新 Live 授权默认关闭**：新建项目的 CLI 生产预检须检查显式用户授权、模型配置和成本政策。历史 J19/v5 冻结配置不得因本条被改写。该 Atom 内的离线测试不得启用真实 Provider；本计划内实际输入包验收另受 0.3a 约束。
16. **源码变更与数据迁移分离签收**：Controller 先核对引擎预备代码和模拟回归，再允许唯一指向新数据的 cutover；迁移后如有路径映射失败，回滚活动指针，不得编辑原 run 企图修复。
17. **真实成果而非测试数验收**：所有结论至少给出具体项目产物、消费链 SHA、失败负例 raw、候选提交与远端回读；运行通过个数和文档中写“支持”均不构成功能成果。
18. **原方法保护优先于目录美化**：所有修改在对应 Atom 的 M01–M16 适用行接受独立只读子智能体审查；不得用“仍有11阶段”替代职责/读集/票数/反馈/Canon/Sprint 的真实证明。
19. **单一子智能体验收责任**：Controller 不启动则停止在 `CONTROLLER_UNAVAILABLE`，Writer/同一上下文/被测脚本都不能代签；Controller RETURN 不推送、不跳 Atom、不改作者方法阈值，修复后重新候选 C/T 复审。
20. **活动入口不抢跑**：Atom-01 先修唯一活动计划指针；新 resolver、policy、CLI、迁移模块以受控影子路径工作，旧明确可用入口在新完整回归接受之前不得破坏；final cutover 才令旧场景不可默认触达。
21. **方法测试不膨胀**：尽量复用已有 tests、固定作者资料和两个有源+一个原创 fixture，M01–M16 的结果合并写入本 Atom 方法差分和独立 Controller 记录，禁止为了验收另起服务或不断增加形式化证据。

### 1.1 R5 独立只读 Controller 子智能体：真实启动、学习、签收与强制驳回

**身份与启动（Atom-00 前必做）**：Writer 必须真正调用 Codex 当前环境支持的**独立子智能体**，指定 Controller 仅读权限；**不能**在 Writer 同一代理上下文中写一段“Controller: ACCEPT”，不能让被测代码自身模拟一个 Controller，也不能请 Writer 生成预置赞成票。尽可能整个 R5 使用同一独立 Controller；如果子智能体会话无法跨 Atom 保留，重新创建只读子智能体并重读下列全部权威原件及上一 Atom 的实际签收消息，不可只投递 Writer 的总结。若当前 Codex 环境没有独立子智能体/无法配置只读能力，应当停在 `CONTROLLER_UNAVAILABLE`，保留现场而非代签。**本计划只规定以后执行的行为，不冒称编写计划时已经实例化了该子智能体。**

**Controller 首次必须独立读完（不是 Writer 摘要）**：

- 当前导入仓库的 R5 **全文及实际 SHA**，其 Atom-00…10、M01–M16、成功/失败/停止边界，和当前用户关于“不破坏原作者工作流、偏移就驳回重做”的指令；确认它知道本次目标是通用化而非继续 J19 生产。
- 现场仓库当前有效 `AGENTS.md`、`docs/governance/GOVERNANCE.md`、`docs/governance/PLAN_AUTHORING_STANDARD.md`、`reviews/CONTROLLER_PROMPT.md`、`reviews/P3_1_CONTROLLER.md`、`plans/CNW_PUBLIC_REPLICATION_GOAL.md` 的 C01–C15、当前活动计划指针、`implementation/CNW_ROLE_INPUT_OUTPUT.md` 与相关技术/验收合同；**识别其中旧 J19/预算条款属于历史工作范围**，新用户范围变更不取消数据安全、原方法、费用、main-only、证据与创意批准的边界。治理的旧“验收后才形成 commit”若与要求审精确 C/T 冲突，采用 R4 已确定的真实顺序：本地正常提交形成 C/T → Controller 读 C/T → ACCEPT 后正常推送。
- 固定上游 `workflow.template.yml`、`ai_roles.template.yml`、`THREE_LAYER_REVIEW.md`、`HOW_TO_ADAPT.md`、`templates/CLAUDE.md`、Workflow 01–05、Sprint 模板、`GETTING_STARTED.md` 和许可证；按作者真实文字建立个人审查判断，**不能把我们的 M01–M16 当成原作者原文**。
- 该 Atom 实际受影响源码、完整 patch、允许的项目/运行原始证据、测试输出和失败负例，实际 C/T、受保护 WIP/账本/历史哈希；必要时通过只读文件/GitHub 工具读取代码原件。**不得只读 Writer 的验收摘要**。仓库外私有输入只在得到已授权只读访问时检查，不向公开工具泄露全文。

**初始化口头确认门**：子智能体在开始审 Atom-00 前先独立回一条 `CONTROLLER_BOOTSTRAP_ACK`，列实际已读来源 path+可核 SHA/版本、当前目标、核心方法不变量、其只读权限限制、当前未知项；漏读资料即 `EXTERNAL_INPUT_NEEDED`，不得凭“理解了”三个字通过。Writer 将原始子智能体消息保存在私有验收日志及公共脱敏索引，不得编辑原判断措辞。

**每个 Atom 的固定控制回路（在其现有验收门内，不凭空增加新 Atom）**：

```text
Writer 自查现场、遵循 Atom 输入/写入边界和 R5 M 合同
    → 实装该 Atom 的最小真实功能，收集原始产物和必要负例
    → Writer 归档 diff、测试命令+exit、结果 SHA、费用及 WIP 不变量
    → 有源码改动时在现有 main 正常本地提交成精确 C/T（不推送）
    → 独立只读子智能体重新对照完整计划/本 Atom 当前门/M01–M16 适用项
    → 子智能体独立查源代码、实际角色请求/产物、历史身份及日志
    → ACCEPT：Writer 才正常推送、远端 C/T 回读一致，进入下一 Atom
      RETURN：指出最早偏移、根因、精确修复和最小必要复验；Writer 修复并新增本地提交，重审，不推送问题版本
      EXTERNAL_INPUT_NEEDED：事实无法获取，保持现场与已完成原件，不把不可验证当通过
```

**Controller 必须针对本 Atom 回答 6 个可判真的问题**：①目标/允许范围是否偏移？②作者 M01–M16 哪些适用、是否实质被改变？③本次新功能实际读取哪个原始输入、产出哪些有字节的结果、被什么消费者使用？④有没有越权读/自动 Canon 晋升/审稿共享/绕过三票/伪 Live 等反例？⑤旧 J19/v5/W10/账本历史 SHA 和可继续使用的入口是否受损？⑥哪些前置已证明可复用、哪些只完成离线模拟或仍 NOT_RUN？Controller 没有读到某个关键原件，不允许 Writer 代答其结论。

**权限红线**：Controller 只读原文件与返回独立文本判断；不得修改本地/远端代码、测试、合同、Canon、账本、验收日志，不运行测试或生产命令，不发请求、不支付 API、不调用写工具、不再派生执行代理。Writer 执行测试；Controller 只能审查命令/原始输出并清楚说明“未亲自运行”。Controller 不能替用户给新故事或旧 J19 的艺术满意、Canon 事实批准或真实 Live 证据签字。

**返回协议（原始回答保留，不允许 Writer 代填）**：

```text
CONTROLLER_VERDICT: ACCEPT | RETURN | EXTERNAL_INPUT_NEEDED
ATOM_ID: ATOM-XX
REVIEWED_PLAN: <R5 的实际 SHA、路径>
GOVERNANCE_READ: <实际路径和版本，缺的逐项列出>
UPSTREAM_METHOD_PIN: 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
REVIEWED_COMMIT: <本地候选 C；零代码阶段为 NOT_APPLICABLE>
REVIEWED_TREE: <候选 T；零代码阶段为 NOT_APPLICABLE>
REVIEWED_WORKTREE/WIP: <实际可查范围及 protected 清单>
METHOD_GATES: <M01..M16 的 PASS / NOT_APPLICABLE / RETURN / UNVERIFIED + 原因>
CURRENT_ATOM_EFFECT: <真实输入→实际输出→消费 hash/路径、期望是否达成>
RAW_EVIDENCE_READ: <实际看过的文件/收据路径及 hash；不可查的写 UNAVAILABLE>
METHOD_DRIFT: <NONE | 文件:行/函数 + 原上游要求 + 实际不一致>
PRIVACY_LEDGER_HISTORY: <原字节/哈希及费用边界核查结论>
BLOCKERS: <精确的缺失资料；无则 NONE>
REQUIRED_CORRECTION: <RETURN 时最早根因、可执行改法、受影响最小复验；无则 NONE>
REUSE_APPROVED: <未受影响已验证项>
NEXT_ACTION: <该 Atom 可进入下一步或必须停留>
```

**机械问题不无限扯皮**：RETURN 必须具体指出文件/行/可复现偏差和修正目标，不以“多写文档、多加用例”代替实际效果；连续两次同根因 RETURN 应回到输入、调用图与真实消费者定位，不随机重试模型。已经核过且哈希未变的证据不重复付费。**不能因为当前 Atom 功能尚在后续 Atom 才可实现而提前索取完整11阶段证据**；当前阶段验当前闭环，总体完整方法由 Atom-09/10 终验。

### 1.2 每个 Atom 的方法保护关注点与 Controller 签收门

| Atom | 本阶段需由子智能体重点检查 | 当阶段必须有的实证；完整端到端按 Atom-09 |
|---|---|---|
| **00** | 固定作者来源、M01–M16 规范基线、治理/计划冲突、现存旧路径/W10/历史/账本清点 | 作者 blob 与现场缓存实际 SHA；方法基线可读；独立 `CONTROLLER_BOOTSTRAP_ACK`；旧证据只读封存。缺关键原件 BLOCKED |
| **01** | 新项目路径/实例不污染作者模板，先更换旧活动计划指针；旧入口不过早废弃 | 无苍歧新项目模板、身份碰撞拒绝；`AGENTS`/治理/CLI 文档只有一个活动 R5 指针、旧内容完整历史可追；Controller 读到变更 |
| **02** | 全局/Provider/项目策略解耦不重写11阶段、票数、Sprint 门或历史 policy SHA | M01/M07/M08/M13 的新旧策略快照及 hash；旧只读按原身份读，未适配消费者不先切换 |
| **03** | 三工作意图来源选择不绕过 Plot→Brief→Prose 角色材料边界；Canon 未决项不晋升 | 选 B 真读 B、JSON Pointer、无源第一章来源合法；方法 M02–M05/M11/M15 的输入规划证据 |
| **04** | CLI 只有路径/路由变化，没删作者操作职责或真实 Consumer；新旧入口灰度安全 | supported 命令能定位实现、明确 project required；旧明确入口在 cutover 前可用，新入口不会回退 J19 |
| **05** | 同一 run 的 Plot/Cards/Brief 消费顺序与候选隔离；Canon/修订晋升只在项目级 CAS 发布 | M03/M10/M12 的阶段产物和拒绝冲突；历史 run/账本不变；进入 cutover 前子智能体只读审核数据映射和回滚能力 |
| **06** | **方法中心强审**：M01–M16 中所有受影响项，特别四角色读集/五Lens/三反证/Completeness/Canon/Sprint；辅助不代岗 | 实际消息结构、上游 source→函数矩阵、正反例；不许只报11个阶段、mock 文件数或测试通过数 |
| **07** | 新合同/Controller 门只证明 preflight，不能绕过三反证/作者批准/用户接受；历史运行可恢复 | 跨合同票错配拒绝、旧身份/阶段 hash 真实结果，Controller 不自签、无新请求 |
| **08** | 清理旧场景仅移活动项目事实，不删公开方法参考、合法 Workflow 01–05 / 标准操作或后续消费者 | 受跟踪/受忽略/历史归档对账，clean clone 不泄旧内容且所有通用方法入口存活 |
| **09** | M01–M16 全适用合同真调度/产物消费；五话 Sprint/Canon/Revision/Handoff；跨项目与 failure 注入 | 三创作意图、EP001/002、至少五话 Sprint、Workflow 01–05/标准操作、各 review 和真实 request trace 的断网模拟；退回偏差，不许以 mock 评文学效果 |
| **10** | 总体方法逐项闭环，先前各 Atom ACCEPT 是否指向对应 C/T 和原件，过渡期旧入口是否安全退休 | Final `METHOD_FIDELITY_DIFF` 逐项源/代码/实物；全验无 RETURN；离线与 Live 状态分开、正常 main 远端回读；用户创意等待亲读 |

**危险切换附加门（不另造 Atom）**：Atom-05 对旧 v5 及 J19 私有文件/账本的唯一活动指针进行 cutover 之前，Controller 必须读迁移计划、路径图、hash 和锁/静止状态，返回 `CUTOVER_READ_ONLY_ACCEPT`（仅允许切换，不代表运行功能总验）。Atom-09 全链与旧入口双路回归通过且 Controller 接受后，才允许**使新通用 CLI 成为唯一默认活动入口**；不成熟的新入口不得提前覆盖旧可用路径。`main` 本地提交可以分阶段存在，**有方法破坏或旧入口退化的候选不得推送**。

### 必须写出的共同验收记录

对每个 Atom 写私有或公共的适当记录：`ATOM_ID / INPUT_SHA / CHANGED_FILES / TEST_COMMAND / RAW_OUTPUT / NEGATIVE_TEST / PROVIDER_REQUEST_DELTA / CONTROLLER_VERDICT / CANDIDATE_COMMIT / CANDIDATE_TREE`。公共记录只包含可公开标识、哈希及脱敏摘要，不包含私有稿件/密钥。

---

## 2. ATOM-00 — 现状封存与全量依赖清点（零代码改动）

### 00.1 读取与封存

在现有 StoryStudio 本地目录运行只读操作：

```powershell
$ErrorActionPreference = 'Stop'
git status --porcelain=v1 -uall
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^{tree}
git ls-files
git ls-files --others --exclude-standard
git submodule status
```

执行 AI 还须实际列出 `workspace/`、`runtime/`、`runs/`、`deliverables/`、`inputs/private/` 等 Git 忽略目录内的**路径、大小、哈希和数据级别**；不要将任何私有文件内容输出到公共仓库。

用 `Get-FileHash -Algorithm SHA256` 对六个 W10 未提交文件、三个 v5 项目合同、TS 已建 run 的 `run_state.json`、旧 J19 原始证据、全局账本分别登记。对于不存在的文件，报告 `NOT_FOUND`，不得编造哈希。

额外清点：`runtime/reference/`、`runtime/patched/`、`runtime/envs/`、上游 `third_party` 子模块真实 gitlink/提交、依赖锁、真实 `cnw_live_executor.py` 等未提交文件，以及 `source_manifest.json.original_path` 等历史绝对路径。**逐项目列出**已注册的 sources（数量/身份/所在路径/manifest revision）、多次导入修订历史、所有合同引用的 manifest 快照是否实际存在，以及是否存在单行 JSON/仅一个源行/无源原创单位；缺少旧快照是迁移风险，不能用“当前 manifest”冒充。对于 v5 按附件脚本检验每份 F01 是否在各自项目 `_INBOX/originals/`；旧 J19 另清点其外部 Release 和 `ROOT/runs` 的 CritiCS native 证据，不混为一类。
**不可省略的独立证据面**：`git ls-files`（当前 HEAD）/全部 Git 历史（仍可追溯）/受忽略目录/未提交与 untracked W10/三个 v5 真实 `project_id`+`contract_sha`/TS 失败码及冻结键/旧 J19 run/账本 `PENDING` 与 `UNKNOWN_NOT_ZERO`/原始供应商请求与 raw/运行中 NK、CritiCS 进程与其写入目录/依赖 pin 和许可证/独立 Controller 原消息。将是否可访问逐一填 `OBSERVED/UNAVAILABLE/NOT_APPLICABLE`；不可见不能当作不存在。仅目录存在不等于在干净 clone 可重建；逐项标 `tracked / ignored-but-rebuildable / ignored-irreplaceable`。

在现有仓库的**同级目录**创建私有迁移归档，例如：

`<StoryStudio父目录>/StoryStudio_Legacy_Archive/<本次冻结身份>/`

归档目录必须位于 Git 工作树之外，访问控制不比原私有数据更宽。分开保存：

- `tracked_history/`：旧 Git 受跟踪文件的迁移前字节和路径映射。
- `private_inventory/`：私有项目/运行/原稿/收据的**只读副本或受限备份**，禁止公开上传。
- `manifest.json`：旧相对路径、归档位置、大小、SHA256、文件类型、来源 HEAD、备份结果、是否允许新应用默认访问（统一 false）。
- `README_RECOVERY.md`：如何只读查看历史，怎样显式挂载旧项目、如何回滚本次通用化；不得包含密钥或全文小说。

复制前检查真实私有文件规模、外部目录容量、访问权限、长路径/大小写冲突与软链接/junction，不盲目追踪外部链接。先由现场**计算**待复制字节数 `S_copy = Σ 实际源文件字节`、不可替代备份字节数 `S_backup`、操作暂存及回滚预留 `S_tmp`；在目标卷证明 `free_bytes >= S_copy + S_backup + S_tmp`（同盘已存在的校验副本不得重复计算，跨卷不得假设 rename 是原子）。`S_tmp` 按实际文件系统与事务方案测定，不预填“2倍/3倍”万能常数。空间不足 `DISK_CAPACITY_BLOCKED`，保持原数据不动。**不估算本机磁盘体量或改造工期**：本机大小、文件系统、活跃锁、第三方缓存、移盘方式尚未实测；迁移将涉及备份/映射/双读校验和回滚存储，额外磁盘成本由现场上面的实际测量计算。模型费用本轮为零，但 CPU/内存/磁盘 I/O 及 Controller 审核工作并非零成本。只按已清点的重要证据和可再生成工具缓存划分备份优先级；不可再生的私有项目、合同、源稿、raw、账本必须完整备份。所有文件复制后逐字节 SHA 回读；仅完成备份后允许改动可能影响运行的引用。若复制失败，保留原地文件并返回 `ARCHIVE_INCOMPLETE`，不得以“历史 Git 还能找回”为由删除 Git 忽略的私有文件。

### 00.1a R5 方法基线与独立 Controller 启动（此 Atom 不改代码）

- 按 §0.2a/0.2b 逐一列出 M01–M16 的**原作者固定条文**及现有源码对应函数/读取边界；至少覆盖 `cnw_roles.py` 的 `AUTHOR_ROLE_READS/build_author_role_messages`、`cnw_runner.py` 的每阶段执行/审稿/三反证/Refine/Sprint/支持 hook、`cnw_review.py`、`cnw_lint.py`、`cnw_project.py`、`cnw_import_workflow.py`、`cnw_maintenance.py`、`cnw_sprint_live.py`、`cnw_recovery.py`、相关 prompts/policies；标 `AUTHOR_METHOD / STORYSTUDIO_ADAPTER / LEGACY_SCENE_DATA`，不以代码现状当规范。
- 对已有可合法读取的真实请求或纯离线测试，保存旧角色读集与审稿构造的真实身份；**不得新增付费**或执行将写回旧 run 的历史核验。无法从旧场景脱离的当前漏洞如实标 `PRE_REFACTOR_IMPLEMENTATION_LIMITATION`，以后以作者规范对照，不造出“曾在旧环境跑通”的证据。
- 真正启动一个独立只读 Controller 子智能体，投喂其自行读取的 R5 全文、仓库治理、作者固定原件、C01–C15、当前 C/T、现场保护清单；取得真实 `CONTROLLER_BOOTSTRAP_ACK` 和 Atom-00 verdict。无法真实启动就停，不能用 Writer 的总结/预设模板代替。
- 先只读查明 `AGENTS.md`、`docs/governance/GOVERNANCE.md`、`CODEX_START.md`、README/旧 plans 哪些仍指向 J19/P3。把应改的活动入口与历史原字节列出，为 Atom-01 一次受控修改准备；不在 Atom-00 偷改。

### 00.2 全仓扫描并分类

对**受跟踪 + 未提交 + Git 忽略但会被运行代码读取**的路径逐一构建表：

`PATH | CLASS(engine/project/runtime/historical/toolchain/test) | ACTIVE_CONSUMERS | SOURCE_IDENTITY | SOURCE_REVISION | OLD_ROOT -> NEW_ROOT | ACTION(KEEP/EXTRACT/MOVE/REWRITE) | RISK | TEST`。所有读取路径要记录其归属（项目内、共享 J19 release、原生 CritiCS root、工具缓存、全局费用）。

至少搜索：

```powershell
# 有 rg 时执行；没有就使用 Python 等价文本扫描。
rg -n -i 'cangqi|苍歧|J19|J20|CQ-J19|F01|EP001|JUN-SINGLE|Cangqi_Jun|workspace[\\/]cangqi|p2_06|first.scene|legacy.scene' --glob '!*.lock' .
rg -n 'ROOT.*workspace|ROOT.*runs|ROOT.*deliverables|p2-cost-ledger|production.example.json|cnw_production_policy.json|SOURCE_ROOT|project_root|contract_sha256' tools config tests
```

扫描命中不得全部机械删除。判断它是实际生产依赖、历史归档、合法测试 fixture、通用文档还是第三方 pin；分类误删属于 RETURN。

**验收**：清单覆盖活跃入口及本地 W10；所有旧数据具备真实可追溯的归档位置；零生产 API 调用、零受保护字节丢失；磁盘/权限/锁/历史访问状态有实际结果；**冻结 M01–M16 规范基线与现有职责映射并取得真实只读子智能体 `CONTROLLER_BOOTSTRAP_ACK` + Atom-00 ACCEPT**，才可进入 Atom-01。若用户期望“公共 Git 历史也无法再找到旧资料”，须报告此目标与“禁止改写历史”的既有授权冲突；本次不得自行执行历史重写。

---

## 3. ATOM-01 — 冻结“引擎 / 项目 / 运行 / 历史”的明确所有权

定义并落盘 `docs/ARCHITECTURE.md` 与 `docs/PROJECT_CONTRACT.md`，采用以下逻辑边界；实际 Python 文件不必为了好看全部搬包：

```text
StoryStudio/                        # 通用应用代码，Git 跟踪
  tools/                            # 项目无关 CLI 和编排/适配器
  config/                           # 通用 schema、示例、方法与 Provider 配置
  prompts/cnw/                      # 原作者角色方法映射，不含任何作品事实
  templates/                         # 空白项目模板/通用合同模板（可放 config）
  tests/                            # 全部使用独立虚构素材/临时目录
  docs/                             # 当前通用文档，不含 J19 的历史验收正文
  third_party/                      # 上游子模块与版本 pin

<APP_DATA_HOME>/                    # 非源码，不受 StoryStudio Git 跟踪
  projects/<project_instance_id>/   # 内部不可变实例身份；显示名/project_id 为元数据
    project_identity.json             # 新项目有不可变 ID；旧项目另以受限 legacy mapping 描述
    contracts/                      # 本项目合同
    runs/<run_id>/                   # 按项目隔离的运行记录/回执
    exports/                         # 导出稿
  shared/                            # 唯一活动费用账本、跨项目锁与工具状态，不复制为多份可写账本
  tool_cache/                        # 可重建且经 pin 校验的 CNW 参考件/NK/CritiCS build/env
  archives/                          # 可选受限本地运行归档

<StoryStudio父目录>/StoryStudio_Legacy_Archive/   # 已封存旧项目/旧施工史
```

所有路径由**统一的路径解析器**和明确上下文决定：

- `app_root`：代码/固定方法；仅由应用安装目录决定。
- `data_home`：由首次 `setup --data-home` 的**用户明确选定路径**持久化、`-DataHome` 或 `STORYSTUDIO_DATA_HOME` 决定；没有用户选择时，`doctor --app-only` 可运行，但任何创建大型项目/缓存或迁移写入必须返回 `DATA_HOME_REQUIRED`。**`setup` 的持久化路径指针必须有唯一明确的位置/规则（例如仅存小型用户级本机配置；或要求后续都显式传参数/环境变量），不得把用户数据、密钥或可写费用账本塞进源码仓库。重启后的新进程必须解析为同一个真实 data_home；指针损坏/失效报错而不是静默落系统盘。**不得在用户未选择时悄悄落到 `~/.storystudio`（Windows 往往落系统盘），也绝不可默认为苍歧项目根。选定数据根后需先检查可写性、独立权限和实际剩余容量。
- `project_root`：命令行 `-ProjectRoot` 或显式 `STORYSTUDIO_PROJECT_ROOT`；缺失时，所有**项目级命令**报 `PROJECT_REQUIRED`，不得猜 `cangqi`。项目运行前必须证明此路径与已登记的 `project_instance_id` 互相匹配；非数据根内项目仅能走显式受限挂载注册（只读旧历史与可写新项目须区分）。
- `project_instance_id`：为**每个新项目**一次生成并冻结的不可变内部标识，区别于可重复的显示 `project_id`。合同、run、Controller、出账/审稿、导出统一绑定它；旧合同不增字段，使用 `project_id + frozen contract/source hash + 经签收的迁移外部映射` 做只读兼容。**移动（relocate）保留原 ID 且只有一个活跃写入路径；复制成新作品（fork / clone-as-new）必须产生新 ID，重新建立合同/项目批准，不可继承旧活跃 run、费用归属或 Controller ACCEPT。**同一 ID 在两个活动可写根出现必须 `PROJECT_INSTANCE_COLLISION`，不能仅靠目录路径相异当作两个项目。
- `run_root`：`<project_root>/runs/<run_id>`；`run_id` 只在所属项目内唯一，**新格式缓存、票和费用至少同时绑定 `project_instance_id + contract/source identity + run_id`**，不单靠可重复显示 `project_id`；旧票不得为迎合新 schema 反向改写。
- `source_root`：由**项目来源声明和实际清单**解析，非应用常量。
- `export_root`：本项目私有 `exports/` 或项目显式指定的、已验证的安全输出路径。
- `cost_ledger`：唯一可追溯的全局/配置账本；同一实际支出不得因迁移被复制成两个可写账本。

任何外部路径都必须验证真实规范路径、符号链接/Windows junction（含 Windows reparse points）、根路径包含、拒绝 `..`、拒绝跨项目越界。当前 CritiCS 固定 Python 3.11.15 的工具链**没有 `Path.is_junction()`**；不得在该环境无保护地调用 3.12 才有的方法。使用与现场 Python/Windows 兼容的 reparse-point 检测，并用真实 junction、symlink 与跨卷测试证明防护。显式用户选择的**外部源文件只允许一次性只读导入并复制/哈希封存**，不能因此授权日常生产从任意磁盘路径读取。对写入/迁移进行锁内复核，防止检查后路径被换成链接。**路径支持用户配置，不等于允许读取任意磁盘文件。** Windows 本机目标卷上要真实测试同卷原子替换/CAS/文件锁与 crash recovery，不能把 Python `os.replace()` 成功时的单次替换推广为跨卷或多文件原子事务；参考 `https://docs.python.org/3.11/library/os.html#os.replace`。

### 01.0 R5 首个代码/治理变更：更新活动入口，不改变历史职责

Atom-00 已封存后，Atom-01 **最先**在可改的当前工作树中将 R5 以原字节放到 `plans/` 下单一正式计划文件，并记 SHA；同步修复实际仍会被 Codex 读取的 `AGENTS.md`、`docs/governance/GOVERNANCE.md` 的**唯一活动计划指针/当前目标**以及 `CODEX_START.md`、README 的生效入口指向（以现场活跃消费者为准）。旧 P2/P3/J19 范围和成本叙述如实留历史档，不得伪称其以前就采用 R5；**保留治理规则的唯一 Writer、独立只读 Controller、main-only、最小影响验证、WIP/凭据/原始字节保护**。旧文档中的“J19 当前唯一要生成”的执行范围与用户此次最新指令冲突，因此作为历史工作目标保留而不继续生效；不能把它当成保留安全边界的理由来重新发起生产。

建立薄的 `legacy_explicit_only` / `generic_shadow` / `generic_active` 入口状态（命名不限；必须有可验证路由），在 Atom-09 终验前最多开启**显式影子通用测试**，不提前移走仍在被使用的旧实现/账本/依赖；不需新增复杂特性开关平台。切换新默认入口与旧入口退役的判定见 §1.2 和 Atom-09/10。每次从本地候选到远端推送都由只读 Controller 比较“本 Atom 新能力”和“仍被用户使用的现有显式入口”；必要的旧接口只读兼容和资料保护不能成为默认查找苍歧的借口。

### 01.1 通用应用冷启动的两层要求（补 R1 缺口）

- `git clone` 的仓库不包含 Git 忽略的 `runtime/reference/`、patched NK/CritiCS 构建、Python 虚拟环境；不可把旧工作区中存在这些文件当成干净 clone 具备相同能力。通用引擎应通过统一 tool-cache resolver 读取这些依赖；旧路径仅允许版本化受限兼容，不再成为新安装必备路径。不同 Python 环境/Node 模块不移动正在执行的进程，优先按 frozen lock 和 patch 重新构建并核验。
- 实现确定性 `bootstrap/doctor --app-only`：逐项核对固定 CNW 原件、Git submodule pin、本地 patch/依赖锁、Python/Node 环境；来源原件可从**可信 pinned checkout 或经 SHA 校验的可离线包**安装。缺少外部安装材料时报告 `RUNTIME_MISSING` / `BOOTSTRAP_SOURCE_MISSING`，不伪装成功，也不伪称此时可以离线安装依赖。
- 区分 `ENGINE_SOURCE_READY`、`CORE_RUNTIME_READY`、`PROJECT_READY`、`OPTIONAL_NK_{ENABLED/DISABLED/UNAVAILABLE}`、`OPTIONAL_CRITICS_{ENABLED/DISABLED/UNAVAILABLE}`、`LIVE_PROVIDER_READY`。项目资料不存在不影响核心源码/依赖检查；**未启用**的辅助组件缺席不得把 CNW 核心标为不可运行；**启用但缺席**应在启用者的执行前报缺。
- 完整离线 clone 验收使用**明确声明的预装依赖/本地安装包前提**；同时必须证明仅 clone + 已存在的 Python 测试依赖可跑的纯 Python 测试，不允许把联网完成的安装谎称纯离线。上游参考文件的 Git blob SHA 与本地字节 SHA 分开记录。
- 对当前 TS 和旧 J19 的运行版本，按 commit/构建身份留精确版本快照；新架构不能读取旧项目目录里的参考文件作为新项目 bootstrap 依赖。
- 建立**第三方与模板版权/BOM 清单**：固定 CNW `templates` 结构和许可署名；核验 NK、CritiCS 的实际许可证/patch 归属及打包分发条件；作者 `example_project` 的私人创作内容不作为新应用的默认样本、模板或离线 fixture。代码能 clone 并不等于所有上游小说素材可以自由再发布。

**Atom-01 独立验收（只验本阶段能成立的事实）**：架构与路径方案完整，建好通用路径/项目实例注册器的最小离线单测，输入 `DataHome` 和新 project ID 能解析/登记为不同实例；验证 setup 指针跨进程/重启保持、缺失或错误时安全拒绝；复制已有 `project_identity.json` 造成双活实例必须拒绝，`relocate`/`fork` 语义明确；不能把现有 `studio.ps1` 的旧默认路径误签为已经消失——旧 CLI 真正切换与不回退的行为由 Atom-04/09 测。此处控制只进入新 resolver 的请求，不要求尚未改造的历史 CLI 全绿。

---

## 4. ATOM-02 — 全局配置清洗与旧版本身份保全

### 02.1 清理默认配置

将 `config/production.example.json`、`config/cnw_production_policy.json` 拆成等价的**通用 app policy + Provider policy + project policy**；具体命名不限，但需明确职责：

| 层 | 允许内容 | 禁止内容 |
|---|---|---|
| 应用级 | CNW 原方法 pin、阶段/验证器结构、路径规则、并发/回执安全规则 | `cangqi`、J19、人物/剧情、每篇固定目标字数、某份私有源 SHA |
| Provider 级 | DeepSeek Flash 当前适配与限制、Key 环境变量名称、价格来源、reserve/send/settle 协议 | 把某个旧场景作为 Provider 的默认运行对象 |
| 项目级 | `project_id`、语言、篇幅指标、Arc/角色/世界/声线/禁句、第五 Lens、source registry、可选 JET/NK/CritiCS | 借别的项目原稿或旧验收自动补空白 |
| 工作合同级 | 工作单元、来源冻结、Anchor、篇幅目标、必需情节、审查方式及其哈希 | 隐式继承旧 J19 contract 或旧 Controller 凭据 |

默认 Provider **可以继续使用已验证的 DeepSeek Flash**；本任务并不强制改造多供应商抽象，也不改模型行为来假装完成通用化。若允许项目级 Provider override，必须显式验证受支持的适配器，而非接受任意未实现配置。

新项目不得默认声称其角色、语言、JET OS、故事专属 Lens、禁句等已经配置完成。**新安装的实时调用默认关闭**，必须由显式项目/运行授权解锁；历史已授权 `null` 金额上限作为历史配置保留，不自动传播为所有新项目的无限额度授权。`--mode live` 不是在无来源/无审查/缺 Key 时强行发送请求的理由。项目模板可以存在字段，但未填写时 `PRE_FLIGHT_MISSING_PROJECT_INPUT`，不自动拿示例内容顶替。

### 02.1a 方法配置不得随项目拆分而被削弱

- `workflow.template.yml` 的 M01/M07/M08/M13：逐话阶段序列、五 Lens 身份、`verifier_count=3/refute_default=true/threshold=2`、五话 Sprint 及其阈值视为固定**作者方法合同**，项目 policy/Provider 覆盖层不可重写或使用任意更宽默认值；单个项目可以填写第五 Lens 的**实际审稿职责**，不能删除第五 Lens。
- Prompt、角色 read 列表、两层 Lint 项目规则、Canon 批准记录与费用政策身份分开冻结。仓库旧固定 J19 Prompt 可以按其历史版本只读核验，新通用实例使用自己的合法数据而不是复用旧故事的“好用示范”。
- 分离 policy 前后形成方法字段的实际 key/path/值对照；涉及职责语义的配置变化由 Controller 依据 M 项审查。新项目缺真实项目级 Lens/Canon/Style 只能返回具体缺项，不拿示例内容偷填。

### 02.2 冻结旧合同使用过的配置

**不能漏掉的有效配置身份**：旧 run 同时持有 `contract_sha256`、`provider_config_sha256`、`cost_guard_runner_sha256`，而 `stage_identity` 又包含 Builder/Transport/Workflow/模型身份。建立逐字段兼容矩阵，给出“历史按旧解释验证”与“未来在新代码运行的版本化恢复”两条路径；不能仅实现 `resolve_policy_by_sha()` 就宣布所有身份兼容。对于 TS 尚未通过 Plot 的 run，允许在**以后正式创作、用户授权之后**按经审查的迁移 sidecar 恢复并写新阶段身份；本次整改不得改写它。已完成的 J19 旧 stage 如果代码 SHA 不匹配，应走冻结历史读档验证，禁止重新运行并称等价。

重要：旧合同包含 `policy_sha256`、source manifest 与 workflow 身份。修改全局政策会让旧历史运行不可校验。

依次执行：

1. 归档迁移前政策原字节及 SHA。建立按**内容 SHA**读取的只读政策/Provider/Prompt/工作流/工具身份快照索引。不要仅按“当前最新版本”覆盖旧证据。
2. 对已存在 run，保留其 `artifacts/contract.json`、原 `policy_sha256`、原 Prompt/Workflow/Provider 配置身份和真实收据，不得重算成新 SHA。**旧来源 manifest、source-index 和被真实旧合同引用的状态文件若会被后续导入覆盖，须在操作之前保留完整原字节快照；旧文件已经不存在时 `LEGACY_SOURCE_SNAPSHOT_MISSING`，不得拿现行索引回算旧 SHA。**
3. 新 run 固定新版本配置快照和对应哈希；旧 J19 run 读取**原先冻结的兼容版本**做只读核验；**v5 尚未完成的合同及 TS 原 run 不只需要只读，它们以后还需继续创作**。先建立合同政策解析器 `resolve_policy_by_sha`，确认新执行器可对旧冻结政策做真实验证，并能以未来选定的新配置进行受控复核/恢复，但不得悄悄改写 v5 合同。
4. 旧格式不可恢复到新引擎时报告 `LEGACY_MIGRATION_REQUIRED`，保留旧状态，不覆盖/伪迁移。
5. 禁止通过修改旧 `contract_sha256`、旧 manifest、旧收据或替换 SHA 验证逻辑使其“兼容”。
6. 新格式改动先落到影子配置，保证尚未适配的实际程序仍可读取原有效配置。定义准确的迁移/激活顺序和回滚选择器；不能在此 Atom 就把原 `production.example.json` 换成不被当前 `p2_cost_guard` 识别的新 schema。

**Atom-02 独立验收**：新/旧政策 schema 和按 SHA 的版本化解析器能处理两个不同的项目级配置，旧合同 hash 不变；冻结配置/旧 manifest 快照都可按原始内容 SHA 回读；影子配置可读且尚未替换所有旧消费者时仍不切换活动文件。**项目配置变更引发的真实阶段失效与两个 run 不互改的运行效果推迟至 Atom-07/09**，不得在本阶段拿假造 stage 状态自签“已验证”。

---

## 5. ATOM-03 — 来源识别和合同生成彻底去苍歧化

修改并核验：`cnw_runner.py`、`cnw_roles.py`、`cnw_project.py`、`cnw_contract.py`、`cnw_generate.py` 和所有直接消费 source 的入口。

### 03.1 必须消灭的隐式行为

- `ROOT/inputs/private/release/<旧 SHA>/Cangqi_Jun_Release_2_3` 作为兜底来源。
- `ROOT/workspace/cangqi` 作为未传 `project_root` 的默认值。
- 当 `source.identity_type` 不认识时，直接按苍歧 Release 解析。
- 隐式从历史 `EP001`、J19 或之前成功的 contract 补充新项目字段。

### 03.2 通用来源注册与工作意图：严禁混成同一个字段

**来源身份（source origin）** 指向证据从哪里来；**工作意图（work intent）** 指此次要对来源做什么。两者正交，不能把“有原稿”直接等同于“插入两个锚点之间”。将旧 v1 来源识别与新 v2 工作意图区别处理。最小来源有：

```text
IMPORTED_PROJECT / PROJECT_SNAPSHOT:
  按 project_instance_id + immutable source_revision_id + source_id + content_sha256
  查本项目 _INBOX/originals 的原始只读副本与不可变 manifest/index revision
  旧 source.identity_type="imported_project" 继续按 v1 冻结规则兼容

ORIGINAL_PROJECT:
  没有待改编原稿；由本项目冻结的 Canon/Arc/Style、episode/前章身份承载
  不得伪造 source_file、source_manifest 或双边锚

EXTERNAL_PINNED_SOURCE（只有明确注册时）：
  用户显式授权的只读源根及其 SHA、原始快照/manifest；日常运行读已封存副本
  不得从 project_id、角色名或 work_id 猜原稿路径

LEGACY_SOURCE（仅旧项目）：
  通过受限只读映射和冻结历史字节；不得在新项目默认查找
```

新 `work_intent` 至少严格区分：

| 工作意图 | 需要什么 | 不得怎么做 | 交付范围 |
|---|---|---|---|
| `INSERT_BETWEEN` | 显式 source revision、真实且有次序的 before/after 锚 | 不存在时硬补两行、借另一份稿的行号 | 在两个固定片段之间创作新场景 |
| `ADAPT_SOURCE` | 显式 source revision + 非空 source span（MD/TXT 行区间，或 JSON Pointer/结构化字段路径），选段内容 SHA | 要求不存在的第二行、覆盖源原字节、混入别的 source_id | 把选定原稿片段/完整章节改编为新章节或 AVG 文字 |
| `ORIGINAL_EPISODE` | 经核验的本项目 Canon/Arc/Style/Story 指定；后续章需明确前章来源 | 制造原稿文件或借旧项目 Canon | 原创第一章及后续章 |

JSON 原稿可以是**一行 minified JSON**：`import_source` 目前已经记录 `json_pointer`，新合同解析必须实际使用结构地址、按原始 JSON 字节 SHA 冻结选中节点或稳定结构值；不为凑双行而改写 raw JSON。对 JSON Pointer 缺失/漂移、同名 JSON 节点歧义和空范围需 fail-closed。原始文件和可读展开快照必须分别存哈希。

旧 J19/v5 **原 v1 合同原样保留**；仅对已确实包含 before/after 且可验证的旧合同，按 legacy 插写语义解释，不能把未知旧格式默认成 `INSERT_BETWEEN`。新合同明确 `work_intent`，未经支持的 source type/intent 拒绝 `SOURCE_TYPE_UNSUPPORTED` / `WORK_INTENT_UNSUPPORTED`。

### 03.3 路径本身进入身份：必须兼容旧 Run（P0）

当前 `cnw_runner.literary_source_freeze` 以 `script.relative_to(ROOT)` 构造冻结记录键；`validate_literary_source_freeze` 和 `source:anchor_excerpt` 回读也用仓库 ROOT。迁出后不只是找不到旧文件，在新冻结时还会触发 `ValueError`。

逐条落实：

1. 对**新**合同/run 使用版本化 `literary_source_freeze_v2`，来源和 manifest 的键采用项目内相对路径 + 明确登记的源根身份；项目移动且字节未变时身份不变。严禁在身份键中保存安装绝对路径作为权威源 ID。
2. 对**现存** J19 与 TS run，不修改 `run_state.json`、旧 SHA、旧冻结键。增加 `legacy_source_path_map` **独立受限迁移记录**（旧根路径类别→新根；真实源类型；逐文件 hashes；生成时的旧代码/policy 身份）；每一类路径分别登记：① v5 三个项目内 `_INBOX/originals` 的复制源；②旧 J19 的 `inputs/private/release/<sha>/...` 和相关源根；③原生 CritiCS `ROOT/runs`、NK 证据；④旧全局账本和依赖快照；⑤仓库内曾被引用的 project/workspace。不能把它们统称一条“project_root 映射”。仅在明确指定目标项目和迁移 manifest 验证成功时生效。
3. 旧格式键只在历史路径兼容解析器中读取：先校验其原始合同/source/manifest SHA，再从映射后的文件重新算原有哈希；不得按旧键文字直接定位任意系统路径，也不得将 `source:anchor_excerpt` 当成免检通道。
4. `stage_identity` 含函数代码哈希：`LEGACY_READ_ONLY_VERIFIED` 由冻结旧代码快照与原始证据证明；`V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK` 单独在迁移后验证 TS 的 `source freeze`、合同/政策和 `stage_identity` 可进入 Plot 的确定性前置检查，不执行模型。旧 J19 不要求在新代码中无损继续其每个历史阶段。 **旧核验程序不允许写原始 run：当前 `verify_evidence → support_input_snapshot` 可能补写 `run_state`；须用纯只读验证器或先复制到隔离临时目录再核验，并断言源 run 原始字节/哈希不变。**
5. `cnw_project.import_source` 的 `source_manifest.sources[].original_path` 是导入时绝对路径，保留为**历史来源描述**，迁移时不可改旧 manifest 内容；合法运行只依项目内原始副本 `stored_path` 和 SHA。断开的 `original_path` 不能被当作当前可读取路径或静默刷新。
6. `build_source_bound_contract` 当前把 `unit.language` 固定写成 `zh-CN`；改为由已验证的项目语言设置/合同入参决定，语言未知就报缺。允许选择 Unicode 可见字符作为跨语言统一计数标准，但须明确其计数语义，不能把英语“字数”误称为按单词统计。定义 `tested_locales` 与模型/工作流实际支持的长度范围，未测试语言或长度拒绝正式兼容宣称，不伪报支持所有语言。

### 03.3a 多来源选择与清单修订：通用化新 P0

当前 `import_source()` 支持连续导入，而新合同构造器始终取 `sources[0]`。必须：

1. 新项目 `create-work-contract` **显式指定 `source_id` 及 `source_revision_id`**；若清单中有多个候选来源而参数缺失，返回 `SOURCE_SELECTION_AMBIGUOUS`，绝不可拿第一份；若 source_id 不存在、和源 SHA 不一致，拒绝创建。v1 已冻结单来源合同按既有源字节兼容，不自动升级。
2. 一次追加导入生成**不可变 source-manifest/index revision**（内容 SHA 与版本 ID）；更新可变的“当前来源列表”只是一个索引，不得覆盖旧合同需要的那一份原始 manifest。对原有 v1 所引用的具体 manifest SHA，使用历史原字节快照；没有快照绝不可从当前列表伪造同一 SHA。
3. `contract.source` 冻结所选来源的 byte sha、格式、选择范围及其具体 manifest revision；`runner` 的 Source Freeze / 输入路由 / Review / Export / Sprint 必须引用同一所选源，而不是读取首个源或最新列表。未被此工作合同引用的来源追加，不得伪造其 raw 已改变；如果当前 Canon/Arc 等被实际修改，仍按内容依赖正常失效，不能把来源无关变化等同于整份故事状态无关。
4. 所有历史修订可以追溯原始副本；新文档可被批准纳入 Canon，但导入器不能直接把 `INFERRED/TODO_CONFIRM` 提升为 Canon。若发现同源新旧版本冲突，保留两者和人工决策边界。

**本 Atom 必做四组零网络负例**：导入 A 再 B，选 B 的合同只消费 B；反向导入顺序仍选 B；单行 JSON 通过 Pointer 范围选源并建立改编合同；导入 C 后前一个 B 合同仍可按其**原生快照**只读验证（若 Canon 实际改变则新执行正确失效）。缺少选源、篡改旧快照、Pointer 不存在全部拒绝。每组包含真正的 read/consumer 输入 SHA，而不仅是合同字段存在。

### 03.4 无原始稿件的原创项目（必须支持；不是伪造 source）

**方法归属声明**：这是 StoryStudio 的通用应用能力扩展，不是原作者已公开证明“没有既有章节也可全自动量产高质量小说”。官方 `docs/GETTING_STARTED.md` 明确建议先人工创作前数章，形成 Canon/Style 后再自动化。故 R3 要验证扩展功能的安全与完整消费链，不将其冒称原作者私有自动化系统或文学效果验收。

当前 `cnw_contract.check_required_fields()` 无条件要求 `story.before_anchor` / `after_anchor`，`cnw_project.build_source_bound_contract()` 先读取 `source_manifest` 并验证原稿行号。它只能服务已有稿件插写，**不是作者通用小说创作工具的充分合同**。

新增一个显式版本化、源身份仍严谨的**原创项目类型**（名称可为 `ORIGINAL_AUTHORING`/`NATIVE_PROJECT`，最终选择一个稳定名称）：

- 允许空项目初始化后，先构造项目自己的 `90_canon`、`04_chapter_design`、`92_style_engine`、工作目标和声明过的角色范围；没有 `_INBOX` 原稿时不凭空生成 `source_file`、虚构 `before_line/after_line`。
- 第一章标明 `story.first_episode=true`、预设情境和计划上下文；第二章及后续章以**同一项目的经授权已发表前章 / 显式选中的前章版本**及当前 Canon、Arc 为来源，受哈希和来源范围保护。一个模拟 EP001 不等于可用生产票发布：离线测试可用单独标记的 `SIMULATED_CARRY_FORWARD`（仅测试目录中有效）证明消费者，绝不能调用真实 `promote` 把模拟票变成正式发表。
- 验证器按 `source type + work intent` 联合分支：`INSERT_BETWEEN` 强制真实 source + manifest + 有序双锚；`ADAPT_SOURCE` 强制源范围/Pointer 和 SHA，**不必有不存在的双锚**；`ORIGINAL_EPISODE` 第一章强制 Canon/Arc/Style 与既定故事状态，后续章还验证前章引用。**不允许三种意图用空值、伪造引用或默认首源相互逃避检查**。
- `cnw_runner.execute_plot/read_production_preparation/literary_source_freeze` 仅在 `INSERT_BETWEEN` 时读取双边锚；`ADAPT_SOURCE` 读取真实选段/Pointer 及必要的现有上下文；其 `export` 应输出“选定原文 + 改编后的新内容 + 真实来源身份”或只输出独立改编章，**不可硬拼不存在的插场前后锚，也绝不可覆盖 `_INBOX` 原始字节**；原创类型消费经批准的 Canon/Arc 和相应项目资料。`read_production_preparation` 当前另需 `94_runtime/current_state.md`、`07_draft/manuscript_index.md`、`arc_*_episode_details.md`、voice 文件；新项目初始化要生成**没有虚构事实**的合法结构占位，并由预检区分“结构文件存在”与“故事权威内容已填写”。`cnw_export` 遇无来源锚点的原创第一章时生成单章阅读版，不应 KeyError 或拼接虚构前后文。
- 兼容规则：旧 `imported_project` 合同/TS run 字节不变；引入新 source type/schema_version 只影响新创建的原创合同，不能让旧工作单元被自动升级。官方 CNW 的章节创作不要求总有“待插入的原始稿件”，不能为了支持第一章而伪造一份“原始稿”。

**本 Atom 的验收**：源稿插写严格要求双锚；单行 JSON 和完整原稿改编严格要求选段/Pointer SHA、**无需伪造双锚**；另一个完全无原始稿件、Canon/Arc 已填写的合法原创第一章合同能建立、通过离线预检，进入非网络 Plot 请求构造阶段；并把“原创模式必须走到完整11阶段+可读导出”列入 Atom-09 的终验，而不是在 Plot 就宣布功能完成。空 Canon 不放行，原创类型不反向降低插场合同的来源门。

### 03.4a 创作意图扩展不得导致四角色绕读（R5 强制）

INSERT、ADAPT、ORIGINAL 新合同都必须经同一个适用的四角色读取边界 M02–M05；新增 `source_id/source_revision/span/json_pointer/previous_episode` 进入**来源解析、Plot 或合规准备资料**，再经 Cards/Brief 传到 Prose，不允许以“ADAPT 要参考全文”“ORIGINAL 没有双锚”为理由，把整个 source、隐秘 Canon 或 `forbidden_patterns` 直接塞进 Prose system/user messages。若某项目合法确需具体引文，先由允许读取该来源的岗位选入 Brief 并保留 source hash；Prose 仍仅直接读 Brief+相关声线。Atom-03 交付两个正例和一个非法来源 canary 负例的**真实消息构造**，完整模型链在 Atom-09 再验。保留分 `CONFIRMED/INFERRED/TODO_CONFIRM` 与人工事实晋升界限。

### 03.5 真实源文件校验

每次预检检查：

1. 源清单与原始文件 hash 匹配。
2. before/after anchor 行号和字节 SHA 匹配。
3. source root 位于该项目授权根或显式信任的只读目录。
4. 源类型及状态与工作合同一致。
5. 同时存在两版冲突事实时保留冲突供作者决定。
6. `CONFIRMED / INFERRED / TODO_CONFIRM` 不相互冒充。

**验收**：在只有全新虚构源稿的测试机上可合法建立 INSERT/ADAPT 两种有源工作合同；在没有原稿的新项目中合法建立原创合同；输入完全不包含苍歧项目时，没有代码尝试访问苍歧目录；多来源、追加导入、单行 JSON 三个输入案例必须满足本 Atom 的真实来源消费负例。

---

## 6. ATOM-04 — CLI 与旧场景专用脚本脱钩

### 04.1 重构 `tools/studio.ps1`

保留现有成熟入口的外壳，按如下行为改造，不必为“纯净”重写成全新 CLI：

```text
studio doctor [--app-only]             # 引擎/依赖/参考 pin 与工作区可用性
studio setup --data-home PATH           # 首次显式选择写入位置、验证空间并保存用户配置；零模型调用
studio project-init --project-id ID --data-home PATH
studio project-import --project-id ID --input PATH --data-home PATH
studio project-contract --project-root PATH --input PATH
studio produce --project-root PATH --contract PATH --run-id ID --mode offline|live
studio step --project-root PATH --run-id ID --stage CNW_STAGE
studio show-run/resume/verify-history/verify-live/review/promote/export
studio canon-audit/handoff/arc-review/standard-operation/support-workflow/sprint
```

CLI 表面语法按现有 PowerShell `-Param` 风格保留即可；上表仅表达使用合同。**不能因为本文件使用 `--` 就直接更换所有 PowerShell 参数。**

具体修复：

- 没有 `-ProjectRoot` 和项目选择环境变量时，`doctor` 检查引擎仍能返回 ENGINE_READY，项目命令明确拒绝。
- 去掉 `$SourceRoot` 的固定苍歧 Release 构造。
- 删除活动 `scene`/`legacy-scene` 对 EP001 的默认派发；历史需要的脚本迁至外部归档，通过用户显式旧项目入口调用。
- 把 `Export-ReadingPackage` 中的 J19 文本拼接、书案评论、预置旧位置等活动逻辑从当前 CLI 移出；当前 `export` 调用真实 `cnw_export`，并绑定当前项目/合同/运行。
- `import-source` 不再用 `JUN-SINGLE-02.3` 和旧固定 SHA 判定身份；改成通用 source manifest 校验。增加 `source list/select/version`（可合并进合同创建命令），允许用户在多个已导入来源中**显式**选择输入和改编范围。通用导入和创作入口分别校验来源 revision，不能让 `import-source` 完成后自动把第一份稿当成选中稿。
- `verify live` 不得靠 `reviews/P2_ACCEPTANCE_LOG.md` 是否出现两个关键词就宣称可用；要验证指定 run 的真实 source/response/receipt/status。`doctor` 的“配置/依赖可用”不能称为 Live 已实跑。
- 旧 `prepare-live`、`live-call`、`accept-role`、`w10-*` 与未提交 executor 要逐函数检查消费者：属于新通用能力则纳入通用契约；属于仅旧 W10 诊断则移外部归档。不能因为文件名旧就把当前 CNW 真正调用的实现删掉。
- 创建公共 CLI 命令表：`COMMAND | REFERENCED_IMPL | IMPLEMENTATION_TRACKED? | PURE_GENERIC? | STATUS(SUPPORTED/LEGACY_ONLY/REMOVED) | CLEAN_CLONE_SMOKE_TEST`。所有标 SUPPORTED 的命令必须在干净 clone 中能定位实现并通过无网络入口测试。不得把未提交 W10 当成新安装时天然存在的依赖。

### 04.1a 活动 CLI 切换顺序与方法入口保护

受治理允许的 `main` 分 Atom 提交并不授权把尚未打通的新 CLI 立即设为生产唯一入口。Atom-04 只将新通用参数化入口放在受控影子路由，验证命令确实消费项目上下文；对既有 v5/W10 的**显式**入口以带 pin 的兼容层维持可用性（不再给新项目使用苍歧默认路径），直到 Atom-09 真正断网全链和迁移资格达标。移除旧脚本前 Controller 必须按调用图判定是否仍服务 M01–M16、历史数据和 Sprint/Workflow 03；凡仍有活动消费者或唯一可用能力，先抽出通用薄实现并证实同语义，再撤旧派发。每次本地候选接受、推送前做旧显式入口不退化的有限 smoke；不能删支持命令后在 Atom-09 才发现原方法操作遗失。

**输入包生产入口依赖（见 0.3a）**：项目所有者以包及明确选择的项目上下文启动；CLI/应用内部创建并校验合同、来源选择、Run 与身份，不能要求用户提供这些内部标识或逐阶段执行。包输入格式与项目正式 Contract 不同，应由适配器完整映射并保留原要求/材料，不得要求用户改写为内部格式。

### 04.2 清理历史一次性脚本

**真实活动路由完整性**：对 PowerShell 调用、Python 模块引用、子进程调用、环境变量、第三方 patched build 路径建立有向消费图；不能只 grep 名称。所有公开 CLI 即便注册为 `SUPPORTED`，在缺当前项目时必须明确报 `PROJECT_REQUIRED`，而不是用旧 J19 私有路径补默认。


将 `tools/p2_06_draft_run.py`、`p2_06_revision_run.py`、P2 probes 及 `tools/p2_06_nk_live_probe.ps1` 等按 Atom-00 活跃消费者表逐项处理：

```text
for old_script in inventoried_legacy_scripts:
  if active_generic_consumer_exists(old_script):
      extract_necessary_generic_function_to_supported_adapter()
      update_consumer_and_tests()
      verify_identity_and_raw_receipt_compatibility()
  archive_original_bytes_outside_active_repository()
  remove_from_current_active_dispatch()
```

`tools/p2_06_critics_run.py` **目前确实被 CNW 生产链调用**，不可直接删除；先抽成正式通用 CritiCS live adapter（或证明同等通用实现已经存在），保持 reserve/send/settle 与 native 方法语义、请求缓存身份以及历史调用可追溯，再将旧文件归档。`p2_cost_guard.py`/`p2_cost_pricing_*.json` 是另一类**仍被活动生产使用的 P2 命名实现和版本化价格资料**：新通用入口须只依通用 `cost_guard`/policy resolver，旧名字可以做按旧身份调用的受限兼容适配，但**不能只删旧文件名、也不能把 P2 首场专用 campaign scope 当新项目默认范围**。前后真实账本/收据校验按冻结格式进行。

**Atom-04 独立验收**：所有**当前宣称 SUPPORTED** 的 CLI 路由均已注册到 Git 跟踪的实际实现，在已准备的源码/基础运行环境中能准确解析项目身份，未配项目时明确拒绝；旧 J19 特殊导出已移出活动派发，必要通用桥仍能被当前实现定位。`doctor` 清楚区分核心与可选组件，不能使用旧项目来报就绪。**每条命令完整语义产物、实际11阶段与 Arc/Sprint 输出的终验留到 Atom-09**，不得用当前路由“找到代码”冒充功能全过。

---

## 7. ATOM-05 — 应用运行数据、费用账本与项目隔离

### 05.0 数据迁移前的子智能体额外签收门

Atom-05 Writer 必须提供复制前后目录/身份/锁/费用账本原字节对账、事务回滚计划及迁移 dry-run 原始结果，Controller **只读**核查后输出 `CUTOVER_READ_ONLY_ACCEPT` 才能由 Writer 切换活动数据指针；此签收不意味着新引擎 11 阶段已通过。未取得真实批准、仍有活跃 Writer/进程/Unknown 费用或基础 source freeze 对不上，停在旧唯一活动根并报告对应 `*_BLOCKED`，不得靠“单测成功”压过去。Run 候选隔离与项目级 CAS 是工程实现变化，不授权改变作者 Plot→Cards→Brief 的同 run 实际消费，也不授权自动 Canon/正式正文晋升。

### 05.1 数据根迁移

`tools/cnw_generate.py`、`cnw_export.py`、`cnw_critics_adapter.py`、`critics_bridge.py`、`cnw_import_workflow.py`、`cnw_maintenance.py`、`cnw_sprint.py`、`cnw_sprint_live.py` 等必须通过统一解析器获得项目根/运行根/导出根。

处理步骤：

0. **先停止所有写入并取得迁移锁**，冻结工作树版本、TS/J19/v5 的源与 run 文件、原全局账本 SHA，列出本机可能正在执行的后台 NK/CritiCS/Provider 会话与锁。无法确认静止状态就不切换目录。
1. 保留原来的 `workspace/`、`runtime/private/`、`runs/`、`deliverables/` 原字节；冻结 hash。
2. 将新项目默认**用户数据根**设置为仓库外的 `<APP_DATA_HOME>`；在兼容校验通过后，把 v5 TS/DL/RH 三个未来仍要继续的项目（连同 TS 既有 run）无损迁移到 `<APP_DATA_HOME>/projects/`，把旧 J19/EP001 私有项目及专属导出移入**仓库外历史归档**。迁移采用可重入日志 `PREPARED → COPIED → HASH_VERIFIED → TARGET_READ_ONLY_VERIFIED → CUTOVER → POST_CUTOVER_VERIFIED → OLD_PATH_RETIRED`；失败时保持唯一活动入口并可回滚。**不能**只看 `contract.json` 哈希就切换；要以实际 TS 旧 `literary_source_hashes` 和旧 policy 与运行记录验证兼容映射，确认原 TS `run_id` 在新路径可被定位，**先通过基础合同/source/policy/冻结键核验和非网络 stage identity 计算**；此时尚未到 Atom-07，不要求旧 J19 专用的 Controller 门立即放行。若基础身份不成立 `V5_CUTOVER_BLOCKED`，不得移走原件；Atom-07 再解除真实新合同的审查门。
3. 新项目按 `project_instance_id + project_id + run_id + contract_sha256 + source_identity` 组织运行身份与索引（有原稿的 source identity 包含 manifest SHA，原创项目用 Canon/Arc/Style 冻结身份）；旧 run 只读兼容索引不得改原格式。
4. 旧 J19 项目只有显式指定仓库外 legacy 根才能读取；v5 三项目只有显式选中各自项目根才能继续。旧 J19 源代码以固定历史快照只读验证，不能要求它的每项旧 raw 在新版本运行器中可重新生成。不得使用名字相同的 `run_id` 跨项目复用正文/收据。
5. 错误路径与跨项目穿透在**付费调用前**拒绝。`project_id`、`run_id`、工作单元 ID、导出路径都必须对组件路径分隔符和越界片段作校验；`cnw_export` 现以合同 `project_id` 拼 `ROOT/deliverables`，不得让非法项目 ID 逃逸目标输出根。
6. 输出 HTML/TXT/Markdown 必须写入本项目 private export 根，不能覆盖别的项目同名文件。
7. **工具缓存单独处理**：`runtime/reference` 的固定 CNW 资料、`runtime/patched` 的 NK/CritiCS 构建及 `runtime/envs` 的虚拟环境既非旧 J19，也非新项目 Canon。逐个活跃消费者改用统一的版本化 tool-cache resolver；以锁定 Git pin、patch、依赖版本重建或校验，不能把仍在运行的虚拟环境跨盘复制后就视为有效。旧构建在全部消费者转接验证前保留只读副本，冷 clone 不得依赖这些未跟踪的本机路径。

### 05.1a 运行产物必须具备事务与版本所有权（R3 新 P0）

当前 `cnw_runner._planning_stage()` 在执行期间写 `project/06_plot/<work_id>_plot.md` 或 Cards，`execute_writing_brief()` 也先写项目共有文件再记录当前 run stage；`produce()` 还会直接将旧同 work-id、不同合同的 run 标记 `INVALIDATED`。以下场景不是可以忽略的“旧样本瑕疵”：

1. **不变量**：`run_id` 对应的 Provider raw、各阶段候选、旧 `run_state.json` 在后来创建新 run 时保持可按原 hash 回读；新 run 的出现不等于旧历史 run 必须物理失效。旧状态可以在**其自身的合法原 run 恢复/执行**时追加更新，但绝不能因创建另一个 run 而变化。
2. **生成与晋升分离**：新的 Plot/Cards/Brief/Prose/Review 先在 `runs/<run_id>/artifacts/` 或受限 run-scoped overlay 落盘并登记 hash；后续角色优先消费**同一 run**已登记的上游候选，而不是随便读取项目目录中同名文件。可将只读 overlay 呈现为作者需要的相对路径，但不可默认覆盖公共正本。
3. **发布操作**：被接受的候选经 Controller/项目指定的晋升门，以 `expected_current_sha`/版本化 CAS 原子写入项目权威文件；如果冲突就 `PUBLISH_CONFLICT`，保留两份稿件供人处理。旧项目若历史阶段原已直接写公开目录，历史字节原样保留，通过旧代码身份 + 外部迁移报告说明，不能迁移时冒称当时已经实现事务。
4. **取消旧 run 的直接篡改**：`produce()` 创建新 run 不得改写已存在 run 的 `status/updated_at` 或被接受产物；需要“被新稿取代”时写独立追加的 `supersession/index`，读取时按最新版本/显式版本解析，不抹掉原始运行结论。

   必须在设计中落实而不是只画目录，最小读取/发布伪代码：

   ```python
   def author_input(run, role, required_path):
       if required_path in ROLE_STAGE_DEPENDENCIES[role]:
           producer = ROLE_STAGE_DEPENDENCIES[role][required_path]
           return verify_and_read_immutable(run.stage_artifact(producer))
       return verify_and_read_project_frozen_file(run.project_snapshot, required_path)

   def write_candidate(run, stage, text):
       # 先写 run-scoped tmp -> 校验 -> 原子替换候选文件 -> 持久化状态；
       # 不更改同 work_id 的已发表项目正本。
       artifact = persist_atomic_stage_artifact(run, stage, text)
       persist_stage_receipt_with_hash(run, stage, artifact.sha256)

   def publish(run, expected_project_version):
       require_real_candidate_review(run)
       version_dir = build_immutable_versioned_output(run)
       verify_version_dir_against_run_hashes(version_dir, run)
       # 通过版本指针比较并交换；若需呈现多个 CNW 常规路径，
       # 一律由 version_dir 派生，不宣称多个文件写入天然原子。
       cas_update_current_version_pointer(run.project, expected_project_version, version_dir)
   ```

   `ROLE_STAGE_DEPENDENCIES` 必须从固定作者角色读取映射导出且覆盖审稿者需要的 Plot/Cards/Brief/Prose 同 run 产物；不能把所有路径都改成私有 stage 输入，Canon/Style 仍按冻结的 project 文件读取。**单文件 `os.replace` 原子性不等于跨多个文件的原子事务**：若实现为多文件发布，则必须有 journaling/恢复后权威指针一致性证明；不得把“写到一半未崩溃”当事务正确。
5. **失败原子性**：在“项目候选写出之后、run stage 持久化之前”与“晋升版本检查之后、正式写入之前”注入崩溃；重启后既无旧稿损失，也无假 STAGE_MATERIALIZED，继续恢复时不重复使用未验证的半成品。
6. **兼容现有 v5 TS**：TS Plot 尚未有成功 Provider 或已完成的 Plot 候选；迁移后继续时应进入新 run-scoped 落盘策略，不重写 TS 旧合同/失败历史。历史 J19 只读验收只用旧身份，不把新候选事务追溯写成旧行为。

**Atom-05 的独立完成门（避免 Atom 依赖倒置）**：要求实现候选/正本所有权和公共项目级写入仲裁的最小闭环，并通过**确定性、本地、无 Provider 的单元/组件测试**：同项目同 work-id 两 run 的 Plot/Cards 候选不相互覆盖；Cards 消费其**自己 run** 的 Plot；新 run 创建不改旧状态；模拟写入中断不改项目正本；CAS 冲突不发布。此时不要求调用尚待 Atom-06 修复的 NK/Brief，也不要求尚待 Atom-09 建设的完整11阶段模拟 harness。

**后置终验（Atom-09 必达）**：扩展到两 run 完整 Plot/Cards/Brief/Prose/Review 同 run 读取、两个项目同名 work-id 并发执行、导入/维护/Sprint/版本发布竞争、完整11阶段和崩溃恢复；任何一项不符均不得在 Atom-10 签总 ACCEPT。

### 05.1b 所有能修改项目权威文件的工作流必须共享一个写入所有权（R4 新 P0）

R3 的 `write_candidate/publish` 只覆盖 CNW 生产阶段，但当前 `cnw_import_workflow._apply()`、`cnw_maintenance._apply()`、`cnw_sprint_live` 也会写 Canon/来源状态、工作日志、阶段反馈和已发表章节。单个模块具备 journal，**不证明不同模块并发时具有共同事务**。

强制单一项目权威发布版本：

```python
with project_write_lock(project_instance_id):
    assert_registry_identity_and_authorized_root(project)
    assert_expected_authoritative_version(project, expected_version)
    assert_source_snapshots_and_targets_match_preimages(operation)
    prepare_immutable_transaction_journal(operation, outputs)
    publish_versioned_files_and_cas_current_pointer(operation)
    finalize_or_recover_journal_idempotently(operation)
```

- 新 Canon、Arc、source index、manuscript index、Lens feedback、导入日志、Handoff、Sprint carry-forward 和正式正文发布的**权威写入路径**共用上述项目级互斥/CAS；不要求所有临时工作文件持锁，但正式发布时必须在锁内重新验前态。
- 业务权限仍分开：Canon 事实晋升须项目作者决定；Controller 签工程或审稿不等于批准新 Canon。共享事务只是解决“谁先写、写什么版本”，不能让引擎擅自补全来源事实。
- 原始 `_INBOX/originals`、旧 run、Provider raw 和账单只追加/不可变。来源索引的新 revision 发布必须可回退到上一已接受版本，同时保留新不可变快照；两个并发 import/maintenance 不能只靠各自的临时 `.import-tmp` 或 `.tmp` 自称安全。
- Sprint/Arc publication 读取的前章/Canon 必须冻结明确项目版本；若并发维护修改了所依赖 Canon，则 **pause/RETURN_CONFLICT**，不得静默用一半新一半旧。反之无关资料只按声明依赖决定是否失效。
- 测试必须执行：同时导入与发表、同时 maintenance 与 Sprint、两个不同 run 同时 publish、断电/异常后恢复 journal。检查无丢更新、无混合权威版本、旧 project pointer 一致，允许正确的拒绝冲突。

**本 Atom 的当期门**：建立项目级仲裁和两种写操作的确定性竞态单测（例如 `import` 与 `publish`），确认合法提交或可恢复拒绝；剩余维护/Sprint 真实消费者完整并发的综合断网测试延至 Atom-09，但必须在 Atom-05 交付对应适配代码/接口，不得只留 TODO。

### 05.2 成本与 Provider 原始证据

费用账本不属于某一篇故事。保留历史 CNY10 上限、其后 `null` 无金额上限以及真实变更记录和实际已使用配置的字节快照，不重算历史费用，不把已计费请求写成免费。**一个账本只代表其配置的数据根/工作账户的本地执行器支出；若同一 API Key 在另一个 StoryStudio 安装/数据根或外部客户端使用，不能把本账本宣称为供应商账户全局费用总账。**

- 使用同一个明确的已配置全局账本与锁（不是每个项目另起一份复制账本）。**所有活跃消费者**包括 `p2_cost_guard`、Runner、CritiCS、NK、旧 P2 审计入口先同步转向同一账本/锁，再切换数据目录；迁移前副本只能只读，不允许出现两个可写账本。历史行不得因缺 project_id 而被修改。
- 每笔**新** Provider 记录绑定 `project_instance_id/project_id/run_id/stage/request_id/provider_request_id`；保留 `PENDING/SETTLED/UNKNOWN_NOT_ZERO` 的原意。同一 run ID 跨两个实例不得共享或误用账单记录；旧账单没有 `project_instance_id` 不得倒填成新事实。旧账本行原字节不变；历史格式允许用只读兼容解析，而不能补造 project_id。
- 全局 CritiCS native 运行名/目录、缓存、辅助日志与 Provider 槽位须以明确的 **project+run+hook/唯一随机 ID** 防碰撞，不能只靠重复的 `run_dir.name` 当作跨项目身份。检查 `tools/p2_06_critics_run.py`、`critics_bridge.py`、`cnw_critics_adapter.py` 的真实消费者及原生结果回读；原始 `run_name` 和 receipt 原样保存。
- 未能确认响应时不自动补0；不因为切换项目清空 Unknown。
- 新项目启动的 `doctor`、初始化、预检、离线测试，账本的真实已结算总额和历史行不变。
- 新项目的每个真实费用操作必须把已验证的实例绑定费用上下文显式传入既有 reserve/settle/accounting primitive；禁止临时改写模块全局账本/配置。保留共同 provider 并发总限额，不按项目复制额度或可写账本。
- 原始 request/raw、价格来源和政策哈希留存；密钥只在受限环境/KeyStore 存放，公共日志不包含敏感内容。

**验收**：两个项目隔离输出、相同 work/run ID 不覆盖、重复实例 ID 的双活 root 拒绝、错误交叉凭据必拒；同 work-id 新 run 不改旧 `run_state.json`；零 API 的迁移测试原始账本前后 SHA 相等；历史费用无重复或丢失。账本切换时保留 `PENDING/UNKNOWN_NOT_ZERO` 按原格式正确解析，不能为了通过迁移简单归零。

---

## 8. ATOM-06 — 官方 CNW 方法保真与项目配置解耦

**不能为了“通用”把作者公开工作流变成只剩阶段名的空引擎。**

保留 CNW 原顺序：

`plot → scene_cards → writing_brief → prose → lint_layer1 → lint_layer2 → multi_lens_review → adversarial_verify → completeness_critic → refine → re_review`

保留四角色作者读取边界、来源记录、固定 Prompt/模板、两层结构 Lint、五 Lens（含项目自定义 story_specific）、每个真实 Finding 三个反证、Completeness、Refine、受影响 Re-review。

项目层可配置（不得把“通用”理解为删掉必要的项目材料或缩减原方法）：

- `language` 和文字计数单位；无有效配置则预检报缺，不能静默采用旧君天离中文场景的规则。实际支持列表通过验证后冻结在 `SUPPORTED_LOCALE_MATRIX`；本轮至少有中文与英文离线请求证据，其余语言不得宣传已支持。目标字数与 Provider token 上限需有显式拒绝/续写策略，超出已验容量不能声称“任意长度”。
- `genre`, `character_bible`, `glossary`, `timeline`, `world_bible`, `style_guide`, `voice_samples` 的实际项目文件。
- 项目自己的 `forbidden_patterns.md`；结构沿用官方，禁止装入原作者故事或苍歧词表。
- 第五 Lens 的**项目特定审稿职责/规则**；不能无条件套官方示例小说的误认结构，也不能套苍歧个性化审稿。
- JET 可选，NK/CritiCS 辅助可配置；未选择时不得因不存在项目 JET 而让一个完全合法的 CNW 工作流失效。**运行器必须显式区分** `ENABLED / DISABLED / ENABLED_BUT_UNAVAILABLE`：未启用是合法选择，已启用但缺运行组件不能静默退化为通过；不把额外组件冒充官方11阶段。尤其必须修改现有 `execute_writing_brief()` **无条件 `_nk_pov()`** 的逻辑；DISABLED 时提供无 NK 的合法 Brief 材料输入与稳定身份，ENABLED_BUT_UNAVAILABLE 要在付费前失败。CritiCS 目前在组件缺席时可能仅记录 `CRITICS_ENV_MISSING` 后继续，ENABLED 时不能这样签成功。
- **fixture 和模拟隔离**：消除依赖 `project_id.startswith("FICT_")` 获取生产旁路的行为。新模拟只限测试 harness/注入上下文，不能在常规 `produce --mode live` 凭项目名称或输入开关触发。对 `FICT_BAD` 执行真实 Live 入口应当和普通真实项目一样强制合同/来源校验，或者在任何网络前直接拒绝。模拟回执明确 `SIMULATED/fixture_only`，不能通过 `verify-live`、真实费用结算或 `promote`。
- **真实多语言输入**：除了合同生成器，`execute_prose` 的续写 system prompt、各角色提示词、输出验证说明、导出 HTML 的 `lang=zh-CN` 和错误恢复文字，都要由工作合同语言/明确 `visible_unicode_characters` 计数策略决定。无单词计数实现时不能把英语可见字符称作单词数；实际构造的英文续写请求不能含“只写中文正文”这种相反要求。
- Episode/Scene/Arc/Sprint 计划与长度须来源于当前合同和项目配置，不能继承 1500 或 3100 或 500–700 的旧场景常量。正式 Provider output cap、单次调用的长度估算、欠产/超限恢复及 `finish_reason` 必须按实际 Provider 适配器验证；断网模拟至少覆盖不同字数合同的欠产、续写与超限拒绝，且不把拟合的 chars/token 比值冒充通用科学常数。
- 工作合同/角色来源读取依 `work_intent` 选择：`ADAPT_SOURCE` 的原文片段必须真实进入 Plot/对应审稿证据，而不是用与之无关的前后锚替代；`ORIGINAL_EPISODE` 第二章必须消费受控的已选择前章版本，不可因少 `source_file` 在 Sprint/Review/Export 隐式读取 J19。

各产物仍写入相同 CNW 项目层级（如 `06_plot`、`05_scene_cards`、`07_draft`、`08_review`、`09_revision`），并保证用户可在运行记录中追溯精确消费者和当前模型输入。

### 06.1 R5 必做的实际方法保真差分（当前 Atom 不要求完成 Atom-09 的11阶段模拟）

**通用输入包生产调用链（见 0.3a）**：生产入口必须调用既有受检调度与本节列明的实际阶段消费者、审查/修订/Re-review、恢复和导出。包适配层负责身份和资料映射，不得建立绕过 CNW 角色/阶段边界的第二生成器。离线阶段验证与后续真实输入包验收分开记证据。

**必须覆盖的源码/Prompt/配置边界**：`cnw_roles.py:AUTHOR_ROLE_READS/resolve_author_reads/build_author_role_messages`，`cnw_runner.py:stage_predecessors/_role_sources/_planning_stage/execute_plot/execute_scene_cards/execute_writing_brief/execute_prose/_review_sources/execute_five_lenses/execute_three_verifiers/execute_completeness/execute_refine/execute_re_review/_critics_hook`，`cnw_review.py` 各 Lens/Verifier 消息构造，`cnw_lint.py`，`cnw_import_workflow.py`，`cnw_maintenance.py`，`cnw_sprint_live.py`，`cnw_revision.py` 和活动 `prompts/cnw/`。与固定作者方法 M01–M16 逐项映射；不得把“只有11个方法名”当完成。

在临时合成项目以**实际生成的消息和已封存离线响应**做受影响组件测试，并由 Writer 提交原始请求指纹、输入字段列表、产物与消费者映射，Controller 独立读原件：

1. **四角色边界**：Plot 见正确 Arc/Canon/人物；Cards 仅消费自己 run 的 Plot；Brief 正确消费 Plot/Cards/当前合法 Canon/Style；Prose 仅直接看合格 Brief+相关 voice。向来源文件/另一个项目注入唯一假秘密 `GUARD_SECRET_CANARY`，即使存于被允许的上游 Canon，未经 Brief 批准进入正文前 Prose 的最终文学请求不得直接含该原值；向 forbidden_patterns 注入 `GUARD_LINT_ONLY_CANARY`，Prose 请求不能看到它。请求元数据的 SHA/合同 ID 不等于文学正文越权读取。
2. **独立五 Lens**：同一合成 Draft 故意设计 Style、Character、Plot、Canon、story-specific 对应问题；五个不同 request_id/role、各自合法源、彼此不包含前一个 Lens 的 `finding`。相同 Draft 可共享，但不得把五个 Lens 合并成一个 Prompt 并伪写五份返回。对无 Finding 分支应真正零审稿意见，不强行制造审稿结果。
3. **三反证**：带两个原始 Finding 的实测票矩阵；0、1、2、3张未反驳票分别验证 `REFUTED_OR_UNCERTAIN / REFUTED_OR_UNCERTAIN / CONFIRMED / CONFIRMED`；同一 Finding 三种立场请求彼此不共享投票文本，`uncertain` 按默认反驳处理；重复/遗漏/跨 Lens ID 必须拒绝。
4. **Completeness 与 Refine**：有遗漏时可见其新 issue 后续进入修订队列及相应 Lens 未来反馈；没有遗漏时不能虚造。Refine 后针对被改的真实文本版本重新发受影响 Lens 请求，不能复用旧 PASS。两层 Lint 的可执行规则与当前语言/项目绑定，不得在缺 regex 时宣称所有规则 CLEAN。
5. **Canon 和辅助分工**：`INFERRED/TODO_CONFIRM` 及两来源冲突没有旁路升为 Canon；Workflow 03 的审核建议没有在无作者批准时发布正文；NK/CritiCS 禁用不缩减官方职责，启用但依赖缺失 fail-closed。
6. **Sprint 方法门**：精确检查作者固定 `size=5/min_score=75/max_p0_findings=0/max_p1_findings=2` 在真实策略消费者中能被读取，不能仅在 README 出现；本 Atom 只测单阶段/策略组件，完整五话批审与交接留 Atom-09。

每组至少交真实**被测函数输入→实际消息或候选→下游消费者/拒绝**的可查路径及 SHA，不得拿 mock 票当 Live；若尚须 Atom-09 才能检查的路径标 `DEFERRED_TO_ATOM_09` 并保留明确对应终验，不允许本 Atom 自签全量方法效果。

**Atom-06 独立验收**：按 §06.1 提交 M01–M16 适用项的真实消息/输入权限、审稿与反证正负结果、被测消费者效果和方法差分；使用轻量确定性组件测试核实两个项目的四角色实际请求构造/正确来源与声音切片、英文和中文续写真实消息、`NK/CritiCS=DISABLED` 时对应单阶段不调用外部辅助组件、`ENABLED_BUT_UNAVAILABLE` 在付费前拒绝；`FICT_` 项目不会进入正式 live fixture 特例。独立只读 Controller 对这些实证逐项判定，**不能仅凭11阶段枚举或通过 N 个单测 ACCEPT**。完整11阶段的禁用/启用路线、所有审稿者消费者、连续原创 Episode 与模拟回执拒绝 Live 的全链端到端证据由 Atom-09 统一签收；不在当前 Atom 索要尚不存在的完整测试器。

---

## 9. ATOM-07 — 新合同预检、Controller 与恢复通用化

此 Atom 同时解决先前 TS 被旧 J19 审查凭据阻挡的根因，但**本阶段不实际生产 TS**。

### 07.1 定位既有硬绑定

从实际本地 `cnw_live_executor.py`、`cnw_live_provider.py`、`tools/studio.ps1`、相关 W10 工具、`cnw_runner.py`、`cnw_recovery.py`、preflight/acceptance 检查及私有 TS `execution_failures` 读取完整调用链。只凭 `EXECUTION_INCOMPLETE` 不能假定错误代码位置。

如果仅旧文档写死 J19，更新治理/入口映射；如果执行器真把 J19 `contract_sha256` 或老 Controller 证据写入常量，则参数化并提供 per-contract 预检。不得为了通过直接绕开检查。

### 07.2 分开三种审查身份

1. **合同/来源预检**：在 Plot 之前验证当前项目/工作合同/来源/权限/项目配置；无需未来 Plot/Prose/Reviewer 收据。
2. **生产流水线审稿**：CNW 的五 Lens、三反证、Completeness 和 Re-review；绑定实际稿件与请求 raw。
3. **独立工程/候选审查**：Controller 只读对代码、真实作品、证据与候选提交签 ACCEPT/RETURN；Writer 不能代签。用户满意度独立为 `PENDING_USER_READING`。

每次新预检至少绑定：`project_instance_id(新项目)/project_id/work_id/run_id/contract_sha256/work_intent/source_id+source_revision_id(有源时)/source_manifest_revision_sha256(有源时)/source_root_identity/selected_span_or_anchor_sha(按意图)/policy_version/preflight_version/reviewer_identity/evidence_digest`。原创项目使用其经校验的 Canon/Arc/Style、前章引用（非首章）冻结身份代替不存在的 source manifest/anchors，不能填伪 SHA。旧 v5 通过明确限定的迁移映射绑定，不改其旧合同。从当前实现选择可复用字段；无必要不重复发明第二份运行状态。

规则：

```text
if evidence.contract_sha != current.contract_sha: REJECT
if current.is_new_project && evidence.project_instance_id != current.project_instance_id: REJECT
if evidence.project_id != current.project_id: REJECT
if evidence.work_id != current.work_id: REJECT
if evidence.run_id_is_specified && evidence.run_id != current.run_id: REJECT
if evidence.work_intent != current.work_intent: REJECT
if evidence.source_identity != current.source_identity: REJECT
if work_intent == ADAPT_SOURCE && !selected_span_or_json_pointer_hash_matches: REJECT
if work_intent == ORIGINAL_EPISODE && next_episode && !selected_previous_episode_identity_matches: REJECT
if evidence.reviewer_not_independent: REJECT
if evidence.is_future_prose_receipt_required_before_plot: FIX_THE_GATE
otherwise: accept_valid_preflight_only
```

合同缺字段返回具体缺项；不把未来 Provider 回执当预生成必备条件。检验成功不得生成 `USER_CREATIVE_ACCEPTED`。

### 07.2a Controller 工程签收与原作者文学审稿不可互相替代

独立只读 **工程 Controller 子智能体**验收本次代码/合同/source/router 行为；CNW 中的“五 Lens + 每 Finding 三 Verifier + Completeness + Refine + Re-review”是实际作品创作流水线，不能拿工程 Controller 一条 ACCEPT 替代。这是两套不同职责：工程审核可以驳回绕过 CNW 的实现，但不能代替每个文学 Finding 的三路模型反证，也不能代替作者批准 Canon/出版正文。新增 `preflight` 只管**生成前**合法性；不得要求未来模型回执，不得预填 `REVIEWED_CANDIDATE` 或 `USER_CREATIVE_ACCEPTED`。实际不满足合同/来源/权限的 run 应在费用 reserve 之前被拒绝。

### 07.2b ATOM-07 离线身份、可信签收与 Live 权限分层（项目所有者 2026-10-12 补充）

本条为 R5 的有限验收分层修订，不更改 CNW 方法、危险数据门或 Atom 顺序：

1. **确定性离线身份层**：只读核验当前 project/instance、Run、合同字节、source 与 manifest/revision、Policy、Workflow、历史 run_state 快照、旧项目受限外部映射以及 TOCTOU 稳定性。核验结果可为 `OFFLINE_BINDINGS_VALIDATED`，并记录计算出的身份字段与 SHA。该结果只说明身份与来源可确定，不是 Controller 签收，不是恢复资格，也不能授权 Provider。
2. **独立工程 Controller 层**：独立只读 Controller 对精确候选 C/T、离线身份报告、真实 W10 调用链和恢复计划审查后，可给出限定的 `ATOM07_OFFLINE_ENGINE_ACCEPT`。不得因为缺少 API Key、真实付费 Provider 回执或 Live 签名私钥而否定已完成的离线工程核验；也不得把该限定结果写成 ATOM-07 Live 完成。
3. **W10 生产可信签收层**：运行前的 Controller 原始签收必须来自 Writer 不可控制的受信任验证端，并签名绑定 `project_instance_id/project_id/work_id/run_id/contract_sha256/work_intent/source_id+revision/manifest_revision/source_root/selected_span/policy/workflow`。普通 JSON 的 `ACCEPTED`、自报 reviewer/ref 或可重算摘要不是可信签收。签名验证器应通过部署提供的独立信任接口取得信任根；缺少该接口或有效信任根时返回 `ATTESTATION_PENDING`。离线身份报告可以先于签收产生，不能被 Provider 消费为授权。阶段产物的 `accept_controller_role_output()` 必须使用相同的独立签收边界，并额外绑定实际 Run、stage、request/provider receipt 和输出 SHA。
4. **单独 Live/费用授权层**：Provider 请求另需适用于该操作的项目所有者 Live/费用授权、有效 Provider 配置、费用政策/额度与可信签收。离线身份核验或 Controller 工程 ACCEPT 均不能替代这些条件；禁止通过把 `provider_call_authorized=false` 改成 `true` 打通请求。所有者已授权 0.3a 所述计划内必要的通用输入包付费验收，但只有计划与精确代码候选获独立接受后，才能在正确的新项目边界内执行；此项绝不授权 TS Provider 请求、TS 恢复或迁移。

唯一已验证的 TS 如其合同/来源/运行身份与调用链获得完整只读核验，并由独立工程 Controller 接受，可记录 `ATOM07_OFFLINE_ENGINE_ACCEPT`，并按本补充范围申请继续 ATOM-08 中不涉及旧私有数据删除、搬移或切换的安全工程工作，以及 ATOM-09 完全隔离、断网、虚构项目的模拟验收。除非可信生产签收与单独 Live/费用授权另外通过，必须记录 `TS_LIVE_AUTHORIZATION_STATUS=NOT_AUTHORIZED`、`TS_RECOVERY_ELIGIBILITY=NOT_ESTABLISHED`。此路径不接受历史数据迁移、真实恢复或新生产默认启用；`CUTOVER_BLOCKED=true` 继续有效，直至原危险切换门取得 `CUTOVER_READ_ONLY_ACCEPT`。

保留 C3 的 `NO_PUSH_AUTHORIZATION` 和用户后来直接要求推送的审计事实。该用户指令允许当时实际的推送行为，但不能倒写为旧 Controller ACCEPT，也不能替代本补充条款要求的候选 Controller verdict。

### 07.3 中断恢复

- 既有 `EXECUTION_INCOMPLETE` run 的 contract/source/收据/费用原样保留；**不新建同一 TS run，不执行 TS**。原 TS 运行状态的合同、旧 `source:` 键、policy SHA、历史 `execution_failures` 必须通过迁移映射验证可读性，不准重置状态。
- 改代码/配置后，只允许明确的 `refresh-references` / `invalidate` / `resume` 路径恢复受影响阶段；**本 Atom 的测试不得实际调用会执行 Live API 的 `resume`**，只能用纯验证/干跑求出恢复计划和预期下一阶段；不能静默覆盖旧 artifact。
- 严格区分本任务的离线 `READY_FOR_LIVE_PRODUCTION` 与已真实完成 `LIVE_EVIDENCE_VALIDATED`。

**验收**：全新两个虚构项目的合法预检互不复用；含多来源选 B 的合同不能被 A 的预检解锁；ADAPT 与 INSERT 凭据不能互换；旧 J19 证据不能解锁新合同；TS 的真实 run_state 原字节/源 hash/合同/政策身份均有对账；`stage_identity` 在新代码中变化必须明示版本化恢复计划而非伪称旧身份完全相同；在已验证前不输出 `V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK`；0 新供应商请求、原费用状态保持不变。

---

## 10. ATOM-08 — 历史与通用文档拆分，并清洁当前 Git 工作树

### 08.0 R5 方法资料与活动治理入口不可误归档

Atom-01 已经将 `AGENTS.md`、治理/current scope 入口和相关 CLI 文档改为唯一生效 R5 指针；Atom-08 只做最终去旧场景审查，不得**第二次**用历史 P3/J19 文本覆盖该活动指针。`plans/CNW_PUBLIC_REPLICATION_GOAL.md` C01–C15、固定 CNW method pin、合法通用标准操作与本轮 M01–M16 差分是功能保真证据，不是垃圾；保留当前应用所需的脱敏方法映射/测试/Controller 索引，原历史专用诊断原字节另存，不能两者一起删除。需要移除文件时 Controller 必查其入/出消费者，并给来源→新路由映射；仅因为目录名带 `P2/EP001` 不足以删除仍承担通用职责的函数。

### 08.1 活动仓库应留下的东西

- README：说明 StoryStudio 是什么、CNW/NK/CritiCS 方法 pin、应用安装/项目初始化/私有工作区/通用调用/故障恢复。
- `AGENTS.md`：改为长期通用执行规则（不得锁死 J19 或当前 v5 三篇）；Controller、私有文件、证据和真实结果验收继续保持。
- 当前计划文档：本次通用化具体执行阶段及终验状态。
- `docs/`：方法映射、源导入、项目合同、生产、审稿、可恢复性、配置、费用、隐私、通用 CLI 说明。
- `tests/`：自包含的合成 fixture，独立于 `.gitignore` 中旧私有仓库。

### 08.2 必须迁出的东西

- 原先 P2/P3 只针对旧 J19 的施工计划、诊断报告、独立验收历史记录和旧现场截图/导出清单。
- 旧 EP001 作品、旧 J19 桥接参数、JUN-SINGLE-02.3 Source Release 的特殊项目配置。
- 只为第一场实验搭建的单场调试脚本/一次性提示词。
- v5 的 TS/DL/RH 三个已安装项目、其每份 `_INBOX/originals` 和已有 TS Live run：**它们是未来显式挂载的项目数据，不是应用模板，也不是需要删除的垃圾。**旧 J19 的独立 `inputs/private/release` 与原生 CritiCS `ROOT/runs` 等若被历史凭据引用，必须各自独立迁到受限归档，不能只搬 `workspace/cangqi`。

处理受跟踪历史文件时：先完整备份字节+路径+SHA 到仓库外；保留 Git history，然后可用**正常提交中的删除/替换**让当前 HEAD 只留下通用应用。**明确安全事实**：GitHub 官方文档确认从仓库 HEAD 删除文件并不把敏感内容从 Git 历史消除，本轮没有获得重写历史权限。因此交付只能声称 `CURRENT_HEAD_FREE_OF_SCENE_DEPENDENCIES`，不得声称 `GIT_HISTORY_PRIVATE_SCRUBBED`。如现场发现已提交的真实密钥等紧急泄漏，先停止操作并单列安全事件处理，不能依本轮计划秘密强推改历史。禁止 `git filter-repo`、`git gc` 作为删历史工具，禁止改写提交链。

处理 Git 忽略的私有资料时：本次“拆出去”授权允许**经备份、原字节验证与兼容性验收后的无损迁移**，不等于授权销毁。把旧 J19 原始数据、旧运行和导出迁到仓库外独立受限归档，把 v5 三项目迁到仓库外可继续生产的 `<APP_DATA_HOME>/projects/`；成功切换后原位置若仍有冗余副本，须先改名并移动到仓库外受限回退区，**不可在本任务中直接删数据**。若无法保证原始回执身份和恢复能力，标 `LEGACY_RELOCATION_BLOCKED` 并停止迁移，不得声称“完全剥离”。

通用代码/公开说明原则上不能含 `cangqi`、`J19`、`EP001`、固定旧 source SHA、人物名、旧角色声线等项目事实。唯一允许通过**明确外部 legacy archive 说明**追溯旧身份；不能把历史放在当前活动配置或新项目模板中。

第三方上游保留 `.gitmodules`、固定方法引用与许可证；不把作者实际故事或私人资料打包成应用模板。来源固定 pin 可保留。

**验收**：从新的 clone（不包含仓库外历史归档）经声明的固定版本 bootstrap/离线依赖准备启动，README 与 CLI 不指向任何旧 J19 路径；**新本轮通用化的 Controller/测试证据留公共脱敏摘要与私有 raw 的可访问索引，不得被旧历史整理一并删除**；当前仓库目录的活动 `workspace/`/`inputs/private/`/`runs/`/`deliverables/` 中没有残留旧故事或旧场景运行副本（不会为此删除未验证数据）；旧私有数据通过显式指定仓库外路径才可读；历史文件可凭清单逐字节追溯。

---

## 11. ATOM-09 — 两个有原稿 + 一个原创项目的完整离线模拟验收

用临时目录而不是 `workspace/cangqi` 构造**两个完整的有原稿项目（含多源改编和单行 JSON），以及一个无原稿原创 EP001/EP002 连续章节项目**。任何一个都不得复制苍歧源稿或作者公开示例正文：

| 项目 | 原始材料 | 场景类型 | 语言 | 用途 |
|---|---|---|---|---|
| `TEST_HARBOR`（**不以 FICT_ 开头**） | 自造港口题材 UTF-8 `.md`；先导入 A 后导入 B | 同一项目分别建立 `INSERT_BETWEEN` 和 `ADAPT_SOURCE` | 英文 `en` | 测普通合同源选择、两种工作意图、语言与声线；追加第三来源不毁旧合同 |
| `TEST_ORCHARD`（**不以 FICT_ 开头**） | 自造果园**单行 JSON** + 另一个来源 revision | `ADAPT_SOURCE`（JSON Pointer）及一份 episode | 中文 `zh-CN` | 测 JSON 结构定位、跨来源/跨修订、Arc、来源字节保护、项目隔离 |
| `TEST_ORIGINAL`（**不以 FICT_ 开头**） | **完全没有**导入原稿；填真实测试项目 Canon/Arc/Style | `ORIGINAL_EPISODE` EP001 和 EP002 | 已测试语言之一 | 验原创第一章、续章真实依赖与无伪造锚；模拟有合法受控 carry-forward |

**关键修正**：`FICT_` 在当前 `cnw_runner.produce` 中直接触发 `is_fixture=True`，跳过真实来源冻结等检查。**三个通用化 E2E 项目一律使用非 `FICT_` 标识，运行真正的项目/来源/政策/合同校验；只在 Provider 输送层注入不会联网的确定性替身**。更重要：**正式生产代码中的按前缀绕验必须本身被移除或对 live 拒绝**，不能仅靠本次测试不使用前缀规避。可以额外保留 `FICT_` 测试，但它们不得计入通用生产路径验证。替身输出须有实际不同的 Plot/Cards/Brief/Prose/Review 内容和消费/哈希核验；不能把模拟 receipt 传入 `verify-live` 冒充 LIVE。随测试提交源 fixture，测试依赖均从明确声明的本地 bootstrap 准备。

### 09.M R5 方法保真全链强制反证：实物、独立性、作者工作流效果

此处沿用 R4 的三个临时项目和同一隔离网络 harness，**不增加第四个项目、不增加模型付费**。Controller 不能只审 Writers 给的“11阶段完成”清单，应独立读取由真实执行函数构造的脱敏 request/材料散列、各阶段实际候选、Lint/Lens/Verifier/Completeness/Refine/Re-review 的结构化结果、变更稿和下游消费证据：

| 必做覆盖 | 具体失败注入与期望结果 | 独立 Controller 审什么 |
|---|---|---|
| **四角色 M02–M05** | Prose 出现全 Canon、全来源原文、当前规则禁句、另一项目资料、前一 Lens 输出等可追溯 canary：正式请求门拒绝；同 run 的 Plot→Cards→Brief 才能授权具体创作信息。少任一阶段产物不得继续 | 四份真实请求与 reads 范围、Voice 选择、来源 ID、可读正文或拒绝；不只验证输入对象中有 ID |
| **Lint/Lens M06–M07** | 两个项目不同规则的命中必须有差异；一个 Lens 的意见出现在别的 Lens 请求里必须拒绝或在构造时绝对不会发生；第五 Lens 必须是本项目规则 | 原文 SHA 前后一致、规则提取、五个独立调用与其来源/原始响应 hash、各 Lens 真实不同职责 |
| **三反证 M08** | 无 Finding 不出现伪调用；单 Finding 的不同 verdict 模拟覆盖 0/1/2/3 `not_refuted`；任一重复 `finding_id`、少一票、串别项票必须拒绝 | 三种独立立场实际输入/票/聚合、阈值与不确定默认反驳，确认项确实被修订读入 |
| **Completeness/Refine M09–M10** | 有实际遗漏必须进入修订与 Lens 反馈；没有遗漏不能写伪 finding；修改稿故意引入新违规时 Re-review 不能复用旧票宣称 CLEAN | 输入全文和问题集合、两个稿件 SHA 与定位 diff、受影响复审的新材料和未闭合结论 |
| **Canon/Workflow 01–05 M11–M12** | First Import 产生可使用项目资料；Incremental 不把冲突改为 confirmed；**Workflow 03** 真实读取普通 Beta/Canon 审稿生成 P0–P3 计划，未经作者批准不得晋升；Canon Audit 只写 findings/未决，Handoff 真实被后续消费者使用 | 来源状态/旧字节、修订独立文件、审稿到计划链、Canon SHA、Handoff 输入消费。对任意故事不得偷复制作者示例 |
| **五话 Sprint M13** | 同一 Sprint 五个不同 Episode 的产物/批审；`score<75`、`P0>0`、`P1>2`、断章/Canon 冲突均停；合法条件才写真实可读 carry-forward/Handoff（mock 仅测试身份）；不能跨 Arc 门抢跑 | 原作者 `workflow.yml` 阈值确实进执行器、逐话结果、batch review、Arc/Handoff、下一 Sprint 的 input/hash |
| **扩展与分层 M14–M16** | INSERT、ADAPT、ORIGINAL 的源证明不同但使用同一 CNW 角色职责；NK/CritiCS off/on，不代替任何 CNW 环节；模拟票不能 `verify-live` 或正式晋升 | 新意图只是入口扩展；方法未降格；`SIMULATED`/真实费用/创意接受彼此隔离 |

所有关键“通过”必须表现为**实际由生产消费者读取并派生**的文件/回执，不接受通过的单测断言或手工造出的状态 JSON 冒充。若真实代码无法消费某来源/发现/前章、读集越权或 Sprint 门被绕过，**该测试及 Atom-09 均 RETURN，必须重做对应实现**；不存在以“未影响小说审美”为由绕过方法门的通道。原始请求中可能涉及私有/密钥的内容只存受限目录，公共报告仅记录字段、脱敏摘要与 SHA。

### 09.0 真正的离线全链证据机制（R3 新 P0）

**当前事实**：`cnw_runner --mode offline` 不是 Live 11 阶段执行器，只创建请求包；`record-fixture` 能标记阶段也不等于实际运行四角色与五 Lens。为防止假验收，必须使用一个**只供测试调用**的 harness，给以下真实执行器函数/职责注入受控传输替身：`execute_checked/_dispatch_cnw_stage`、四角色读取/输出验证、五 Lens/3 Verifier/Completeness/Refine/Re-review、可选 NK/CritiCS、Export。

实现条件：

1. 两个测试项目使用**非 `FICT_`** `project_id`；从真实合同/Source/Policy/时间边界通过安全校验开始。模拟只替换**最后的 Provider 请求与辅助服务网络边界**，不旁路阶段/消费者函数。
2. 从测试进程启动前设置网络不可达/阻断并取消真 `DEEPSEEK_API_KEY`；拦截真实 HTTP 和子进程网络启动。所有测试账本属于临时目录，真实 `runtime/private/...` 字节不变。
3. 替身为每个阶段产生可区分、符合格式的实际文本和审稿数据（含适用 Finding 和三个 Verifier 的消费、无 Finding 分支）；真实 stage write/校验/hash/read 执行，测试**明确保存输入请求指纹与输出文件**。
4. 所有模拟 Provider 票标 `SIMULATED / MOCK_ONLY`，不标 `SUCCEEDED LIVE`；`verify-live`/真实 `promote` 必须硬拒绝这些测试 run。不能通过给 mock 伪造 http=200/raw/cost SETTLED 换验收绿灯。
5. 检查11阶段全部有可读、内容非空、所属 run/contract/source/上下游身份一致的落盘产物；Review 需要真实发现/投票/驳回链的模拟消费者，不是写11个同名空 JSON。
6. 对原创第一章（完全没有 `_INBOX` 原始稿）和第二章的连续生产都走**完整11阶段 + Export**，不能仅证明 Plot 构造；EP002 必须读取实际选定的前章文本与哈希，模拟前章只可在隔离测试中通过 `SIMULATED_CARRY_FORWARD`，绝不冒充真实已发表正本/真实 `promote`。各项目至少一轮中断恢复/相同 work-id 新 run 版本并存。此验收是 `SIMULATED_OFFLINE_E2E`，不得冒充真实模型创作/成本/作品质量。

### 09.1 端到端最小动作

对两个有源项目的 INSERT/ADAPT 分别执行，并对原创项目两个连续 Episode 执行相应的无源版本：

```text
create_empty_project()
assert project_contains_no_legacy_canon()
import_distinct_source()
verify_original_sha_and_manifest()
prepare_project_specific_canon_and_style()
explicitly_select_source_revision_and_work_intent_if_imported()
create_contract_for_insert_or_adapt_or_original()
preflight_without_network()
run_actual_orchestration_11_stages_with_network_blocked_simulated_transport()
inspect_real_materialized_plot/cards/brief/prose/review_files()
verify_stage_consumer_hashes()
resume_and_export_without_network()
```

至少产生三种工作意图的真正不同内容、可溯源的设计/模拟草稿；不得仅打印 `STAGE_MATERIALIZED` 而没有实际可读文件和消费者校验。

### 09.2 强制负例

- 默认不传项目路径不能落到苍歧；没有经过明确 setup 的 `DataHome` 时必须在写入前拒绝，不能静默填满系统盘。
- 不存在 `Cangqi_Jun_Release_2_3` 仍能初始化并导入。
- A 项目 contract 无法获取 B 项目 source、voice、Brief、Review、run 产物。
- A 项目 Controller 凭据不能解锁 B 项目，即使 work_id/run_id 碰巧相同。
- 旧 J19 预检不能解锁任何虚构新合同或 v5 合同。
- 错误 source manifest SHA、错误 anchor SHA、缺少真实源文件、路径越界、symlink/junction escape、合同被改写均应在真实付费前拒绝。
- 更换项目配置只失效本项目实际受影响阶段，历史 raw/收据不得丢失；追加无关 source revision 不得改写旧合同所固定的 manifest 快照，变更实际 Canon/Arc 依赖时正确识别失效。
- 空项目 `doctor` 能表明 ENGINE_READY；空 Canon 的 `produce` 不能自造事实放行。
- 两个项目导出同名 `run_id` 不得互相覆盖。
- 新项目的初始运行费用应为零、全局旧账本前后 hash 不变；模拟执行仅写临时 ledger，不写任何真实账本行；在**真实公共 Provider 请求函数边界**断言没有 HTTP 请求，不使用真实 `DEEPSEEK_API_KEY`，不生成可被误认为真实的 Provider 回执。
- 两个非 `FICT_` 项目的合同、来源、Anchor、Policy 在执行前都运行正常身份校验；断网替身只负责生成内容，不可跳过这些检查。
- 历史旧 J19 run 显式指定时可只读核验；若缺少来源或版本而无法验证，返回明确 `LEGACY_SOURCE_UNAVAILABLE/LEGACY_POLICY_MISSING`，绝不自动签成功或篡改历史。 若旧验证器在准备 input snapshot 时会修改其状态，只能在隔离复制件上执行；原运行前后 hash 对比必须完全一致。
- 当前 v5 三份合同、TS 原 Run/失败状态的**原文件始终保持原字节**；该 v5 来源是各项目自己的 `_INBOX` 副本（若本机安装与包说明一致），旧 J19 Release/native CritiCS 证据另有路径根；任何附加审查写独立 sidecar，绝不改旧 run_state，本次测试不触碰原 run；路径迁移必须能以**新显式 project root** 识别原始合同和同一 TS run，不能创造第二份独立 run。
- 项目初始化使用**尚不存在的目标路径**必须成功创建，不能在创建项目目录前被 PowerShell `Resolve-Path` 拒绝。
- 旧 TS run 的路径身份通过真实迁移映射校验，不重写状态，也不调用其 Live resume；旧 J19 历史只读检验允许走归档版本，不能用新实现生成出来的虚构 `execution_identity` 覆盖历史。
- 原创第一章**和第二章**都没有任何导入原稿/Anchor，仍可建立真正**非 `FICT_`** 的合法合同并分别完成11阶段模拟；第二章使用真实受控测试前章的明确版本和哈希，Export 不引用不存在的前后原文。该能力测试不得伪造临时“原稿”，不得将模拟 EP001 晋升为真实 Live 已发表。
- 清洁 clone 必须自带可信 bootstrap 操作说明/依赖与固定上游 pin 校验。分别记录 `SOURCE_ONLY_CLEAN_CLONE_TEST`、`PREPARED_RUNTIME_CLEAN_CLONE_OFFLINE_E2E`；后者依赖安装包须真实列出，不得隐瞒需要人工下载的前置条件。
- `NK`/`CritiCS` 关闭与启用但缺依赖是不同状态；在应用路径和项目目录彻底分离后，真正的项目级未启用允许 CNW 11 阶段离线完成；启用但缺依赖前置失败；独立开启后相应辅助输出进入正确的 Brief/Review 请求而不替代 CNW 阶段。
- `FICT_...` 项目名字不能触发 live 绕验；新旧合同 `source.identity_type` 不认识时严格拒绝，不能掉入 legacy。生产网络调用仍必须显式授权。
- 同一 `work_id` 两个 run 的完整 11 阶段模拟产物并存；项目级 import/maintenance/sprint/publish 并发写入遵守同一 CAS，拒绝冲突而不丢更新；未通过审查的 run 不能覆盖 project-level Plot/Cards/Brief/Prose，晋升时做 CAS，错误版本和模拟票不能进入正式晋升；新 run 生成不改旧 run_state。
- 并发交错运行两个项目且使用相同展示 `project_id`（不同 `project_instance_id`）、相同 `work_id/run_id` 的替身测试；复制相同 `project_instance_id` 的两个活跃根则必须拒绝，relocate 保持 ID、fork 新分配 ID；实际模型组装输入和各自回执不串用。
- 真正引发一次生成中间写失败、一次晋升中间写失败和一次源/Config变动，检查已有可读成果及 hash 不变、能恢复而不会误复用旧阶段。
- 非中文合同完整**实际请求内容**、Prose 首次/二次续写、导出 `lang` 不得仍硬叫“中文正文”。单词计数如未实现，明确显示按 Unicode 非空白可见字符统计。超出测试支持的语言/篇幅前置拒绝；欠产、超限恢复必须基于假响应实际通过/返回明确错误，而不是仅断言字段存在。

### 09.2b 大缺口的专用反证矩阵（补 R4；同属 Atom-09）

| 反证 | 输入差异 | 必须从产物/拒绝中实际观察 |
|---|---|---|
| 多源选择 | 先 A 后 B，再反序；合同明确选 B；随后增量导入 C | Plot/Brief 的选段 SHA 必指 B，旧 B source-manifest revision 可读；`SOURCE_SELECTION_AMBIGUOUS` 对漏选失败 |
| JSON 一行 | `{"chapters":[{"text":"one"}]}` 只有 1 行 | JSON Pointer 可锁定指定节点，原始文件 SHA 不变，ADAPT 不要求第二行；错误 Pointer 阻断 |
| 有源整段改编 | 仅 1 行 Markdown 原稿或整章 TXT | ADAPT 用实际 source span；无双边锚仍合法，INSERT 用同样缺双锚材料必须拒绝 |
| 原创连续性 | 无原稿的 EP001→EP002 | EP002 真实消费 EP001 测试用受控版本/hash，能贯通审稿/Export；production `promote` 拒绝 simulated |
| 共用项目写锁 | import 与 publish、maintenance 与 Sprint、两个 publish | 最多一个权威 pointer 版本成功，另一方明确冲突或合法重试，源/Canon/已发表稿没有混合版本 |
| 项目克隆冲突 | 拷贝 identity.json 后两个根同时设为可写 | `PROJECT_INSTANCE_COLLISION`；relocate 不造新身份，fork 不偷旧已签凭据 |
| 离线与 Live 分层 | 全部模拟输出均可读且完整 | 只能得 `GENERIC_OFFLINE_FUNCTIONAL_VERIFIED`；`verify-live`、真实 `promote` 与 `GENERIC_LIVE_VERIFIED` 均明确拒绝 |

每个反证输出输入指纹、实际读取的来源片段/hash、阶段消费目标、正/负结果与不变的原始历史哈希。

### 09.2a 其余公开工作流的必要功能成果

仅完成11阶段场景生成仍不能证明公开 `project-incremental`、`canon-audit`、`handoff`、`arc-review`、`sprint` 不再依赖旧项目。必须使用新项目实际命令与隔离网络替身补验：

1. 在测试项目 A 添加一份**新版本来源**，执行一次真正 Incremental Update，旧来源字节/旧结论保留，新事实与冲突分别记录 `CONFIRMED / INFERRED / TODO_CONFIRM`、来源/hash/未决问题。不是只检查“新增文件存在”。
2. 在测试项目 B 完成一次 Canon Audit 和一次 Handoff，各自读取项目文件并生成可再次消费的非空审查/交接产物；故意制造冲突并证实没有越权自动修改锁定 Canon。
3. 对明确公开支持的 Arc Review、Sprint 执行离线模拟：至少五个不同工作单元组成同一 Sprint，验证顺序、carry-forward、失败暂停、产物索引、项目边界及恢复；**其中原创模式的 Sprint/续篇消费者不能强制 `story.source_file`**；需要模型的职责可使用明确 SIMULATED 响应，绝不冒充五话 Live。
4. 在独立全新项目对作者**Workflow 03 Revision** 跑一次真实受控离线模拟：使用普通审稿/读者反馈与章稿/Canonical 输入，生成 `09_revision/revision_plan.md`（P0–P3、来源、原稿与 Canon 的处理建议），按用户是否批准的两种分支验证修订只另存并记录、未经许可绝不自动 `promote`、已有 07_draft/90_canon 原字节未改。不能以五 Lens JSON 到 Refine 的调用覆盖这条独立公开维护工作流。
5. 对已作为公共 CLI `SUPPORTED` 的 Manuscript Decomposition、Canon Extraction、JET Diagnostic（若明确选用）、Character OS 和普通 Revision Plan，按现有 C01–C15 正式职责读实际输入并至少完成其被声明支持的离线可消费产物/明确 `NOT_SUPPORTED` 边界；**JET 是可选项目框架，不要求启用才能产生合法 CNW 全链**。不能因迁移只剩逐话程序就宣称原作者所有工作流保持完整。
6. 若上述公开命令仍指向 J19 专用目录或功能只有占位而非执行，必须按 Atom-04/06 对应职责定点修复；不得简单删除正式公开功能后宣告 CNW 方法已完整移植。

### 09.3 工具测试

**安全/授权边界必须专门反证**：生产入口 `--mode live` 在未激活项目权限、无 Key、`FICT_` fixture、跨项目凭据、当前目录被 junction 调包等条件下均必须在 `reserve/send` 前失败。迁移脚本的“无 Provider 调用”至少靠三条证据相互支持：联网系统调用被拦截、实际账本前后 hash 相等、全部未变化的真实 Provider request/raw 索引及数量对账。单靠日志“provider_calls=0”不充分。

- 先运行受影响源码的 `py_compile` / PowerShell Parser / JSON schema/语法检查、`git diff --check`。
- 再运行原有对应 tests 和新增隔离/迁移/配置/路径回归 tests。
- 最后运行可在**纯净临时数据目录**执行的完整离线 test suite。
- 测试不得依赖常驻 NK 服务、真实 DeepSeek Key、已有私有 J19 合同或非项目内随附的隐形 fixture。第三方真正必需服务以显式 offline mock 声明覆盖，绝不标 Live。
- 记录每条测试的 exit code、输出文件、sha 和异常分支，不只报告“共 N 通过”。

**验收**：Controller 应先给出完整 `M01–M16` 方法一致性逐项 verdict，Writer 对每个适用项提交真实请求与消费者证据，且 §09.M、§09.2a 的 Workflow 03 和五话 Sprint 负例均成立；不能只是11个阶段名或11个 JSON 文件。两个有源项目分别覆盖 INSERT/ADAPT、一个原创无源项目至少两章，均经过合法非 `FICT_` 真实代码路径模拟运行11阶段至实际文件导出；多来源选择与快照、单行 JSON、公共项目事务锁得到具体正负证据；新项目增量、Canon Audit、Handoff、Arc Review 和 Sprint 有明确可消费的离线产物；全源/实例隔离、同名 run 及候选事务、失败恢复负例成立；旧历史不被改写、账本无新开销；正式 Live 本轮 `NOT_RUN`。作品质量只能标 `NOT_LIVE_VALIDATED`，不承诺模型能写出作者同水平作品。

---

## 12. ATOM-10 — 以真实三项目离线成果交付通用应用

### 10.1 README 必须可操作

在 README 中说明：

1. 从干净 clone 完成受控 `bootstrap`（固定公开原件校验、Python/Node 依赖、NK/CritiCS build）；逐项列出所需网络或离线缓存，不把尚未安装的第三方运行组件视作 READY。
2. 首次执行 `setup -DataHome <实际选择的数据目录>`，或通过 `STORYSTUDIO_DATA_HOME` / 显式 `-DataHome` 给出已选目录；不默认将数据写入系统盘，并展示实际可用空间。
3. 新建与导入一个全新故事项目。
4. 在项目目录填 Canon/Arc/Style/Voice 与项目专属规则。
5. 建立独立工作合同；执行 preflight、produce/step、resume、review/export。
6. 查看任务/来源/Provider/费用/审查证据，如何从中断状态恢复。
7. 历史项目只能通过显式挂载；如何在本机受限归档中寻找迁移前旧 run。说明正常删文件不等于 Git 历史隐私擦除，且不得对旧作品作未获授权的公开分发。
8. 哪些功能本轮只验证 Offline、哪些旧 Live 收据仅是历史事实。

给出一组在**全新虚构项目**上实际跑过的完整命令；路径不得以 `D:\\CangqiStudio`、`workspace/cangqi` 或 J19 作为示例。

### 10.1a 产品能力与证据等级声明（不可省略）

交付必须分开陈述工程实现、实际通用输入包运行和用户对成品的接受：

- `GENERIC_ENGINE_CODE_SEPARATED`：实际代码已经不依赖 J19、冷 clone 可按明示条件启动。
- `GENERIC_OFFLINE_FUNCTIONAL_VERIFIED`：三种创作意图、两源多版本、原创续章、并发、恢复、导出等有真实调度 + 断网模拟消费者和产物。
- `GENERIC_LIVE_PRODUCTION=NOT_RUN`：若本计划的实际输入包生产验收尚未执行，明确记为未运行；不得声称实际 Provider 已为新项目写出文章或 NK/CritiCS 已在真实 Provider 新环境验证。不得使用 `PRODUCTION_READY_VERIFIED`、`LITERARY_QUALITY_EQUIVALENT` 等超出证据的标签。项目所有者已经授权计划内必要的付费验收；仅在活动计划与真实代码候选精确接受、绑定和费用检查通过后执行，不得以未重新询问授权或未检查凭证为由阻塞。
- `V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK`：只证明 TS 现有 run 在迁移后、尚未发起付费请求前，源/策略/审查门可静态验；**不等于** TS 后续真实 Plot/Prose 已运行。
- 所有者授权后的新项目付费验收仍须按 0.3a 在本计划的实现门通过后执行；必须使用其实际输入包，检查要求/材料逐项映射、11 阶段的真实消费者、导出正文及审查证据。此真实故事交付门与较早的离线工程门分开，不可用模拟结果替代；用户阅读后决定创意接受。凭证仅由本机受限运行环境使用，不能记录或提交其内容。

模拟文本不能证明“读者喜欢人物”或“一定达到原作者正文品质”。不得因此重启与通用化无关的文学调优；实际付费验收严格限于所有者已授权的输入包目标和计划门禁。生产结果的创意接受由用户阅读决定，不得把工程/Controller ACCEPT 当作创意接受。

### 10.1b R5 独立方法不变量终验与活动入口切换

- `METHOD_FIDELITY_DIFF` 最终版将 M01–M16 每一行绑定固定上游路径+blob、实际代码/Prompt/配置、规范期待、已执行测试、实际请求/产物/消费者及 Controller 原始判定。所有适用 P0 为 PASS；确实非适用必须给出功能/来源理由，不能把缺证写成 N/A。
- Controller 回查每个 Atom 的**原消息**、精确候选 C/T、远端正常读回身份、已复用证据哈希和所有 RETURN 修复历史；遇到某 Atom 的活动代码已被后续变更影响，必须沿依赖链检查最终行为而不是只指先前 ACCEPT。
- R5 M01–M16 与旧合法显式 CLI 方法入口完成双路回归且接受后，**才**使新通用入口成为默认，并将旧 J19 变为仅显式只读访问；旧资料的完整迁移和费用唯一写入器仍须已通过 Atom-05/08 门。不能用 new README 代替真实 final cutover。
- 由一名真实独立只读子智能体终审；Controller 不可用、任何方法漂移、原数据改动或预期功能实物缺失时终态是 `RETURN/BLOCKED`，不能报告 `GENERIC_OFFLINE_FUNCTIONAL_VERIFIED`。本轮没有一次新的真实 Provider Live，因此文学效果独立 `NOT_VALIDATED`。

### 10.2 最终清洁验证

复核所有活动文件（代码、配置、默认模板、活动提示词、当前 README、活动 tests）：

```text
assert no_scene_specific_constants_in_active_runtime()
assert no_legacy_project_default()
assert no_hidden_dependency_on_ignored_private_files()
assert every_supported_cli_command_has_tracked_implementation_and_offline_smoke_test()
assert original_11_cnw_stages_preserved()
assert cnw_M01_to_M16_method_invariants_have_actual_consumers_and_independent_controller_verdicts()
assert plot_cards_brief_prose_author_read_boundaries_and_prose_forbidden_source_canaries()
assert five_lenses_independent_and_3_verifier_refute_default_2_of_3()
assert canon_workflow_01_to_05_revision_and_handoff_not_auto_promoted()
assert five_episode_sprint_author_thresholds_and_carry_forward()
assert each_atom_controller_is_true_read_only_subagent_with_real_message()
assert method_fidelity_before_after_diffs_reviewed_and_no_open_RETURN()
assert explicit_source_revision_selection_and_immutable_manifest_history()
assert three_distinct_work_intents_including_json_pointer_and_original_sequel()
assert all_authoritative_mutations_share_project_level_cas()
assert native_nk_and_critics_integrations_preserved_or_explicitly_optional()
assert historical_receipts_not_rewritten()
assert all_new_project_tests_reproducible_on_clean_checkout()
assert project_A_and_B_data_isolation_verified()
assert duplicate_project_instance_id_cannot_be_double_writable()
assert default_live_is_unverified_and_forbidden_during_refactor()
assert private_files_not_git_tracked()
assert legacy_and_v5_project_data_live_outside_app_checkout()
```

命中 `J19` 等旧关键字时必须区分**纯历史归档**与仍被运行代码消费；运行路径零实际硬编码是验收重点。不能通过关闭扫描规则制造清洁报告。

### 10.3 独立 Controller 终验与 Git

Controller 在真实工作树只读检查：

- 对应 Atom 的实际 diff、原始命令/测试证据和迁移 manifest。
- Controller 原始 `CONTROLLER_BOOTSTRAP_ACK`、Atom-00…10 方法不变量 M01–M16 判定及受影响源码的 `METHOD_FIDELITY_DIFF`；任何漏项先 RETURN，不接受 Writer 自我判分。
- 四角色最终实际模型消息白名单、审稿 Lens/Verifier 的互相隔离和票决、Canon 事实晋升/Workflow 03、五话 Sprint/Arc/Handoff 的实际消费证据；不能用11阶段枚举、生成的文件数量或缓存 SUCCESS 替代。
- 原 CNW 11 阶段和职责没有被删/冒名顶替。
- 真正无场景依赖的两项目回归证据。
- 历史 Git 未改写、账本和私有运行证据未丢失。
- W10 未提交文件在迁移中未被静默覆盖，其后续归属（通用实现/历史归档）有明确记录。
- 旧 J19 与三场 v5 **不是启动依赖**；迁移后三场 v5 和旧 J19 数据不再停留在当前应用代码目录内；新应用不自动开始旧项目生成。

代码候选**先本地正常提交**形成精确 Commit/Tree，保留受保护未提交 W10 清单；Controller 独立只读审该 C/T 与工作树/迁移证据。只有 Controller 返回 `ACCEPT` 后才正常**推送**，随后独立 fetch / `git ls-remote` 回读 C/T。若 RETURN，追加修复提交得到新 C/T 后再审；禁止 Writer 自签，也禁止在未提交前伪造候选 Commit。

---

## 13. 失败/恢复策略（强约束）

| 发现 | 应对 | 禁止行为 |
|---|---|---|
| 源码仍在读取苍歧默认路径 | 找出真实函数和消费者，改为显式项目上下文，并补负例 | 只改变量名或添加 try/except 掩盖 |
| 通用配置变更使旧 `policy_sha256` 对不上 | 读取旧冻结配置快照或 legacy resolver，分版本只读验证 | 改写旧 SHA、放宽 hash 门 |
| 旧 P2 脚本是新流程真实依赖 | 提取通用执行功能并转接，再归档旧脚本 | 先删脚本再报“缺依赖” |
| 旧 W10 工作未提交 | 单独哈希封存后逐函数检查，留在原位直到兼容转接成功 | `git clean`、覆盖、复制新空文件 |
| 新项目初始化缺 Canon | 建空白项目和 TODO，生产预检明确缺项 | 偷用苍歧或作者示例 Canon 填充 |
| 本地无法获得历史私有原稿 | 保留原路径与 raw，标记无法完成历史验证，不阻塞新项目 | 伪造旧历史测试 ACCEPT |
| 迁移期间合同/run/账本发生预期外变化 | 停止写操作，按字节清单恢复，复盘影响 | 继续强推、删除证据、重算历史费用 |
| 旧 run 的绝对路径/原生 CritiCS/NK 证据无法重定位 | 保留源目录与镜像，先做兼容解析和验证；未完成前保持 `LEGACY_RELOCATION_BLOCKED` | 以修改旧 raw 和 hash 强行改路径 |
| 需要修与本次场景隔离无关的随机文学瑕疵 | 记录为诊断，不扩大本次 Atom | 无限修样本、重复付费生成 |
| CNW 角色越权、Lens/Verifier 非独立、2/3 阈值错误或 Canon 自动晋升 | Controller `RETURN_METHOD_DRIFT`，定位最早来源/请求构造/真实消费者，Writer 在本 Atom 定点修复并重审 M 项 | 降低 oracle、删掉异常用例、把审稿或 Controller 一项冒充另一项 |
| Workflow 03/五话 Sprint/Arc 门消失或只剩空占位 | 回到固定作者 Workflow 01–05 与 `workflow.yml`，恢复真实请求、写入与后续消费；按影响范围复验 | 删 supported 命令或只改 README 来宣称方法保留 |
| 无法真正启动单独只读子智能体，或它没有读原件 | 保留本地候选与保护数据，报 `CONTROLLER_UNAVAILABLE/EXTERNAL_INPUT_NEEDED` | 让 Writer、模型自评或预制 `ACCEPT` 替代独立验收 |
| 半成品新 CLI 会使旧显式可用入口失效 | 保持影子路由与旧入口，修完双路回归再切换，Controller RETURN 时不推送 | 提前替换默认入口、删唯一消费者、推送有已知破坏的候选 |

用户不需要为每个机械性路径修复重新批准。确实会丢失/无法完整复制私有历史时，停在该 Atom 并报告准确风险；不得硬做不可逆迁移。

---

## 14. 最终唯一交付格式

请给用户提交以下清楚的报告和可复用应用，不要只发送一句 `REFACTOR_COMPLETE`：

```text
STORYSTUDIO_GENERIC_APP_REFACTOR

BASE_HEAD=<实际本地原 HEAD>
FINAL_HEAD=<实际新 HEAD>
FINAL_TREE=<实际 tree SHA>
REMOTE_MAIN=<实际回读 SHA>
ATOM_00..10=<各 Atom 独立 Controller ACCEPT/RETURN 与证据路径>
R5_PLAN_SHA=<实际导入仓库的完整计划 SHA>
GOVERNANCE_AND_ENTRYPOINT_PRECEDENCE=<已读AGENTS/GOVERNANCE/CONTROLLER及唯一活动R5指针>
READ_ONLY_SUBAGENT_INSTANCE=<实际启动证据/身份；未启动则BLOCKED>
CONTROLLER_BOOTSTRAP_ACK=<真实原始消息索引；缺失不通过>
CONTROLLER_METHOD_VERDICT_M01_M16=<逐项 PASS/RETURN/UNVERIFIED 及来源证据>
METHOD_FIDELITY_DIFF=<旧实现基线、固定作者规范、新执行效果及每 Atom 审核 SHA>
ROLE_READ_BOUNDARY_AND_PROSE_CANARIES=<四角色真实请求、Brief/Voice白名单、越权拒绝>
INDEPENDENT_FIVE_LENSES_AND_VERIFIER_2OF3=<五独立审稿、三独立票、阈值真实结果>
CANON_WORKFLOW_01_TO_05=<First Import/Incremental/Revision/Audit/Handoff 真产物与晋升保护>
FIVE_EPISODE_SPRINT_AUTHOR_THRESHOLDS=<5话/75分/P0=0/P1<=2/失败暂停/Arc交接>
CUTOVER_READ_ONLY_ACCEPT=<Controller在迁移指针切换前的真实许可消息>
FINAL_GENERIC_ENTRYPOINT_GATE=<影子/旧显式/新默认入口双路回归与签收>

ACTIVE_J19_COUPLINGS_FOUND=<真实数量与路径>
ACTIVE_J19_COUPLINGS_REMAINING=<应为 0；逐项证据>
OLD_SCENE_ARCHIVE=<仓库外实际位置、manifest SHA>
ACTIVE_V5_PROJECT_DATA_HOME=<仓库外实际位置、三项目清单 SHA>
ACTIVE_REPO_OLD_DATA_REMAINS=<应为 0；如果被锁阻断必须给证据而非删除>
PRIVATE_DATA_PRESERVED=<原/新 hash 对账>
OLD_J19_HISTORY_STATUS=<保留与可核验范围>
V5_TS_DL_RH_INSTALLS=<三项目身份及原位置>
TS_RUN_STATUS=<未被改变的真实状态>
W10_UNCOMMITTED_FILES=<列出 6 件及迁移处理结果>

NEW_PROJECT_A=<初始化/导入/合同/离线流水线/导出真实证据>
NEW_PROJECT_B=<初始化/导入/JSON-Pointer 改编合同/离线流水线/导出真实证据>
SOURCE_REVISION_SELECTION=<多来源 A/B + 增量 C，B 精确绑定及旧快照验证>
WORK_INTENT_COVERAGE=<INSERT_BETWEEN/ADAPT_SOURCE/ORIGINAL_EPISODE 真消费证据>
JSON_SINGLE_LINE_ADAPT=<一行 JSON Pointer 的原文哈希+正文产物>
ORIGINAL_EP002_CONTINUATION=<受控前章版本/hash消费+完整11阶段模拟>
CROSS_PROJECT_ISOLATION=<真实负例>
PROJECT_AUTHORITY_WRITE_CAS=<import/maintenance/sprint/publish 并发冲突与可恢复事务>
PROJECT_INSTANCE_COLLISION_POLICY=<relocate/fork/duplicate 负例>
DATA_HOME_RESTART_PERSISTENCE=<setup选择后新进程能找到同根且不默转系统盘>
CNW_11_STAGE_METHOD=<官方 pin/映射/产物验证>
NK_CRITICS_STATUS=<通用依赖/适配情况>
SOURCE_HASH_POLICY=<旧 run 兼容验证情况>
COST_LEDGER_BEFORE_SHA=<...>
COST_LEDGER_AFTER_SHA=<...>
NEW_PROVIDER_REQUESTS=0
LIVE_AFTER_REFACTOR=NOT_RUN
GENERIC_OFFLINE_FUNCTIONAL_VERIFIED=<仅网络隔离模拟的实物产出>
GENERIC_LIVE_PRODUCTION=NOT_RUN
REAL_PROVIDER_OUTPUT_QUALITY=NOT_VALIDATED
USER_CREATIVE_ACCEPTED=PENDING_USER_READING

SOURCE_PATH_IDENTITY_V2=<new run source/manifest path-freeze test>
OLD_TS_SOURCE_MAPPING=<old path key/actual new file hash match>
V5_OLD_POLICY_HASH_RESOLUTION=<all three existing contract results>
V5_RESUME_PREFLIGHT_ELIGIBLE_WITHOUT_NETWORK=<TS deterministic preflight, no provider>
RUNTIME_BOOTSTRAP_STATUS=<source/core/optional/live-provider readiness separated>
LICENSE_ATTRIBUTION_CHECK=<CNW pipeline CC-BY attribution, third-party NK/CritiCS notices, proprietary example-content not used>
LIVE_PERMISSION_DEFAULT=<new projects blocked until explicit authorization>
NON_FICT_REAL_CONTRACT_E2E=<2 imported-source 项目3种源模式 + 1 source-less original 的EP001/EP002，实际消费者11阶段断网模拟>
ACTIVE_CLI_COMMAND_COVERAGE=<no untracked W10 dependency in clean clone>
GENERIC_MAINTENANCE_ARC_SPRINT=<incremental/audit/handoff/arc-review/five-unit sprint simulated outputs>
FRESH_ORIGINAL_EPISODE_NO_SOURCE=<EP001/EP002 合同、11阶段模拟、前章身份、导出>
RUN_CANDIDATE_ISOLATION=<same work-id multi-run / interrupted transaction / promotion CAS evidence>
OPTIONAL_NK_CRITICS_GATE=<DISABLED full-11 success; ENABLED missing fails closed>
LIVE_FIXTURE_BYPASS_REMOVED=<FICT prefix negative and simulated receipt denied>
PROJECT_INSTANCE_ID_ISOLATION=<distinct same-name projects and A/B receipts>
ORIGINAL_EP001_FULL_SIMULATED_CHAIN=<all 11 stages + export; source-less>
ENGLISH_ACTUAL_PROMPT_LANGUAGE=<initial/continuation/export evidence>
GIT_HEAD_CLEAN_NOT_HISTORY_SCRUBBED=<GitHub current HEAD vs historical visibility>
MODEL_WRITING_QUALITY=<NOT_VALIDATED_THIS_ROUND>
GENERIC_APP_README=<实际路径>
CONFIG_TEMPLATE=<实际路径>
CLEAN_CLONE_OFFLINE_TESTS=<命令、结果及产物>
CONTROLLER_VERDICT=<真实独立结果>
NEXT_ACTION=等待用户另行指示挂载 v5 TS/DL/RH 并正式创作
```

### 最终硬停止边界

**只有 R4 原 P0 及 R5 M01–M16 全部适用硬保护有真正的离线反证、实际可读消费者产物，且 Atom-00…10 与危险迁移切换具备真实独立只读子智能体 Controller ACCEPT，才允许报告“通用应用离线功能重构完成”，不得报告“新项目真实模型生产已验证”。** 若 TS 源/旧政策/迁移 hash 无法现场核验、旧账本有未结写入者、数据空间不足、同 work-id 产物仍可能覆盖、模拟绕验仍存在或 `NK=DISABLED` 无法走完整链，则停止在对应 Atom，报告 `INCOMPLETE/BLOCKED` 和精确恢复步骤；不得因为完成大量文档或通过多数单测就降格签收。无本地 W10/私有 raw 时，只能对**纸面设计**给出有界审查，不能许诺现实一定绿。


完成**通用应用化、外部归档、两个不同有源项目 + 一个原创无源项目的真实调度模拟验收、独立 Controller 验收、正常提交/远端回读**后，**立即停止本轮工作**。

- 不启动 TS/DL/RH Plot。
- 不因为还有旧 J19 文档藏在 Git 历史中就再修改历史。
- 不要求把原作者真实作品/私有代码迁入仓库。
- 不为了文学样本零瑕疵追加无限整改。
- 不把“Offline 通用化验收”宣布为“新的 Live 全链已经验证”。

**验收对象是一个在没有苍歧、没有 J19、没有原有私有数据的环境中仍能独立安装、管理多来源与多修订项目，支持插写/既有文本改编/原创连续章节，并以隔离网络的真实11阶段调度产生、复核、恢复和导出候选作品的 StoryStudio 通用应用。**这是**离线通用化效果验收**，不是对尚未运行的真实付费模型生产或文学品质做结论。 新环境的真实付费创作效果、文本审美质量及 TS/DL/RH 正式作品验收均为后续独立任务，不能在本轮无网络条件下宣称已证明。
