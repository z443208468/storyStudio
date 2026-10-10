# StoryStudio 空仓库重建执行总计划 P1（治理先行，原版零修改）

> **状态：G01 候选，尚未生效。** 本文件只能在治理修订 G00 `02f466d8bec68ee4df9a0eeb0f2c9722334552dd` / tree `597aad4f54feb93ededb3220fb07f353c1ffb498` 的基础上提交、独立审查并由当前 Controller 对精确提交和树接受后成为活动计划。Controller 委托来自用户明确消息，记录于根 `AGENTS.md`。未接受前，I00 及后续所有阶段均锁定。
> 对应治理：`AGENTS.md`、`docs/governance/GOVERNANCE.md`、`docs/governance/PLAN_AUTHORING_STANDARD.md`。任一 B01–B14 = 阻塞；不准另换流程自救。**所有第三方原版 Git 跟踪字节永远只读。**

## A. 范围、来源和已核事实

### A1. 权威来源与版本

| 源 | 本轮固定身份 / 观察结果 | 行动性质 |
|---|---|---|
| StoryStudio 空仓库 | `z443208468/storyStudio` `main`=`06c66de7c7f18263039ea19a47e84c29716cde4b`；此前记录 tree=`4b825dc642cb6eb9a060e54bf8d69288fbee4904`。本次 G00 修订远端 readback 只含 main SHA，不含 tree；故本轮 main tree=`NOT_VERIFIED`。当前执行分支 G00 委托修订 C=`02f466d8bec68ee4df9a0eeb0f2c9722334552dd`，T=`597aad4f54feb93ededb3220fb07f353c1ffb498`。| 远端 commit 为本轮 `FACT`；tree 为历史参考，待下一现场核实；本地状态按每 Atom 现场读。|
| MVP 治理参考 | `z443208468/mvp` 活动分支 `perf/r667-migration-20261008` C=`2f3d6f9af77a784aa92369cbb224e2cc9cc9a02b`，tree=`d4ab7ddbd15d69fde4a366f4bd7995f1bd4ab065`。仅参考机制，不移植其业务合同。| 只读参考。|
| CNW 原版流程 | `MintoTsukino/claude-novel-workflow` C=`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`，tree=`f06a7b693fda124761b69ad40ab483cc82960219`。| 原版文档、模板、许可证，零修改。|
| NK 原版工具 | `zhangchaodesign/narrative-keyframing` C=`b857f34b7d371ae82c30e00eb021884c14d08ae9`，tree=`3960b25cb52265933e0fa4897d1319ad6161bf9c`。| 原版程序、配置、锁文件，零修改。|
| CritiCS 原版工具 | `EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation` C=`fbf66cbc913012c6f80af1687e27f0ce350475e3`，tree=`c48be7d9cbeb680238a9e832be86bdf167c305a9`。| 原版程序、配置、依赖清单，零修改。|
| 2.3 源稿 | 已有身份记录 SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`，版本名 `JUN-SINGLE-02.3`。本阶段未读取 Downloads，也未声称该 ZIP 当前存在。| `REFERENCE_IDENTITY_ONLY`；须到 I02 按 Known Folder 搜索并哈希。|
| DeepSeek API | 2026-10-10 查阅官方文档：OpenAI 兼容 base URL 为 `https://api.deepseek.com`，模型字段 `deepseek-flash`；官方更新说明该名称当前调用 V4.1-Flash。价格与服务版本可变，本计划不固定价格。| 当日官方公开事实；真实凭据、请求、返回型号和用量仍 `NOT_RUN`。|

### A2. 已核兼容性事实与未验证项

