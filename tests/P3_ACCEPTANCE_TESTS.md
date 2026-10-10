# P3 验收矩阵：必须由功能事实判定，不允许表格/Exit 0 假完成

这些是执行后**必须真实运行**的测试合同。命令中 `cnw_runner.py`、`test_cnw_pipeline.py` 等为**需实现的目标入口**，并不声称截至 P2 已存在。原始工程/模型调用的成功记录照旧保留；新功能的验证必须在新 run 上做。

## A. 来源、治理、兼容性：零付费

| ID | 动作 / 反例 | 必须满足的实际断言 |
|---|---|---|
| A01 | 从本地 pinned submodule 跑 `capture_cnw_reference.py` | Commit 必须是 `97ad71f...`，所选择资料逐文件 git blob = pin，复制 SHA256 一致，完整 manifest 存私有 ignored 目录，原子模块 tracked status 不变 |
| A02 | 将原作者参考原文改动一字节再跑提取器（在隔离 fixture 模拟，**不得改真实 Vendor**） | 明确 `UPSTREAM_SOURCE_BYTES_CHANGED` 或 `EXISTING_REFERENCE_COLLISION`，不默默覆盖、不卡虚假 PASS |
| A03 | 对 `main` 与本地工作树作状态比对 | 当前 local HEAD、未提交 WIP、远端 main、三个 Vendor pins 都如实记录；已存在的正确进展复用，不强制 reset/clean |
| A04 | 按《原作者资料》抽样检查每条方法映射 | 每个环节精确 source path/源 blob/现有或新函数/真实产物/验收，不允许把 CritiCS Inspector 改名成 CNW Verifier |
| A05 | `legacy` 入口不改已修好的 NK 服务 | 既有 `nk-start/nk-stop/prepare` 在隔离非付费检查结果不退化，无端口残留 |

## B. 生产合同与新 ID：零付费

| ID | 动作 / 反例 | 必须满足的实际断言 |
|---|---|---|
| B01 | 两个 fixture 合同：`FICT_SCENE_A` 与 `FICT_SCENE_B`，不同 source、长度目标和锚 | 生成两个**不同** run 目录、Plot/Card/Brief/产量合同，不读取/重命名已有 EP001；任何产物有输入 hash 和来源 |
| B02 | 两份同 ID 不同 contract 内容运行 | 前一结果因 source/contract hash 改变而 invalidated；旧 run 保留，禁止静默覆盖 |
| B03 | `target_visible_chars` 为 null/0/未给 | `PREFLIGHT_TARGET_MISSING`，不向供应商发起请求 |
| B04 | Episode 3 Scene：各 Scene 设预算 900、1100、1200 | Plot、Cards、Brief 目标分量合计 = 3200，角色/场次边界可追溯；若加总不等于 Episode，阻断 |
| B05 | Card 缺 start/end state、required beat、forbidden 或来源身份 | 预审 RETURN，不通过只因卡片字数足够 |
| B06 | Prose Agent 输入捕获 | 只包含 Brief + 参与角色声音材料，不含完整隐秘后文或被禁止披露的 Canon 原句；只输出 markdown 正文 |
| B07 | `studio.ps1 produce --unit scene --contract ...` | 触发新生成驱动，而非 `CHECKPOINT_REUSED`；`studio.ps1 legacy-*` 仍可读取旧 EP001 而不作新请求 |
| B08 | `verify-history`/`verify-live` | 前者只能返回 `HISTORICAL_EVIDENCE_FOUND`，不能返回 `NEW_PROVIDER_CALL_PASSED`；后者必须有本 run provider ID/usage/raw hash，缺少立即失败 |

## C. 正文规模和质量：离线正反例

| ID | 动作 / 反例 | 必须满足的实际断言 |
|---|---|---|
| C01 | 合同目标 1000 / 范围 700–1400，模拟返回正文 120 个可见中文字符 | `RETURN_UNDERPRODUCED`；不得用 `finish_reason=stop` 和 HTTP 200 替代文学完成 |
| C02 | 返回 900 可见字符，缺 `B02` 的人物行动与回应 | `RETURN_MISSING_BEAT`，不能靠长度和情绪词过关 |
| C03 | Scene B01、B02、B03 位置齐备但没有任何对话/行动变化 | Story-specific/Plot Lens 返回具体可定位缺陷，判 `revise` 或 `rewrite` |
| C04 | `v0` 约 1000 字、`v1` 约 150 字且删掉关键动作 | `REVISION_REGRESSION` 和 `RETURN_UNDERPRODUCED`，不能被其“没有新 Canon”覆盖 |
| C05 | 真正删掉重复段落但 v1 仍满足分量和 beat | 可通过，不为了凑字数恢复废话；保存 revision diff 与理由 |
| C06 | 传入 5 Scene 的 Episode，模型输出第 3 Scene 后结束 | `TRUNCATED_OR_UNFINISHED`，对缺的分场有限续写/再审，不给整话 PASS |
| C07 | 当前项目实际声音/称谓样本的一个反例 | Character Lens 能指出谁说错、哪句话、与哪个 source 冲突；不凭作者小说角色语气判断 |
| C08 | POV 主角提前说出源稿尚未知秘密的负例 | Canon Lens 拦截并指明前后文知识边界；用户/Controller 不得靠“写得漂亮”将其放过 |
| C09 | 故意加入镜头语言、UI 标签或编辑指令 | L1/L2 能抓正文中的遗留标记；不会把原文合法情绪词自动删掉 |
| C10 | Unicode NFC、空行/Markdown 标记、中文标点输入 | visible chars 与 markdown 文件 bytes 明确分离；报告字符、汉字、对白/叙述段落及长度算法 |

