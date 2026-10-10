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
- 最终带验收记录的提交与远端 readback：推送后追加。