1. **NK**：固定源码 `lib/openaiServer.ts` 第 4–10 行从请求头取 key 并调用 `createOpenAI({ apiKey })`；未在该函数显式设置 base URL。固定源码 `app/api/generate-perspective/route.ts` 第 256–258 行调用 `generateObject`、`ResponseSchema`，模型硬编码为 `openaiProvider("gpt-4.1")`。README 要求 OpenAI API Key。外置 base URL 是否可审计地注入、SDK 是否接受 DeepSeek 的模型和结构化输出，均 `NOT_VERIFIED`；不得由该代码或环境名称推定兼容，不得改变原 Prompt、schema、输入/输出语义或发真实 GPT 创作请求。
2. **CritiCS**：固定 `critics/setting/chatsetting/gptsetting.py` 第 12、15 行默认 `gpt-3.5-turbo` 与 `gpt-3.5-turbo-instruct`；第 43 行文本为 `verbose=True                       s`，这是源文本异常，**本阶段未运行 Python 解析器，运行时语法结论 `NOT_VERIFIED`**。固定 `storygen/common/llm/llm.py` 在 OpenAI server 路径设置 `openai.api_base='https://api.openai.com/v1'`；`requirements.txt` 包含 `openai==0.28.0`、`vllm==0.1.7`、`ray==2.8.1` 等。实际解析、平台和 Flash 兼容性留 I01 原字节副本核验；绝不补字符、patch、monkeypatch 或重写原版。
3. **CNW**：固定 `templates/_workflows/README.md` 第 3 行称工作流不是 scripts，而是供人或 AI 手动执行的 prompts + procedures；同文件说明复制 Prompt 块并按 procedure 执行。它是作者文档规程，不是单击运行程序。Codex 只能读取原文按授权范围执行，不另造 Story Agent 或创作流程。
4. **许可证**：CNW README/LICENSE 区分文档/模板和受保留版权的示例故事内容；NK 与 CritiCS 固定版本采用 MIT。纳入上游时保留各自许可证，不把示例小说或用户原稿复制进公开 Git。
5. **模型名**：DeepSeek 官方入口目前仍列 `deepseek-flash`，当前服务版本为 V4.1-Flash；这只核实公开文档字段，不证明 NK/CritiCS 可以原样连接，也不授权任何 API 调用或费用。

### A3. 明确禁止事项

- 不执行旧 S00–S09、AT00–AT15；不恢复“六槽、二十四候选、首次批量多透镜×反驳者”等旧设计。
- 不修改任何 Vendor 源码、配置、Prompt、依赖锁或工作流字节；不在 runtime 副本中编写替代算法。
- 不把依赖安装/构建成功说成原工具已能创作；不把 API 200、工程评分或自写意见冒称作品效果或 CritiCS。
- 用户未读一场样本前，不扩为完整 Episode、第二场或批量生产；不私设 token/字数/调用数/预算，不用 GPT 或 Pro 作为创作后端。
- 任何候选计划条目未被 `reviews/PLAN_PROVENANCE_MATRIX.md` 归属为 `UPSTREAM`、`USER` 或受限 `ADAPTER`，即删除或标为待 Controller 裁决；该矩阵本身不授权扩大用户约束。

## B. 项目目录与数据所有权

```text
D:\CangqiStudio\StoryStudio\
  AGENTS.md
  docs/governance/GOVERNANCE.md
  docs/governance/PLAN_AUTHORING_STANDARD.md
  plans/MASTER_PLAN_FROM_EMPTY.md
  reviews/PLAN_PROVENANCE_MATRIX.md
  reviews/                         # 独立审查消息索引；Writer如实记录
  evidence/                        # 脱敏审计、Git与工具证据索引，不冒称raw
  .gitmodules                      # 仅G01接受后由I00增加
  third_party/                     # 三个只读精确版本子模块
  tools/                           # 只含项目自有校验、搬运或纯传输代码
  inputs/private/                  # Git忽略：用户ZIP及提取源稿
  workspace/                       # Git忽略：私有Canon、Plot、Card、Brief和样本
  runtime/                         # Git忽略：环境、构建镜像、缓存
  runs/                             # Git忽略：完整请求/响应、失败、证据
```

