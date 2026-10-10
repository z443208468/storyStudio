# P2 阶段签收记录

本文件只记录 Controller 的真实消息。P1 内容仅为历史事实，不代替 P2 签收。平台未提供消息 ID/精确发送时间的项目不伪造。

## P1 历史签收

### G00

- Original governance candidate：C=`b2d18951a101bd0e7c138965bb562e1bd430ab36`，T=`25507793dfea15630ecb57b1cd8ddfe9077a3535`。
- Delegation amendment：C=`02f466d8bec68ee4df9a0eeb0f2c9722334552dd`，T=`597aad4f54feb93ededb3220fb07f353c1ffb498`；同一只读 Controller 曾对本地与远端回读接受。
- 用户委任原话：`我让你组立出来这个这个用做验收的智能体，它就是控制器。`

### G01

- Verdict：`REMOTE_READBACK ACCEPT`
- Candidate：C=`046365ef7e61ffc913a704e3a2e40abcd41fd28a`，T=`a386a981d754bacf1fc9e697daf4b33d2eb88570`
- Controller 原消息摘要：远端候选 C/T 与已审本地身份一致；main C=`06c66de7c7f18263039ea19a47e84c29716cde4b`、tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`；依据 Writer 提供的原始 `ls-remote`/`fetch` 输出，Controller 未独立 fetch。

### I00

- Verdict：`REMOTE_READBACK ACCEPT`
- Candidate：C=`47394d3432fe8b8fe0c0d52edba50c602099e9af`，T=`45e2e70d49aa5304d029818707f8836792deb9bb`
- Controller 原消息摘要：远端分支 commit/tree 与本地已审候选一致；main 身份及三个 submodule SHA 与 Writer 回读相符。

### I01

- Verdict：`REMOTE_READBACK ACCEPT`，接受的是阻塞事实记录，不是兼容性通过。
- Candidate：C=`2586d378669b74d4fc9e4460aa80f2cd8a908038`，T=`5b14e80075811f76f4a1bec10da00b0725bddd69`
- Blocker：`B11 / BLOCKED_UPSTREAM_IMMUTABLE`；CritiCS 固定文件在 Python 3.13.2 的 `py_compile` 第 43 行失败。原始 raw log SHA256 `3E5E4B0FA7360AD4C793406D0FAF3E1E6062CCD21D0BA40CB1EED273A8ADCBBA`。
- Controller 原消息：`I01 的终态是已接受的 B11 / BLOCKED_UPSTREAM_IMMUTABLE，不是兼容通过。I02 仍锁定，因计划明文要求 I01 未遇不可解除阻塞。` 后续用户指定的 P2 包替换旧活动计划并允许修复；该历史阻塞仍作为修复前事实。

## P2-00

- Verdict：`REMOTE_READBACK ACCEPT`（local candidate 与 remote readback 均接受）。
- Candidate：C=`cb7020a3cca0e1f84ebe72120b7e262d4d7cb8b6`，T=`5b2d9607eb9639521ee5bbbda7439892cab94dbb`。
- Main C=`06c66de7c7f18263039ea19a47e84c29716cde4b`，empty tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`；remote candidate C/T 与本地一致。
- Controller：同一用户委任的只读验收子智能体 `/root/g00_reviewer`。精确远端消息摘要：`P2-00 接受。候选分支 C 与 fetch 候选一致，tree 为 5b2d9607eb9639521ee5bbbda7439892cab94dbb；main C 为 06c66de7c7f18263039ea19a47e84c29716cde4b，empty tree 为 4b825dc642cb6eb9a060e54bf8d69288fbee4904。` 该阶段后 P2-01/02/03 解锁。

## P2-01

- Verdict：`REMOTE_READBACK ACCEPT`（local candidate 与 remote readback 均接受）。
- Candidate：C=`675d2b6b26ccbb9bd913cc435266748769a7a918`，T=`a6c8b171c760391e6bee4a72fd0868d90d53062d`。
- Main：C=`06c66de7c7f18263039ea19a47e84c29716cde4b`。
- Source identity：版本 `JUN-SINGLE-02.3`；ZIP SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`。
- Controller：`/root/g00_reviewer`；该阶段已完成，不在 P2-02 重复验收。

## P2-02

- Verdict：`REMOTE_READBACK ACCEPT`。
- Candidate：C=`591b979734981fc30a3a3c011cce8aa622239a8c`，T=`3de19929b54cea86d9a3aef159884b3087a1a493`。
- Main：C=`06c66de7c7f18263039ea19a47e84c29716cde4b`，empty tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`。
- Controller：`/root/g00_reviewer`；local ACCEPT 后 remote readback ACCEPT。修复过的 bridge output symlink finding 与实际执行的离线 symlink 用例已包含在此候选中。

