# G01 活动计划来源矩阵

状态：候选，等待独立 Controller/Reviewer 对精确 G01 commit/tree 审查。`reviewer_verdict=PENDING` 是诚实状态；Writer 的来源映射不是独立批准。计划源自用户明确要求执行的 ZIP 规则：`StoryStudio_Governance_First_Rebuild_Package_20261010.zip` SHA256 `EA42530DF4947615E80E5D7576752DE813D3272E034DF9CF77C0A92224E98A1F`；下文“ZIP计划”均指包内精确路径 `plans/MASTER_PLAN_FROM_EMPTY.md`，原文件 SHA256 `B2DE9FD14C8C1F91D0FDD017017569B02CAFFCE4E6AA1340B6DDC8DD8B1EE926`。`USER` 表示包内用户授权的具体指令；`UPSTREAM` 表示精确 pinned 原文；`ADAPTER` 只限隔离、传输或证据记录，不改变创作决策。用户另明确委托本任务验收智能体担任 Controller，委托记录位于根 `AGENTS.md`。

| item_id | action | source_type | exact_path; source_commit/blob; evidence | requested_change | affected_owned_file | impact | reviewer_verdict |
|---|---|---|---|---|---|---|---|
| P-A1-01 | 记录远端 main 身份与本地现场差异 | USER | ZIP计划 §A1/§G00 SHA256 `B2DE9FD14C8C1F91D0FDD017017569B02CAFFCE4E6AA1340B6DDC8DD8B1EE926`; 本轮 readback: `refs/heads/main` C=`06c66de7c7f18263039ea19a47e84c29716cde4b`，tree未提供 | A1 标记本轮 main C 已核、tree NOT_VERIFIED | `plans/MASTER_PLAN_FROM_EMPTY.md` | 不覆盖本地数据 | PENDING |
| P-A1-02 | 只借鉴 MVP 治理机制 | USER | ZIP计划 §A1; MVP `perf/r667-migration-20261008` C=`2f3d6f9af77a784aa92369cbb224e2cc9cc9a02b`, tree=`d4ab7ddbd15d69fde4a366f4bd7995f1bd4ab065` | 记录参考身份，排除业务合同移植 | plan | 控制范围 | PENDING |
| P-A1-03 | 固定 CNW 原版来源与 SHA | USER | ZIP计划 §A1; CNW C=`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`, tree=`f06a7b693fda124761b69ad40ab483cc82960219` | 只读原版工作流 | plan | 不改上游 | PENDING |
| P-A1-04 | 固定 NK 来源与 SHA | USER | ZIP计划 §A1; NK C=`b857f34b7d371ae82c30e00eb021884c14d08ae9`, tree=`3960b25cb52265933e0fa4897d1319ad6161bf9c` | 只读原版工具 | plan | 不改上游 | PENDING |
| P-A1-05 | 固定 CritiCS 来源与 SHA | USER | ZIP计划 §A1; CritiCS C=`fbf66cbc913012c6f80af1687e27f0ce350475e3`, tree=`c48be7d9cbeb680238a9e832be86bdf167c305a9` | 只读原版工具 | plan | 不改上游 | PENDING |
| P-A1-06 | 将已知 2.3 hash 仅作参考身份 | USER | ZIP计划 §A1/§I02; `JUN-SINGLE-02.3`, SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2` | 不声称本机已有文件 | plan | 避免错误 Canon 输入 | PENDING |
| P-A1-07 | 记录 DeepSeek API 入口/模型字段 | USER | ZIP计划 §A1; DeepSeek 官方文档 `https://api-docs.deepseek.com/zh-cn/`，检索日期 2026-10-10 | 仅公开事实，真实调用保持 NOT_RUN | plan | 不产生 API 请求或预算授权 | PENDING |
| P-A1-08 | 区分事实、参考和未知 | USER | ZIP计划 §A1; §E 报告字段 | 对未读取项标 NOT_VERIFIED/NOT_RUN | plan | 防止伪造证据 | PENDING |
| P-A2-01 | 审核 NK 真实 API Key 获取方式 | UPSTREAM | NK @ `b857f34b7d371ae82c30e00eb021884c14d08ae9`: `lib/openaiServer.ts` blob `79481aeb06e68c1679e793e32752710f299a7009`, L4–10；README blob `7f4c337c65e5743c01623e80a494898a1df8f2e9` | 只记录代码事实，不读取 Key | plan §A2 | API 安全 | PENDING |
| P-A2-02 | 标明 NK 生成模型与 schema 原样限制 | UPSTREAM | NK @ `b857f34b7d371ae82c30e00eb021884c14d08ae9`: `app/api/generate-perspective/route.ts` blob `d3ec1181cd94553126673e515bfe24ce611f6511`, L256–258 (`generateObject`, `ResponseSchema`, `gpt-4.1`) | I01隔离核验 URL/模型兼容；不改源码/PROMPT/schema | plan §A2/I01 | 可能阻断 Flash 兼容 | PENDING |
| P-A2-03 | 将 NK 外置 base URL/结构化输出标未验证 | USER | ZIP计划 §A2.1 明令不得假定 SDK 环境变量支持 | 只在 I01 给出原始证据，不预判兼容 | plan | 禁止越权真实调用 | PENDING |
| P-A2-04 | 记录 CritiCS 默认 GPT 模型 | UPSTREAM | CritiCS @ `fbf66cbc913012c6f80af1687e27f0ce350475e3`: `critics/setting/chatsetting/gptsetting.py` blob `848802dae2fcd2cf29769dc06b539f106ca1b8af`, L12/L15 | 记录硬编码，不擅自替换模型 | plan §A2 | 可能阻断只用 Flash | PENDING |
| P-A2-05 | 对 CritiCS 可疑语法做隔离实证 | USER | ZIP计划 §A2.2/§I01；原文件 blob `848802dae2fcd2cf29769dc06b539f106ca1b8af`, L43 `verbose=True                       s` | 仅报告源文本异常；I01 对原字节副本 py_compile 后定论 | plan §A2/I01 | 禁止未证实称 SyntaxError | PENDING |
| P-A2-06 | 记录 CritiCS OpenAI endpoint 与依赖 | UPSTREAM | CritiCS @ `fbf66cbc913012c6f80af1687e27f0ce350475e3`: `storygen/common/llm/llm.py` blob `ceea77242eb35b3061cfb86654a625bbc86c8325`; requirements blob `97861b02df31a9092d8bf42bc143230bd1d6a11a` | 记录精确版本及 endpoint，不安装 | plan §A2 | 兼容性与平台风险 | PENDING |
| P-A2-07 | 将 CNW 界定为人工 prompt/procedure 工作流 | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: `templates/_workflows/README.md` blob `afe16e553bef171f551c4f82c43a14f86c0aad71`, L3；`01_first_import.md` blob `56148578d91d55e492a6913b4d73cbe529c34ecf` | 只读原文执行，不造 Story Agent | plan §A2/I03 | 创作流程来源 | PENDING |
| P-A3-01 | 不恢复旧S/AT计划或未授权的生成规模设计 | USER | ZIP计划 §A3；包内 `reviews/DESIGN_AUDIT.md` SHA256 `adfd2887d7e4fead7ca45afe421b84c1381834bef0c7f155d3bad6a187f49f65` | 仅保留本轮单场边界 | plan §A3/I04 | 防止旧工作流与批量扩量 | PENDING |
| P-A3-02 | 禁止任何 Vendor 字节或运行副本算法变化 | USER | ZIP计划 §A3、§I00、§I01 | pinned 源与运行镜像均不修改业务字节 | plan §A3 | 上游完整性 | PENDING |
| P-A3-03 | 不把构建、HTTP或自写意见冒称原版/创作成功 | USER | ZIP计划 §A3、§I04、§I05 | 分开工程、功能和读者质量状态 | plan §A3 | 验收真实性 | PENDING |
| P-A3-04 | 用户未读前停止扩量 | USER | ZIP计划 §A3、§I04、§I05 | 用户亲读前标 `CONTROLLER_REVIEW_REQUIRED` | plan §A3/I04 | 质量/范围控制 | PENDING |
| P-A3-05 | 不私设模型、token、调用或费用额度 | USER | ZIP计划 §A3、§I04; 用户明确“按包规则跟流程跟指令执行” | 保持 Flash-only 且无未授权预算 | plan §A3 | 费用边界 | PENDING |
| P-B-01 | 建立项目自有文档、计划、证据和私有目录边界 | USER | ZIP计划 §B 路径树 | 仅 StoryStudio 自有目录可写；私有目录忽略 | plan §B | 目录所有权 | PENDING |
| P-B-02 | 原版 CNW 许可不能外推到示例故事 | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: README blob `0e70b25492c0a43c94814a34a6b2f3a997fc2f32`; LICENSE blob `e900c48410bda2c2eb5a3d780d3c8ffc6e6d12ca` | 不公开复制示例故事材料 | plan §B | 版权范围 | PENDING |
| P-B-03 | Vendor用 pinned gitlink；运行构建物落隔离目录 | USER | ZIP计划 §B、§I00、§I01 | 用原字节 runtime 副本运行 | plan §B/I01 | 上游只读 | PENDING |
| P-B-04 | 公开提交仅含治理、source pins 和脱敏证据索引 | USER | ZIP计划 §B 公共Git条款、§I05 | 原稿、Key、正文和完整响应留私有区 | plan §B/I05 | 隐私及版权保护 | PENDING |
| P-B-05 | 工具目录只容纳项目自有检测/搬运/纯传输 | USER | ZIP计划 §B 路径树；GOVERNANCE §01 O层 | 不创建第二套创作算法 | plan §B | 所有权与方法边界 | PENDING |
| P-G00-01 | 核实 Git 与无损本地状态后再建候选 | USER | ZIP计划 §G00; 当前接受记录 `02f466d8bec68ee4df9a0eeb0f2c9722334552dd/597aad4f54feb93ededb3220fb07f353c1ffb498` | 只读检查，不 reset/clean | plan §G00 | 保留 WIP | PENDING |
| P-G00-02 | G00 只纳入指定治理文件 | USER | ZIP计划 §G00；包内治理文件哈希见 `MANIFEST_SHA256.txt` | 禁止提前纳入工具/样本 | 历史 G00 | 阶段隔离 | PENDING |
| P-G00-03 | Reviewer核差异并绑定精确C/T | USER | ZIP计划 §G00；本委托修订由 Controller 同一子智能体复核 | 精确签收，不自签 | G00记录 | 证据链 | PENDING |
| P-G00-04 | 普通 push、远端 readback 后 Controller 接受 | USER | ZIP计划 §G00; 远端 G00 修订 readback 消息 | 非 force push，下一 Atom 逐阶段解锁 | G00记录 | 远端一致性 | PENDING |
| P-G01-01 | 从 pinned 源 blob 与治理文件核事实 | USER | ZIP计划 §G01、PLAN_AUTHORING_STANDARD §A | 只写纯文档来源映射 | plan/matrix | 计划可信性 | PENDING |
| P-G01-02 | 对每个计划行动映射 UPSTREAM/USER/ADAPTER | USER | ZIP计划 §G01；授权的原始包 SHA `B2DE9FD14C8C1F91D0FDD017017569B02CAFFCE4E6AA1340B6DDC8DD8B1EE926` | 未归属项移除或标待裁决 | matrix | 无无来源创作决策 | PENDING |
| P-G01-03 | 审查 B01–B14 与计划的逐项符合 | USER | ZIP计划 §G01; 当前 G00治理 B01–B14 | 只报告/纠正当前计划范围 | plan/matrix | 不弱化黑名单 | PENDING |
| P-G01-04 | Controller 对精确计划 C/T 接受后才解锁 I00 | USER | ZIP计划 §G01；G00 已接受治理委托 | G01不授权克隆 | plan | 阶段门 | PENDING |
| P-I00-01 | 仅在 G01 接受后检视子模块状态 | USER | ZIP计划 §I00; G00 governance §06 | 不覆盖现有目录 | plan | 保留用户数据 | PENDING |
| P-I00-02 | 固定 CNW 精确 commit | USER | ZIP计划 §I00；CNW来源 commit 同 P-A1-03 | 只加入 gitlink | plan | 来源可复现 | PENDING |
| P-I00-03 | 固定 NK 精确 commit | USER | ZIP计划 §I00；NK来源 commit 同 P-A1-04 | 只加入 gitlink | plan | 来源可复现 | PENDING |
| P-I00-04 | 固定 CritiCS 精确 commit | USER | ZIP计划 §I00；CritiCS来源 commit 同 P-A1-05 | 只加入 gitlink | plan | 来源可复现 | PENDING |
| P-I00-05 | 忽略私有/运行目录且不泄漏 Key | USER | ZIP计划 §B/§I00 明确要求；G00治理 §06 | 本项目自有 `.gitignore` 与只读 ignore 核验 | plan | 隐私与工程隔离 | PENDING |
| P-I00-06 | 核上游 clean/pinned 并经远端签收 | USER | ZIP计划 §I00; 各固定 Git SHA | 不在 Vendor 内写文件 | plan | 不可变证据 | PENDING |
| P-I00-07 | 保留三上游许可证并记录归属 | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: `LICENSE` blob `e900c48410bda2c2eb5a3d780d3c8ffc6e6d12ca`; NK @ `b857f34b7d371ae82c30e00eb021884c14d08ae9`: `LICENSE` blob `d6cca24a828d468505a26e5185f9bb5b195d0d22`; CritiCS @ `fbf66cbc913012c6f80af1687e27f0ce350475e3`: `LICENSE` blob `61ea5cb2832e6d3e99da5b9b81952031f91de7a5` | 纳入许可/来源说明，不复制受限作品 | plan | 许可证归属 | PENDING |
| P-I01-01 | 原字节复制到隔离 runtime 再安装/编译 | USER | ZIP计划 §I01 与 G00治理 §06 明确要求 | 只在副本生成构建物 | plan | 防污染 Vendor | PENDING |
| P-I01-02 | 只读探测本机环境，不装大型依赖 | USER | ZIP计划 §I01 第4条 | 先查 Node/npm/Python/WSL/硬件 | plan/evidence | 不改变环境 | PENDING |
| P-I01-03 | 实测 CritiCS 语法异常但不修源 | USER | ZIP计划 §I01 第5条；CritiCS blob `848802dae2fcd2cf29769dc06b539f106ca1b8af` L43 | 运行原字节副本 py_compile 并保留原错 | plan/evidence | 归因 upstream | PENDING |
| P-I01-04 | 实证 NK Flash 路由与原 schema，不发真实创作调用 | USER | ZIP计划 §A2.1、§I01 | 有实证前保持 NOT_TESTED | plan/evidence | 控制模型与费用 | PENDING |
| P-I01-05 | 保存命令、退出码、错误和哈希 | USER | ZIP计划 §I01交付；GOVERNANCE §03/B08 | 原始失败与成功证据对应工具 | evidence | 可审计 | PENDING |
| P-I01-06 | 逐工具报告原版兼容状态 | USER | ZIP计划 §I01交付状态枚举 | 不宣称全栈成功 | evidence | 结论准确 | PENDING |
| P-I01-07 | I01阻塞交 Controller，不自动绕过 | USER | ZIP计划 §A2、§I01；B10/B11 | 不继续I02/I03/I04超出授权的工作 | plan | 硬阶段门 | PENDING |
| P-I02-01 | 仅从 Known Folder 定位 Downloads | USER | ZIP计划 §I02；不假定旧路径 | 只读目录定位 | plan | 避免错误路径 | PENDING |
| P-I02-02 | 只匹配指定 SHA，不下载替代版 | USER | ZIP计划 §I02; SHA `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2` | 精确版本验证 | plan | 防止 Canon 替换 | PENDING |
| P-I02-03 | ZIP结构检查后私有解压，禁止运行包内代码 | USER | ZIP计划 §I02 | 私有隔离解压 | plan | 防数据泄漏/执行 | PENDING |
| P-I02-04 | 验证 manifest 32场与版本后再签收 | USER | ZIP计划 §I02 | 证据化版本身份 | plan | Canon边界 | PENDING |
| P-I03-01 | 依据 CNW 原文执行 Existing Project Import | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: `docs/EXISTING_PROJECT_IMPORT.md` blob `25a28031c203f716fcb9c9e7b174acb445e66c94`; workflow blob `56148578d91d55e492a6913b4d73cbe529c34ecf` | 保留 CONFIRMED/INFERRED/TODO_CONFIRM | plan | 原作者方法 | PENDING |
| P-I03-02 | 仅做一个 Plot/Card/Brief，来自原版模板 | USER | ZIP计划 §I03；CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: `templates/06_plot/README.md` blob `8543f455d23dfe7fc01bc61adf641fcec511d73e`; `templates/05_scene_cards/README.md` blob `33e553ac36695db19aaacebb34a4035bf85d57a4`; `templates/07_draft/README.md` blob `e64638e11ec8fcf6c184565891eaf901c3cbb965` | 私有工作区只做一场设计 | plan | 不扩大生产 | PENDING |
| P-I03-03 | 保留前后原著锚点与知识边界 | USER | ZIP计划 §I03; 原作输入身份 SHA 同 P-A1-06 | 推论不升 Canon，不泄密 | plan | Canon正确性 | PENDING |
| P-I04-01 | 付费前须通过原版兼容并由 Controller 接受 | USER | ZIP计划 §I04 | 不兼容状态 NOT_RUN/BLOCKED | plan | API授权门 | PENDING |
| P-I04-02 | 只用用户允许模型 deepseek-flash | USER | ZIP计划 §A1/§A3/§I04 | 不选 Pro/GPT/替代后端 | plan | 模型范围 | PENDING |
| P-I04-03 | 写一场完整单 POV 样本，不设定值 | USER | ZIP计划 §I04; 32场原作输入身份 | 不私设长度/请求次数/预算 | plan | 规模与创作约束 | PENDING |
| P-I04-04 | NK 原版输出实际进入样本链 | UPSTREAM | NK @ `b857f34b7d371ae82c30e00eb021884c14d08ae9`: route blob `d3ec1181cd94553126673e515bfe24ce611f6511`; ZIP计划 §I04 | 保留实际输入输出链及 hash | plan/evidence | 功能因果证据 | PENDING |
| P-I04-05 | CritiCS 使用原算法与流程 | UPSTREAM | CritiCS @ `fbf66cbc913012c6f80af1687e27f0ce350475e3`: README blob `c809dd5f6dcc86723463db112da047fc85a6a656`; plan §I04 | 不手写替代批评器 | plan | 方法真实性 | PENDING |
| P-I04-06 | 保存原始调用、用量、上下文并保留首次失败 | USER | ZIP计划 §I04; GOV §03/B08 | 私有保存，公开仅脱敏索引 | plan | 成本与证据链 | PENDING |
| P-I04-07 | 用户读前停止，不自动扩量 | USER | ZIP计划 §I04; 明示用户亲读最终质量 | 设置 `CONTROLLER_REVIEW_REQUIRED` | plan | 最终质量权限 | PENDING |
| P-I05-01 | 公开 Git 不提交原稿/Key/完整响应 | USER | ZIP计划 §B、§I05; GOV §06 | 只提交自有治理与脱敏索引 | plan | 隐私/版权 | PENDING |
| P-I05-02 | Reviewer/Controller按精确 C/T 与远端签收 | USER | ZIP计划 §I05; 新 G00委托规则 | 逐 Atom 独立签收 | plan | 身份与阶段门 | PENDING |
| P-I05-03 | 最终创作效果由用户本人阅读裁定 | USER | ZIP计划 §I05; G00 GOVERNANCE §07 | 工程状态不得冒签 | plan | 保留用户最高质量权 | PENDING |
| P-D-01 | 检查远端空树与本地状态 | USER | ZIP计划 §D第1行/G00 | 每 Atom现场读取 | plan | 防覆盖 | PENDING |
| P-D-02 | 只用有效 MVP 活动治理分支 | USER | ZIP计划 §D第2行/A1 | 机制参考，不搬业务条款 | plan | 授权边界 | PENDING |
| P-D-03 | 固定三个上游版本 | USER | ZIP计划 §D第3行/A1 | 任何变更重新签收 | plan | 可复现 | PENDING |
| P-D-04 | CNW 仅按人工流程操作 | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: workflow README blob `afe16e553bef171f551c4f82c43a14f86c0aad71`, L3 | 禁止造第二套 agent 工作流 | plan | 流程一致性 | PENDING |
| P-D-05 | NK Flash 兼容性必须离线核实 | USER | ZIP计划 §D第5行/I01; NK route blob `d3ec1181cd94553126673e515bfe24ce611f6511` L256–258 | 未验证不调用 | plan | 模型边界 | PENDING |
| P-D-06 | CritiCS 可解析性需要实际实证 | USER | ZIP计划 §D第6行/I01; CritiCS blob `848802dae2fcd2cf29769dc06b539f106ca1b8af` L43 | 不把文本异常写为运行失败事实 | plan | 失败归因 | PENDING |
| P-D-07 | 未证明三工具完整调用前不宣称全栈 | USER | ZIP计划 §D第7行/I04 | 限定结论强度 | plan | 功能真实 | PENDING |
| P-D-08 | ZIP 未定位前不声称在 Downloads | USER | ZIP计划 §D第8行/I02 | 只记录未观察 | plan | 输入身份 | PENDING |
| P-D-09 | 一场样本不代表全篇质量 | USER | ZIP计划 §D第9行/I04 | 结论局限明示 | plan | 防泛化结论 | PENDING |
| P-D-10 | 遵守 CNW 作品材料版权范围 | UPSTREAM | CNW @ `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`: `LICENSE` blob `e900c48410bda2c2eb5a3d780d3c8ffc6e6d12ca`; README blob `0e70b25492c0a43c94814a34a6b2f3a997fc2f32` | 不公开复制示例小说 | plan | 许可边界 | PENDING |
| P-D-11 | 不虚构无预算硬封顶能力 | USER | ZIP计划 §D第11行、§I04 | 不制定未授权美元限额 | plan | 费用真实性 | PENDING |
| P-D-12 | 用户阅读判断不能被工程 PASS 替代 | USER | ZIP计划 §D第12行/I05；GOV §07 | 创作效果保留用户签收 | plan | 质量权限 | PENDING |
| P-D-13 | 所有未核实项标事实状态 | USER | ZIP计划 §D/§E | NOT_VERIFIED/NOT_RUN 明确区分 | plan | 证据质量 | PENDING |
| P-E-01 | 报告 main SHA/tree | USER | ZIP计划 §E第1–2字段 | 不沿用旧值冒充现场 | plan | 远端身份 | PENDING |
| P-E-02 | 报告本地 HEAD/工作区/当前 Atom | USER | ZIP计划 §E字段3–6 | 每次现场记录 | plan | 状态可复现 | PENDING |
| P-E-03 | 报告前一 Atom真实接受与 upstream pins | USER | ZIP计划 §E字段7–10 | 引用真实消息与版本 | plan | 阶段链 | PENDING |
| P-E-04 | 报告模型请求/返回/用量 | USER | ZIP计划 §E字段11–13 | 未调用写 NOT_RUN | plan | 防想象账单 | PENDING |
| P-E-05 | 报告 Downloads 与 Release hash | USER | ZIP计划 §E字段14–15 | 未查写 NOT_RUN | plan | 源稿身份 | PENDING |
| P-E-06 | 报告 NK/CritiCS 兼容状态 | USER | ZIP计划 §E字段16–19 | 只写实测证据 | plan | 工具真实性 | PENDING |
| P-E-07 | 报告样本、审查和创作效果身份 | USER | ZIP计划 §E字段20–26 | 用户亲读前不接受效果 | plan | 验收身份 | PENDING |
| P-E-08 | 报告黑名单及下一阶段锁状态 | USER | ZIP计划 §E字段27–28 | 只有 Controller 精确接受后解锁 | plan | 防止自动越阶段 | PENDING |

## 原始证据索引

- 包原文与清单留在 Downloads；计划副本仅在本次临时审阅目录读入，包未改动。包 SHA 与计划 SHA 如本文件首段。
- Git 源 commit/tree/blob 清单可通过固定对象 ID直接复查；未在项目内复制任何第三方文件。
- 官方动态模型事实：DeepSeek [首次调用文档](https://api-docs.deepseek.com/zh-cn/) 与 [更新日志](https://api-docs.deepseek.com/zh-cn/updates/) 在 2026-10-10 查询；版本与价格可能变化，不构成请求或报价授权。
- Controller 审核：待审，不能以本表 PENDING 冒充 ACCEPT。