- CNW 许可只覆盖其声明的文档/模板等范围；示例小说、Plot、Card、Canon 等作品材料不因仓库可访问就获得复制许可。只引用原仓与路径核对结构。
- 子模块 checkout 只固定 Git link。需要生成构建文件时，将 `git archive` 的原字节放到 Git 忽略的独立 `runtime/build/<tool>/<run-id>/`；生产构建只在副本做。原 checkout 保持 pinned 且 clean，不能覆盖用户 WIP。
- 公开 Git 只放治理、source pins、许可归属、可复现命令与脱敏证据索引。用户原稿、Key、完整 Prompt/响应与正文留在私有目录。

## C. Atom 执行合同

### G00 — 空仓库治理

**已完成并保留历史签收**：初始候选 C=`b2d18951a101bd0e7c138965bb562e1bd430ab36`；用户随后明确委托同一专用验收智能体担任 Controller，委托修订提交 C=`02f466d8bec68ee4df9a0eeb0f2c9722334552dd`、T=`597aad4f54feb93ededb3220fb07f353c1ffb498` 已经同一控制器本地 ACCEPT、普通 push、远端 readback ACCEPT。该修订不改写初始 G00 签收事实。此后 Controller 是用户明确委托的该专用验收子智能体，用户保留最高权威。

### G01 — 活动计划与来源矩阵（当前 Atom，纯文档）

- 仅基于已接受 G00，读取已固定 Git 源的真实 blob、当前包计划和治理文件；核对本节 A1/A2。完成 `reviews/PLAN_PROVENANCE_MATRIX.md`，逐条登记计划动作的授权来源、原始路径/提交/blob、原文证据、作用文件与影响，未核实写 `NOT_VERIFIED`。
- 独立只读 Controller/Reviewer 逐条审矩阵、B01–B14 和计划；检查不存在新增文学创作程序，且 A1/A2 没把推测写成事实。Writer 冻结 C/T，普通 push，提供原始远端 readback；同一 Controller 对精确 C/T ACCEPT 后，I00 才解锁。
- 本 Atom 只改计划和来源矩阵文档；不克隆上游、不安装、不运行原版工具、不读用户 Key、不调用 API、不读取/解压源稿、不生成作品。

### I00 — 三上游克隆、固定版本与零修改保障（无故事生成）