## P2-03

- Verdict：`REMOTE_READBACK ACCEPT`（Controller local ACCEPT 后远端回读一致）。
- Candidate：C=`bbdfbc6b477e0c800a2b7bd02cf6a181b880a266`，T=`5a7128f437713a03e730d95a4a40a78b51891baf`。
- Source commit/tree：`b857f34b7d371ae82c30e00eb021884c14d08ae9` / `3960b25cb52265933e0fa4897d1319ad6161bf9c`；archive SHA256：`921B92480300FC2EDF484108E936E01BC97D938A28A17829F90133CE28A9E9C6`。
- Patch SHA256：`F468219F2A0BC8D9D5205DEF48D245896CD1DF19D84FD9BA5C4DBB141C06963E`; manifest SHA256 `249BF34AA2B53701832B2BFC760797E365841A6CB2FEF42440AA1FC9CF62DAE5`; lock SHA256：`8D6EF80B3161DDDA089DF6EB83AB986326370E9F0F97041E516DD478A0C8E9A4`; runtime build：`p2-03-b857f34b-f468219f2a0b-8d6ef80b3161`。
- Build and ordinary `npm start` offline HTTP evidence passed. Both normal start instances bound loopback; 8 no-key routes returned 401; mock/invalid-result cases matched contract; 0 external provider calls.
- Controller `/root/g00_reviewer` local ACCEPT and remote readback ACCEPT; remote candidate C/T matched.

## P2-04

- Status：三条真实调用链均已跑通；Controller 限定复核 ACCEPT（只接受两项证据纠偏，不重复签收其他要件）。
- Live run：`runs/p2-04-live-20261010/`；汇总：`evidence/p2-04-live-check.json`；跨 run 费用账本：`runtime/private/p2-cost-ledger.json`（本地私有）。
- Plain text：DeepSeek Flash 请求成功；NK `generate-perspective`：真实 HTTP 200、Zod 接收 1 项；CritiCS `chatsettubg` / `ConversationChain`：真实调用成功且 memory 有 2 条消息。
- NK 首次真实返回被 Zod 拒绝，根因是模型返回的顶层 JSON 键与 schema 不同。已明确 prompt schema，设置 `reasoning_effort=none` 并限输出 512 tokens；仅重跑 NK 调用后通过。原始错误调用仍按实际 usage 计费并保留。
- 真实联调还确认 8 条生成路由中 reasoning 参数先前均未落实；现已全部设置 `reasoningEffort: none`，离线验收确认八条路由，`npm start` 的 loopback/no-key 检查、响应边界和 provider 参数均通过。此修正的 current patch SHA256 `289D6E5CA63C3B45D7BC2697A095E0344033482B0F5512E679E6ABF3A2E355B1`，runtime build `p2-03-b857f34b-289d6e5ca63c-8d6ef80b3161`。
- 当前累计估算费用 `¥0.004892 / ¥10`；估算采用当日官方峰值价、输入按 cache miss，并按 USD/CNY 6.70 换算。缺失 usage 的规则为 UNKNOWN_NOT_ZERO 并保留 reservation。未发送项目源稿。
- 证据补充：首次 CritiCS 成功调用的 ledger 行 `critics-b6f3d53fcae34ffa8d7a578cc67140e9` 记录 71/7 tokens 与估算 `¥0.000199`，但供应商 request ID 未捕获；原始响应文件被后续有 ID 的仪表化调用覆盖。该请求已单独列入五笔供应商调用及总费用，并以 `runs/p2-04-live-20261010/critics-b6f3d53fcae34ffa8d7a578cc67140e9-reconciliation.json` 明示限制；不臆造 ID 或响应体。CritiCS 探针现按本地 request ID 分文件，避免覆盖。NK provider 失败响应记录已重新校验为有效 JSON，并确认不含 `reasoning_content` 字段。
- Controller 复核候选 C=`816fed0a299fcd99473725486119691f070bc64e`，T=`b2a3131fc8ceedce1cd74a8a4de77e7f79642992`；限定 ACCEPT。