## D. 独立审稿与修订：离线模拟 + 最小 Live 证明

| ID | 动作 / 反例 | 必须满足的实际断言 |
|---|---|---|
| D01 | 给 5 Lens 输入同一 Draft 和各自来源 | 产生 5 份独立真实数据记录，`input_sha` 一致或按岗位不同，互不读取其他 Lens 发现；没有伪造 API ID |
| D02 | 离线检查五 Lens 对不同缺陷的探测 | Style: 冗余；Character: 错称呼；Plot: beat 缺失；Canon: 提前知情；Story-specific: 无读者体验；每项支持具体文本位置 |
| D03 | 一个 finding 三票 `[not_refuted,not_refuted,refuted]` | 2 票确认后保留；`[not_refuted,refuted,refuted]` 不保留；`uncertain` 按优先 refute 的上游策略处理 |
| D04 | 让 CritiCS 返回故事批评结果 | 仍由原桥接实现，但结果**不得**被写入假的 `lens_*.json` 或抵销 5 Lens |
| D05 | 故意遗漏“场景完成度”这个检查维度 | Completeness Critic 提出遗漏问题并转到受审问题队列；不直接修改正文 |
| D06 | Revision P0 与 P2 有冲突 | P0 优先，保护已确定 Canon；每个问题可追踪 `issue_id→修订→复核`，不得全稿盲改 |
| D07 | Revision 只改了一场对话 | 定点重审 Character/Style/受影响 Plot/Canon；不重跑未变的上游 NK/剧情批评，保持依赖身份正确 |
| D08 | v1 合格时 `promote` | 原正本归档，最终章正本写 `07_draft/episodes/<unit>.md`，索引更新，原 v0/v1 保留，签收指向精确 SHA |
| D09 | Reviewer 说评分 90，却有致命漏 beat | **阻止 PASS**，Controller 必须 Return 具体缺口；分数不是 fatal override |
| D10 | 让三份 verifier 内容复制粘贴同一返回 | 单一相同内容不自动证明“独立判断”，真实 provider request 身份及无共享上下文要通过；离线可测试伪同 request ID 被拒绝 |

## E. 产品完整性与费用/安全

| ID | 动作 / 反例 | 必须满足的实际断言 |
|---|---|---|
| E01 | 在无 Key 新 PowerShell 运行 `doctor, prepare, capture-reference, offline fixtures, resume, export` | 全部非付费路线可执行；不读取秘密；零新增供应商请求 |
| E02 | 5 条虚构章节合同跑 Sprint 离线代理 | 五话队列、每章索引、batch-review JSON 和 carry-forward 能生成；**不要求真实生成5话《苍歧》** |
| E03 | 未获预算预留、usage 缺失/超预算 | 拒绝网络或保留费用预留，不能把未结算算 0；现有 10 元总护栏不被重置 |
| E04 | 重新 `resume` 已成功真实调用的阶段 | 复用相同 input/config/output hash；真实供应商调用次数不增 |
| E05 | 在新 run 只改 Prompt/Canon 内容 | 只让真实受影响的节点及消费者缓存失效；不得因导出文字变更重跑前序付费调用 |
| E06 | 操作系统 symlink/`..`/绝对路径/同 ID 并发 | 防止越出私有目录、防止覆盖、拒绝临时目录重名和多进程错账，不再扩大为通用平台 |
| E07 | 导出一个不是 EP001、不是 J19 的虚构 Scene | HTML/MD/TXT 中**没有**“思柔/书案腾空/J19:555”历史硬编码；仅用新 input manifest 的锚点和人物 |
| E08 | git diff staged 扫描 | 源稿、作者示例小说正文、API key、原始请求、真实私有文本不提交 Git；公开仓只见源码、hash、脱敏签收 |
| E09 | 同一获批准 J19 插戏重产（唯一允许真实新作品） | 至少一个新 run 的新请求、完整篇幅、正确 CNW 阶段 11 步、NK/CritiCS 实际消费、revision 与 re-review、费用对账及新阅读包 |
| E10 | Controller 判 `REAL_PRODUCTION_READY` | 上述独立功能和内容 gate 通过，实际可以新 ID 生产且工程入口可复用。`USER_CREATIVE_ACCEPTED` 仅人类用户亲读后赋值，不从 Controller 推导 |

## F. 必须提交给 Controller 的一份简明验收记录

```text
ATOM=<Wxx>
SOURCE_PIN=CNW@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
LOCAL_REFERENCE_MANIFEST_SHA256=<REAL>
CURRENT_STORY_CODE_C=<REAL>
CURRENT_STORY_CODE_T=<REAL>
CODE_DIFF=<PATHS_AND_CLASSIFICATION>
OFFLINE_TESTS=<IDs_AND_ACTUAL_RESULTS>
LIVE_TESTS=<ID, MODEL, COST, OUTPUT_HASH OR NOT_RUN>
PRIVATE_ARTIFACT_MANIFEST_SHA256=<REAL_OR_NOT_RUN>
QUALITY_GATE=<WHAT_WAS_ACTUALLY_CHECKED>
REVIEWER_VERDICT=ACCEPT|RETURN|BLOCKED
NEXT_DEPENDENCY=<NEXT_ALLOWED_ATOM>
```

审查拒绝必须给**文件/函数/失败测试/应实现的行为**，同一 Atom 修复后只跑受影响的测试；不通过“加新的命名要求、换结构样式、再创验收框架”拖延作品。文本审查已发现实际欠产量、没戏或严重人物偏差时，也不能为了加速而放弃必要文学返工。