仅在 G01 精确 C/T 被 Controller 接受后开始。先现场读取状态；若已有子模块/目录逐项只读核对，不覆盖。空位时依次加入并固定：CNW `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；NK `b857f34b7d371ae82c30e00eb021884c14d08ae9`；CritiCS `fbf66cbc913012c6f80af1687e27f0ce350475e3`。记录源 URL、许可证、commit/tree/gitlink。建立项目自有 `.gitignore`，核实私有目录与 Key 被忽略且不打印 Key。检查每个 Vendor 的 HEAD 与 `git status --porcelain=v1`；不得运行 install/build/compile。提交仅含 `.gitmodules`、gitlinks、必要的自有许可/来源说明和忽略规则。独立审查与远端 readback 后由 Controller 对精确 C/T 签收。

PowerShell 7 执行骨架（逐条执行；任何路径已存在先只读比对，不覆盖）：

```powershell
$ErrorActionPreference = 'Stop'
$Root = 'D:\CangqiStudio\StoryStudio'
Set-Location $Root
$Dirty = git status --porcelain=v1
if ($Dirty) { throw 'B07: dirty worktree; preserve and inspect, do not overwrite' }
git submodule add https://github.com/MintoTsukino/claude-novel-workflow.git third_party/claude-novel-workflow
if ($LASTEXITCODE -ne 0) { throw 'GIT_SUBMODULE_CLONE_FAILED_CNW' }
git -C third_party/claude-novel-workflow checkout --detach 97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
if ($LASTEXITCODE -ne 0) { throw 'PIN_FAIL_CNW' }
git submodule add https://github.com/zhangchaodesign/narrative-keyframing.git third_party/narrative-keyframing
if ($LASTEXITCODE -ne 0) { throw 'GIT_SUBMODULE_CLONE_FAILED_NK' }
git -C third_party/narrative-keyframing checkout --detach b857f34b7d371ae82c30e00eb021884c14d08ae9
if ($LASTEXITCODE -ne 0) { throw 'PIN_FAIL_NK' }
git submodule add https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation.git third_party/CritiCS
if ($LASTEXITCODE -ne 0) { throw 'GIT_SUBMODULE_CLONE_FAILED_CRITICS' }
git -C third_party/CritiCS checkout --detach fbf66cbc913012c6f80af1687e27f0ce350475e3
if ($LASTEXITCODE -ne 0) { throw 'PIN_FAIL_CRITICS' }
@(
  @{Name='claude-novel-workflow'; SHA='97ad71fe5e5e76a82275c6c63d4add06fb60ab6e'},
  @{Name='narrative-keyframing'; SHA='b857f34b7d371ae82c30e00eb021884c14d08ae9'},
  @{Name='CritiCS'; SHA='fbf66cbc913012c6f80af1687e27f0ce350475e3'}
) | ForEach-Object {
  $Path = Join-Path $Root ('third_party\' + $_.Name)
  $Actual = (git -C $Path rev-parse HEAD).Trim()
  $DirtyPaths = git -C $Path status --porcelain=v1
  Write-Output "VENDOR=$($_.Name) EXPECTED=$($_.SHA) ACTUAL=$Actual"
  if ($Actual -ne $_.SHA -or $DirtyPaths) { throw "B02: vendor identity or worktree mismatch: $($_.Name)" }
}
git submodule status
git check-ignore -v inputs/private workspace runtime runs
git status --short
```

### I01 — 本机兼容性与真实执行路径（不调用付费 API）

仅在 I00 接受后执行。Vendor checkout 保持只读；用 `git archive` 原字节复制至 Git 忽略的 runtime。先只读探测 Node/npm/Python/WSL 与硬件，不安装大型环境。按 README 在隔离 runtime 副本进行解析、安装、构建与启动，记录命令、退出码、源和副本文件身份、实际异常。CritiCS 的第 43 行源文本需 `py_compile` 实证；如失败，准确记录 B11，不改原文件。NK 必须证明模型配置、base URL 和 schema 在原语义下确实可路由 Flash；不发真实创作请求，不以 SDK 环境变量猜测替代证明。I01 输出 `evidence/I01_NATIVE_COMPATIBILITY.md`，逐工具标 `NATIVE_BOOT_OK / MODEL_ROUTE_FLASH_VERIFIED / BLOCKED_UPSTREAM_IMMUTABLE / NOT_TESTED`。如原版冲突，停止在事实状态并交 Controller，不继续宣称全栈。

先执行只读环境探测：

```powershell
Set-Location 'D:\CangqiStudio\StoryStudio'
node --version
npm --version
py -0p
wsl --status
```

每个工具从已 pinned 子模块导出到新建、唯一的 Git 忽略 runtime 目录；目标存在则停止，不覆盖：

```powershell
$RunId = [guid]::NewGuid().ToString('N')
$Runtime = Join-Path 'D:\CangqiStudio\StoryStudio\runtime\build\CritiCS' $RunId
if (Test-Path -LiteralPath $Runtime) { throw 'B07: runtime target exists; do not overwrite' }
New-Item -ItemType Directory -Path $Runtime | Out-Null
git -C 'D:\CangqiStudio\StoryStudio\third_party\CritiCS' archive --format=tar -o (Join-Path $Runtime 'source.tar') HEAD
if ($LASTEXITCODE -ne 0) { throw 'GIT_ARCHIVE_FAILED_CRITICS' }
tar.exe -xf (Join-Path $Runtime 'source.tar') -C $Runtime
if ($LASTEXITCODE -ne 0) { throw 'RUNTIME_ARCHIVE_EXTRACT_FAILED_CRITICS' }
# Python解释器仅在 `py -0p` 探测后由当前执行者按实际可用项填写：
& $PythonExe -m py_compile (Join-Path $Runtime 'critics\setting\chatsetting\gptsetting.py')
```

CNW 是文档流程而非可编译程序；NK 的隔离副本按其 README 的依赖与启动命令操作。所有依赖安装和构建仅作用于 runtime，运行前后核对 Vendor checkout clean 及源/副本受控文件身份。不得为探测兼容而发出真实供应商创作请求。

### I02 — 定位本机 2.3 ZIP

仅在 I01 未遇不可解除的前置阻塞、且 Controller 接受 I01 后执行。通过 Windows Known Folder API/注册表只读解析 Downloads；递归只读搜 ZIP 并比较 SHA256 `300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2`。不自动下载替代版、不清理或移动下载目录。无匹配时记录搜索结果并报告 B04/B10；有匹配时记录路径、大小、修改时间和 SHA，检查 ZIP 成员路径/重名，解压到 `inputs/private/release/<sha>/`，不运行包内程序。确认 `scene_manifest.json` 的 32 场 `J01–J32` 与版本字段；只生成私有来源索引。Reviewer 和 Controller 对证据签收。

只读定位和哈希的 PowerShell 骨架：

```powershell
$ErrorActionPreference = 'Stop'
$Root = 'D:\CangqiStudio\StoryStudio'
$DownloadGuid = '{374DE290-123F-4565-9164-39C4925E467B}'
$Folders = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
$Downloads = [Environment]::ExpandEnvironmentVariables($Folders.$DownloadGuid)
if (!(Test-Path -LiteralPath $Downloads)) { throw 'SOURCE_DOWNLOAD_FOLDER_NOT_FOUND' }
$Expected = '300A829C7524D620AB89177AFCF52C03DFFEA633392C632F69A943F798DAD3B2'
$Candidates = Get-ChildItem -LiteralPath $Downloads -File -Recurse -Filter '*.zip' -ErrorAction Stop
$Matches = @($Candidates | Where-Object { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash -eq $Expected })
if ($Matches.Count -eq 0) { throw 'B04/B10: exact JUN-SINGLE-02.3 release not found; do not substitute' }
$Matches | Select-Object FullName,Length,LastWriteTime
```

### I03 — 按 CNW 原文导入并设计一个场景

仅在 I00–I02 都接受且 I01 证明必需原版工具可在不可变约束下执行后开展。私有工作区中按 CNW `EXISTING_PROJECT_IMPORT.md` 与 `_workflows/01_first_import.md` 建立本项目 Canon 输入：源稿明示事实标 `CONFIRMED`，推论标 `INFERRED`，缺口标 `TODO_CONFIRM`。依据原作者架构/Plot/Card/Brief 模板，从已定故事找一个合法日常插入点，只做一个 Plot、一张 Scene Card、一个 Writing Brief。保留前后原著锚点和行动依据；不得增改 32 场原稿、不得把推论升 Canon。交付留在私有 Git 忽略目录。

### I04 — 一场真实样本（仅在用户授权及兼容性成立后）

仅在 I00–I03 被 Controller 接受、NK/CritiCS 均证明原版语义可用且 Controller 已明确接受 I01 模型路径后，才可进行任何付费 Flash 请求。只允许 `deepseek-flash`。按 CNW Brief 写一场完整的君天离单 POV 日常对话与动作，不私设 token/字数/调用数。NK 原版生成结果必须真实进入样本制作链；CritiCS 必须走固定原算法和真实流程。任一工具不兼容时将相应使用状态写 `NOT_RUN`/`BLOCKED`，不以自写替代。保存本地请求响应、服务端型号、用量、费用原始凭据及前后上下文；保留首次失败 raw。用户亲读前立即停止，状态 `CONTROLLER_REVIEW_REQUIRED`，不得自动生成第二场或扩量。不能把历史 `$12` 当预算授权。

### I05 — 远端证据与最终读者判断

只提交项目自有治理、gitlinks、来源映射、纯传输适配及不含敏感内容的证据索引；不提交用户原稿、Key、完整 Prompt/响应或样本正文。独立 Reviewer 对精确源、证据和提交作只读审查，Writer 普通 push 并读回 C/T，Controller 按精确候选签收。最终作品是否好看/好玩仍由用户本人读样本后判断；在此之前 `CREATIVE_EFFECT=NOT_RUN`，任何工程状态不得替代用户判断。

## D. 计划启用前的高影响核对

| 问题 | 当前证据状态 | 计划约束 |
|---|---|---|
| 远端 main 是否空树 | 之前记录 empty tree；本轮 readback 只有 main SHA | 下一 Atom 重新现场读取 C/T，不覆盖。|
| MVP治理基线 | 精确活动分支 C/T 已固定 | 只读参考规则机制。|
| 三个 Vendor 身份 | 三个固定 commit/tree 已核 | I00再现场验证并保持零修改。|
| CNW 是脚本还是人工流程 | 固定 blob 明确称 prompts + procedures，非 scripts | 按文档操作，不自造 agent 流程。|
| NK 原样 Flash 可用性 | Route 硬编码 `gpt-4.1`；外部 URL/兼容性未知 | I01隔离环境验证，未证实则不调用。|
| CritiCS 源码可解析 | `gptsetting.py` 第43行有文本异常；解析器结果尚无 | I01原字节实证；失败即记录，不修补。|
| 2.3 ZIP 当前在 Downloads 吗 | 本 Atom 未读取 Downloads | I02依 Known Folder 与精确哈希只读查找。|
| 一场可否证明全篇质量 | 不能 | 只报告这场实际证据；是否扩量由用户另行决定。|
| 许可证覆盖示例故事吗 | CNW声明区别文档/模板与示例故事版权 | 不复制示例作品进本项目公开 Git。|
| 工程 PASS 能否替代读者判断 | 不能 | 用户读稿前 `CREATIVE_EFFECT=NOT_RUN`。|

## E. 报告字段

```text
STORYSTUDIO_REMOTE_MAIN_SHA=<现场读取>
STORYSTUDIO_REMOTE_MAIN_TREE=<现场读取或NOT_VERIFIED>
LOCAL_HEAD=<现场读取>
LOCAL_WORKTREE=<CLEAN|DIRTY_WITH_PATHS>
CURRENT_ATOM=<G00|G01|I00|I01|I02|I03|I04|I05>
PREVIOUS_ATOM_CONTROLLER_ACCEPTANCE=<真实消息与候选C/T>
UPSTREAM_CNW_SHA=97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
UPSTREAM_NK_SHA=b857f34b7d371ae82c30e00eb021884c14d08ae9
UPSTREAM_CRITICS_SHA=fbf66cbc913012c6f80af1687e27f0ce350475e3
UPSTREAM_DIRTY_PATHS=<EMPTY|具体列表>
MODEL_REQUESTED=<实际请求值，否则NOT_RUN>
MODEL_SERVED=<真实返回值，否则NOT_PROVIDED/NOT_RUN>
ACTUAL_PROVIDER_USAGE=<真实原始值，否则NOT_RUN>
DOWNLOADS_RESOLVED=<实际Known Folder，否则NOT_RUN>
RELEASE_SHA256=<实际值，否则NOT_RUN>
CRITICS_NATIVE_PARSE=<实测命令和结果，否则NOT_RUN>
NK_FLASH_COMPATIBILITY=<实测证据，否则NOT_RUN>
REAL_UNMODIFIED_CRITICS=<YES|BLOCKED|NOT_RUN>
REAL_UNMODIFIED_NK=<YES|BLOCKED|NOT_RUN>
ONE_SCENE_CONTENT_PATH=<实际路径或NOT_RUN>
ONE_SCENE_READTHROUGH=<实际路径或NOT_RUN>
REVIEWER_MESSAGE_REF=<独立消息或NOT_RUN>
CONTROLLER_ACCEPTANCE=<真实消息或NOT_RUN>
CREATIVE_EFFECT=<CONTROLLER_REVIEW_REQUIRED|用户实际结论|NOT_RUN>
BLACKLIST_EVENT=<具体Bxx或NONE_VERIFIED_FOR_CURRENT_ATOM>
NEXT_ATOM_LOCKED=<YES|NO_PER_CONTROLLER_ACCEPTANCE>
```

任何不兼容都要报告具体文件/行、原命令、原始错误、Hash 与责任边界；不以“技术原因”含混带过，不调用替代模型或启用旧 fork。