## P2-05

- Status：单场 CNW Plot 草案已由 DeepSeek Flash 生成；首轮 RETURN 修正后，Controller 对插入边界限定复核 ACCEPT。
- 合同：`workspace/cangqi/sample_contract.json`；源锚：`workspace/cangqi/06_plot/ep001_source_anchors.md`；Plot：`workspace/cangqi/06_plot/ep001_plot.v0.md`。
- 插入窗口：J19 释放行动后、J20 任一路线开始前；单场连续讲堂空间。新增细节均标记为候选，未写回 Canon；保持知识与路线状态。
- 真实调用：`runs/p2-05-live-20261010/`；provider request `02ed6533-354f-432d-8bd7-25a1774f4122`，DeepSeek Flash，finish=stop，3142/955 tokens，估算 `¥0.013994`。全 campaign 六笔真实 provider 请求估算 `¥0.018886/¥10`；其中 P2-04 五笔事实保持原记录。无项目 Key 写入证据。
- 脱敏/私有证据清单：`evidence/p2-05-plot-check.json`；其记录的六项产物哈希已核对。
- 首轮 RETURN：J19 第559行仍允许即时坦白，首版锚点截断在第557行。修正后精确插点为第555行对白之后、玩法开启（557）之前；场景后原样恢复 J19 玩法与坦白选项，再继续 J20。修正说明与补齐的私有源锚已加入 hash 清单；没有重发模型请求。
- 插入边界复核候选 C=`cc30e9d7b7a3966a71279e6dfb5eb9c3905067b0`，T=`645fb4ba8c174f18866e6c5fff39975a86a999f6`；限定 ACCEPT（只接受 J19/J20 连续性纠偏）。
- 阶段验收最终纳入候选 C=`ef76fb329a10e22284de9701b94cb99d690b19bb`、T=`91ceb9b822815e824d358a5fff82e14137efe3f5`；此候选经最终本地 ACCEPT 与远端 `REMOTE_READBACK ACCEPT`。当前关闭记录见 P2-07。


## P2-06 — Plot Gate（阶段中间门）

- Status：Controller 已限定 ACCEPT P2-06 Plot Gate；现在继续生成 Scene Card。**P2-06 全链验收尚未完成。**
- 原生结果/过滤记录：私有目录 `runs/p2-06-critique-20261010-02/` 与 `runs/p2-06-plan-revise-20261010/`；`modifiedStoryline` raw 输出未覆盖。违反单场/Canonical 边界的追加场景、旧书案设定、未经锚定的外部声响、读心解释均明确拒绝。只采纳了可见动作差异，理由见私有 `plot-filtering-record.md`。
- 当前 Plot：私有 `workspace/cangqi/06_plot/ep001_plot.v1.md`；严格一场，J19 第555行后、玩法开启前，结束后恢复 J19 即时坦白选择与 J20 原流程。
- 该子阶段六次真实 DeepSeek 请求均有 ID、stop、usage 与估算；该子阶段 `¥0.077503`。累计 campaign 12 笔真实 provider 请求、14 ledger 行，估算 `¥0.096389 / ¥10`；两次零调用服务器启动与一次 P2-06 导入失败均不冒充真实请求。
- 逐调用私有原始请求/响应在各 run 的 `provider-calls.json`；reasoning 字段被剥除；源稿和提示不进入公开 Git。当前阶段 evidence/hash：`evidence/p2-06-plot-check.json`。
- Plot Gate candidate C=`05a08ba10cf416b06121a2a365b784b92a33c6f5`，T=`13c6e2ff1a5cfda98d2bdda065c792c6d53e6d5e`；限定 ACCEPT，开放 Scene Card 阶段，不等同于 P2-06 全阶段 ACCEPT。

## P2-06 — 全链生产与修订（阶段内容 ACCEPT）

- Verdict：`ACCEPT`（Controller `/root/g00_reviewer`）；接受 Plot Gate、Scene Card/NK 检查点，并在全文核对 v0→v1、修订计划及前后锚后签收 P2-06 内容。此为工程/内容边界验收，不代签用户创作满意度。
- 实际产物：私有 `workspace/cangqi/05_scene_cards/ep001_scene_cards.md`、`07_draft/ep001_writing_brief.md`、完整 v0 `07_draft/ep001_v0.md`、`08_review/ep001_refinement_triage.md`、CNW 计划/日志与 `09_revision/ep001_v1.md`。Controller 确认一场连续动作、君天离限制 POV、J19:555 后插入并恢复 J19:557/559 与原 J20 路由。
- NK → Brief：真实 `/api/generate-perspective` 成功，provider ID `232f4613-855a-4199-a91a-f9bfdae3e8b3`；HTTP 200，604/53 tokens，估算 ¥0.001641。Reflection 只作为观察范围素材。
- CritiCS：Plot Gate 五个原生批评调用 + `modifiedStoryline()` 一次，估算 ¥0.077503；`Refinement.Two_refinement()` 实际三次原生 Image/Voice/Leader 调用，只审连续三句摘录，不声称全文审读。完整 v0 至 v1 经 Flash 同场修订，v1 删去未列入卡片的附加物件/动作。
- 本阶段总真实 provider 请求 12 次。累计账本 17 次真实请求、21 条记录，估算 ¥0.123297 / ¥10；usage 总计 25,018 输入 / 9,055 输出 tokens。明细和私有 SHA-256：`evidence/p2-06-execution.json`。
- 三项不计费失败均明示：未装载锁定依赖的初次 CritiCS 导入、首次 NK schema 不匹配（HTTP 400、未到 provider）、预建 run 目录造成的本地路径冲突；均已修复并在不同 run 完成对应阶段。
- 本地 Controller 内容 ACCEPT 已完成；完整阶段产物纳入 P2-07 最终候选 C=`ef76fb329a10e22284de9701b94cb99d690b19bb`、T=`91ceb9b822815e824d358a5fff82e14137efe3f5`，并随该候选通过本地 ACCEPT 与远端 readback。

## P2-07 — 阅读交付与可复用入口（中间状态，已由下方最终记录取代）

- 当前私有阅读包：`deliverables/EP001/`，含初稿/修订稿 Markdown+TXT、前后文连读 Markdown/TXT/离线 HTML、修改说明、本地使用说明、production preset 与文件 SHA-256 manifest。
- 统一入口：`tools/studio.ps1`。新 PowerShell `doctor → prepare → import-source → scene plot/draft/revise → resume → export` 均通过；读取锁定源/补丁/运行环境，已有生成步骤复用。P2-07 冷启动检查确认成本账本 SHA 不变。
- `nk-start`/`nk-stop` 使用精确 NK build、localhost loopback 并等候就绪；冷启动及停止成功，未产生 provider 请求。两次早期启动路径尝试在本机 npm 启动阶段失败，根因为工作目录未传递；已以 `npm --prefix` 和就绪检查修复。
- HTML 内嵌样式、无外部脚本/资源；私有 J20 分支细节、源稿和密钥未进入阅读导出或公共索引。交付状态为 `READY_FOR_USER_REVIEW`，不写 `USER_CREATIVE_ACCEPTED`。
- Controller 对 P2-07 本地交付、提交 C/T 与远端 readback 待验收。

## P2-07

- Verdict：`ACCEPT`（Controller `/root/g00_reviewer`，本地交付范围）。
- Controller 明确确认：入口脚本、交付文件及 manifest 文件哈希均与当前内容匹配；独立 PowerShell 回放覆盖只读定位、导出和 NK 生命周期；NK 启动到 `127.0.0.1:3175`、停止后无监听器；账本前后 SHA-256 一致且没有新增供应商调用。
- 交付 HTML 无外部资源；连读摘录只含指定 J19 前后锚，不展开 J20 分支正文。用户创意签收保持 pending。
- 证据：`evidence/p2-07-delivery.json`；私有回放与原始生命周期输出位于 `runs/p2-07-replay-20261010/`。
- 本地 ACCEPT 与远端 readback 均已完成：阶段候选 ef76fb3...91ceb9b... 获 Controller ACCEPT；包含本记录的关闭提交 `0b40876b2f90cfc88c700f5d651719fa214d58af` / `eb23c4b4a8e48bf966845e339ab6bfc62ed88b98` 亦获独立 `REMOTE_READBACK ACCEPT`。Writer 与 Controller fetch 及 ls-remote 一致，工作树干净。
- 最终候选：branch `codex/g00-governance-candidate`，C=`ef76fb329a10e22284de9701b94cb99d690b19bb`，T=`91ceb9b822815e824d358a5fff82e14137efe3f5`；main C=`06c66de7c7f18263039ea19a47e84c29716cde4b`，tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`。
- Controller `/root/g00_reviewer` 最终本地候选 ACCEPT；推送后独立 fetch 与 `ls-remote` 回读均为 `REMOTE_READBACK ACCEPT`，远端 C/T 与本地候选一致。
- P2-05 最终交付候选 C=`ef76fb329a10e22284de9701b94cb99d690b19bb`、T=`91ceb9b822815e824d358a5fff82e14137efe3f5` 通过 Controller 最终本地 ACCEPT 与远端 `REMOTE_READBACK ACCEPT`；同一候选包含 P2-06/P2-07 完整产物。

## P3 W02 — 活动治理与状态分离

- Verdict：`ACCEPT`，独立只读 Controller `/root/g00_reviewer`；审查范围仅限 W02。
- 候选：C=`c01713882900d630358c4681856ef6fb0158fb3d`，T=`dfdfb9bafe59af96a2e93a4893de99e01b180dca`；父提交为 W01 C=`d48a25627cfe604bc309cf0f6d9edfe56effa9cb`。
- Controller 原消息：W02 ACCEPT，确认七文件提交与已审工作树候选相同、P2 签收和计划全文保留，P3 状态分开记录，旧 EP001 明确为历史 smoke 样本；旧 `studio.ps1` 恢复/checkpoint 命令仍可用。该 ACCEPT 尚待正常推送和远端回读。

## P3 W03 — 源身份与场景预算合同（零 API）

- Verdict：`ACCEPT`，独立只读 Controller `/root/g00_reviewer`；接受仅限合同/validator 与预生成文学合同预审，不等于正文生成或文学成品接受。
- 候选：C=`249283f864056fcdd13c60956710feaaa794c30b`，T=`76d5a8d2a7277dc9b8823312515ba924ef0e832d`；私有合同 SHA256=`e5ef4ce8d4468756021b8b7a8e10dd3cff0b9445e25a6a399f3cc683bb0978d0`。
- Controller 独立确认《苍歧》source_manifest SHA256=`D3A15ECB58D1ECB01CDB7B97054A274773B146ED46B10E72F05F8EA3117233CF`，CNW 捕获 manifest 另记为 `E9B989C52C66AB9BE8C73F09E84BC5BD7D2ECC92F9F1CBFC61BA300DC6CD3983`；生产脚本与 J19 前后锚哈希相符。初轮 RETURN 指出两种 manifest 身份混用；已改为分别记录，并让 validator 对实际 source_manifest 文件做 SHA 验证。
- 场景合同：J19 555 后至原 557/559 之前；从原文可见的沉默/未说完开口发展成一次短暂、可见的交谈尝试，不揭示分支内容、不决定玩家选项。目标 1500、范围 1200–1800；4 个动作/对白节拍分配 300+400+500+300。Controller 认为来源、知识边界与规模建议合理，并明确不代表授权生成。
- 离线结果：`tests.test_cnw_contract` 6 项通过；覆盖缺失/0 目标、Episode 分场预算、120 字短稿 `RETURN_UNDERPRODUCED`、必需节拍证据、Markdown/NFC 可见字符、source manifest/脚本/锚身份与 manifest 篡改拒绝；`py_compile` 和真实私有源预检通过。无供应商请求。
- Controller 原消息：`ACCEPT — P3 W03`，精确绑定上述 C/T；确认合同 SHA、source manifest、policy、脚本和前后锚哈希相符，事件目标及 1500 / 1200–1800 预生成范围有充分依据；“No generation is authorized by this acceptance.”
- 远端回读：候选提交接受后正常推送，等待记录。
