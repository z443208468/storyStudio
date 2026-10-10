# P2 技术实施规范：具体文件、修复点、命令与运行合同

这份文件规定要实现的内容，不宣称下面的项目脚本已经编写或在用户 Windows 上测试过。源码事实引用 `reviews/SOURCES.md`；其余为本版工程设计。

## T1. 补丁式部署，不维护第二份失控代码

原子模块是对照仓；实际运行树是带补丁的衍生版本。构建身份至少包含：上游 commit、全部补丁按顺序的 SHA256、依赖锁 SHA256、项目配置的非秘密字段摘要。

步骤：
1. 原子模块上 `git rev-parse HEAD`、`git status --porcelain=v1`；已有未知修改只读记录，不清掉。确认用于导出的 commit 是计划记录的固定版本。
2. 使用 `git archive --format=zip --output=<private-archive> <source-sha>` 导出到新的生产构建目录，拒绝覆盖未知目录。不是在原 checkout 中安装依赖。
3. 从根仓运行 `git apply --directory="runtime/patched/<tool>/<build-id>" --check <patch-file>`，然后用相同参数去掉 `--check` 应用；补丁路径必须相对于对应上游根目录。必须限定到实际 runtime 构建树；用显式工作目录及路径清单防止落到父仓。脚本须检查所有原文件 hash，已应用时不能重复打补丁。
4. 补丁第一次从人工/程序修复的前后版本生成，保存到根仓 `patches/<tool>/`；每项写“旧缺陷→具体改动→保留方法→验证”。不得只在 runtime 留下手工修改。
5. 在另一个全新 runtime 目录重建同一 source+patch+lock，比较受控源码哈希；相同后才把该构建认作可重复版本。
6. 不要求运行目录无 `node_modules`/`__pycache__`；这些是构建物，不是“上游被污染”。原始参考文件仍可用于复核。

`PATCH_INDEX.json` 必须写实际值，不提前填伪哈希。最低字段：tool、source_commit、ordered_patch_files、patch_sha256、changed_paths、classification、verification、runtime_build_id。

## T2. Windows 环境与依赖

### T2.1 路径与工具行为

所有本项目新环境、安装缓存、构建和临时输出优先落 D 盘 runtime。保留当前系统 Python 3.13；只为 CritiCS 建 Python 3.11 环境，不全局降级。Node 先使用已观察到的现有版本，失败原因明确时再决定便携版本，不先换机器/驱动。

PowerShell 外部命令每次检查 `$LASTEXITCODE`；`$ErrorActionPreference='Stop'` 本身不能替代外部退出码检查。使用 `-LiteralPath` 或正确引用含空格路径。控制台输出是报告，不能直接作为成功断言。

使用现有 uv；不存在时从 Astral 官方 release 取得 Windows standalone 工具到 `runtime/tools/uv/`，固定其版本与下载 hash，不运行不明来源脚本、不全局改 PATH。uv 能安装独立 Python；环境目录变量见官方文档 [S12]。

```powershell
$Root = 'D:\CangqiStudio\StoryStudio'
$env:UV_CACHE_DIR = Join-Path $Root 'runtime\cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Root 'runtime\python'
$env:UV_PYTHON_BIN_DIR = Join-Path $Root 'runtime\python-bin'
$env:PIP_CACHE_DIR = Join-Path $Root 'runtime\cache\pip'
$env:npm_config_cache = Join-Path $Root 'runtime\cache\npm'
$env:TEMP = Join-Path $Root 'runtime\tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
# $Uv 由现场发现的现有/本项目便携 uv.exe 路径提供。
& $Uv python install 3.11
if ($LASTEXITCODE -ne 0) { throw 'PYTHON_INSTALL_FAILED: inspect cause; do not reset project' }
& $Uv venv --python 3.11 (Join-Path $Root 'runtime\envs\critics-api')
if ($LASTEXITCODE -ne 0) { throw 'VENV_CREATE_FAILED' }
```

已存在且验证合格的 venv 不重复创建。记录 `python --version` 的实际补丁版本，不把 `3.11` 范围伪称精确锁版本。uv 若支持禁用注册表和全局可执行链接，启动参数按安装版本官方 help 设置；不使用 `--default`、`update-shell` 或改全局 Python 的操作。

### T2.2 CritiCS 依赖只按实际调用图安装

固定原 requirements 同时出现 `openai==0.28.0` 和 `langchain-openai==0.1.19`；后者 PyPI 元数据要求 `openai>=1.32.0,<2.0.0`，不能直接同时满足 [S06]。这不是靠换 Python 就会消失的冲突。

先建立以下起始约束（`requirements-api.in`，不是已经验证的 lock）：

```text
langchain==0.2.11
langchain-community==0.2.10
langchain-core==0.2.24
langchain-openai==0.1.19
openai>=1.32.0,<2.0.0
PyYAML
```

`pandas` 等若实际入口仍 import，就保留并锁定兼容版本，或有证据表明纯未使用导入时删除该导入并记补丁；不能忽略真正的依赖。`nltk/scipy/transformers/vllm/ray/pyarrow/torch` 不在所选生产函数及其递归导入链中则不安装；如果确实进入有效链，先查为什么进入，不凭包名臆断可删。

执行顺序：
1. 阅读本次入口递归 import；在适配版里消除仅供研究支路的 import 副作用。
2. 用 uv/pip 解析并生成准确 lock，安装后跑 `pip check` 或 uv 等效依赖检查。
3. 在启动用的同一个解释器下 import `Critic`、`modifiedStoryline`、`Refinement`，不要用系统 Python 测另一个环境。
4. 捕获 LangChain/SDK 不兼容的实际异常；优先在 0.2/0.1 API 兼容范围内修版本和导入。确需移动到维护版本时允许做保留调用职责的 API 迁移，由 Controller 对照本次调用图验收，不被旧依赖锁永久卡死。
5. 检查实际已安装版本的漏洞和包来源，修复影响此运行路径的风险，不把未经核查的旧依赖宣称安全。
6. 将成功环境的精确依赖及 Python 版本入锁；最初依赖范围不能作为“已验证安装成功”的证据。

本方案不运行原论文大规模数据生成、模型训练、vLLM server、全套评测和未使用的 Streamlit 页面。原模块保留；明确功能范围不是把失败功能偷偷删成成功。

## T3. CritiCS 具体修复清单

### C01：语法恢复

文件：`critics/setting/chatsetting/gptsetting.py`。移除 `verbose=True` 后多余 `s`，保留 `ConversationChain(llm, memory, ...)`。测试：原失败样本、修复后解析和运行入口 import。原失败记录不覆盖。

### C02：统一真实 Flash 配置

`chatsettubg()` 内的 `ChatOpenAI` 迁到当前所锁 `langchain_openai.ChatOpenAI`；显式传入 DeepSeek base_url、真实模型、进程 Key。保留 memory 与 predict 的使用方式、原 stop 参数和本次使用函数的温度意图。

最小目标形态（参数名须在安装版本实际验证）：

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model=cfg.model,                 # 必须是 deepseek-flash
    base_url=cfg.base_url,           # 必须是配置中的官方 DeepSeek URL
    api_key=secret_from_process,
    temperature=original_temperature,
    stop=original_stop,
    max_retries=0,                   # 仅外层负责有限重试，避免乘法重试
    timeout=cfg.read_timeout_seconds,
    extra_body={"thinking": {"type": "disabled"}},
)
```

选择 non-thinking 是本次保留原 sampling 参数含义、减少额外推理开销的明确工程选择，不称原作者要求。当前官方说明 thinking 默认开启且会忽略部分 sampling 参数，必须显式处理 [S11]。若锁定 SDK 不支持 `extra_body`，在 HTTP client 的有审计传输边界注入该真实字段，不改模型返回值，不伪装服务。

检查 `plan.py` 内 `modifiedStoryline(... model_name='gpt-4')` 等实际调用点：不得让调用方传入的旧 GPT 常量覆盖统一配置。可将默认值改为配置，或让原参数只承担角色标记、实际供应商字段明确取 Flash，但不能将这种映射隐藏。最简单是修改实际调用点使用同一模型配置。

`completion_mode` 的 instruct 分支、`storygen/common/llm/llm.py` 旧 0.x SDK 路径不在本轮调用图；不用重写它们，不得在产品入口自动落入它们。若后续证据证明必须使用，另按同方法迁移对应 API，不暗启动 OpenAI 接口。

### C03：Voice 正文漏接

`critics/setting/promptDesign/story_template.py` 的 `refine_prompt_voice` 缺少 `{story}`，尽管调用方 `.format(story=self.sentence)` 传了正文 [S05]。在 `Sentence)` 下补 `{story}`，与 Image 的正文输入职责一致。保留 Informal language、Unusual words、Noteworthy sentence structures、Authenticity 等原维度；不得顺便换成自制评分。

离线测试用唯一标记的真实示例句段 `VOICE_INPUT_MARKER_...`，断言它出现在发送给 Voice 的请求内；断言 Image 与 Voice 都接到同一输入身份，Leader 接到这两份具体结果。只检查参数变量非空不够。

### C04：Question 与 persona 提取

`plan.py` 的 Inspector 提取用单行正则，遇到 `Question :` 后换行可能只返回空白；persona 分割以普通数字 `2`/`3` 作结束边界，可能误截年龄、履历等数字 [S04]。修复的是可靠取出原模板要求的内容，不改变最终选择。

- persona：按 `Expert 1/2/3` 和 `Leader` 标题边界分割，保留全文；四段数量不对时结构化报错，不填空 persona。
- Question：限定在选中问题的区域，支持 `Question:` / `Question :` 后多行文字，到 `Why:`、下一评价字段或结束标签为止；不得把原始列出的第一个问题误当 Inspector 选择。
- 如果返回不符合格式，保留 raw，先判断解析器还是模型的问题；必要时一次同结果格式修复请求，只允许提取原结果，不能换一个新批评结论。仍失败返回当前步骤待修，不伪造“没问题”。
- 不“统一拼写”全部函数名；`chatsettubg`、`image_refinmenet`、`Two_refinement` 现有调用可继续用，避免无价值重构。

### C05：条件性缺陷，按是否可达处理

`Story_Selector.calculateSelectScore` 引用未在该文件定义的 `OPENAI_API_KEY`，`text.py` 的未使用 `split_personas()` 引用未定义 `persona`。本计划默认不调用它们；必须明示 `NOT_IN_SELECTED_PATH`。如果桥接实际误调用，先修桥接回到选择的原入口；若确实成为必需入口，再定点补依赖/参数，不能把整仓所有潜在 bug 拉成新工程。

同样不得把“变量叫 three_refine”理解为必须返回三个结果：实际 Leader 模板选择的数量以源码任务为准，不按变量名发明行为。

### C06：桥接接口

`tools/critics_bridge.py` 只实现三种动作：
- `plan-critique --plot <file> --run-dir <dir>`：读当前 Plot，调用 `Critic(plot).three_critic()`，保存 structure/ending/original/inspector 及原始响应。
- `plan-revise --plot <file> --critique <file> --run-dir <dir>`：调用实际 `modifiedStoryline`；原方法是根据反馈修改剧情，项目保护范围明确输入。
- `text-refine --excerpt <file> --run-dir <dir>`：调用 `Refinement(excerpt).Two_refinement()`，保存 Image/Voice/Leader。

脚本进入本次运行目录再调用原函数，或对原写文件 helper 做目录适配，防止固定 `output/...` 路径覆盖上一轮。UTF-8；原始响应独立编号；工作区产物路径必须受根目录约束，不能接收模型给出的任意写路径。

## T4. NK 具体接入

### N01：明确服务端模型，不用伪装网关

固定源 `lib/openaiServer.ts` 只调用 `createOpenAI({apiKey})`；生成路由含 `openaiProvider('gpt-4.1')` [S07]。改为服务器进程中的 DeepSeek 配置；保留函数用途及路由生成算法。

目标：

```typescript
const provider = createOpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: process.env.STORYSTUDIO_BASE_URL,
  fetch: auditedFetch,
});
const model = provider.chat(process.env.STORYSTUDIO_MODEL ?? 'deepseek-flash');
```

创建前验证 Key 存在、模型属于唯一允许项、baseURL 主机/协议正确，日志不打印秘密。允许端口的本地 mock 仅在明确 `offline-test` 模式，产品 live 模式不得走 mock。

固定 SDK `@ai-sdk/openai@2.0.53` 的默认可调用 provider 使用 Responses 模型，且支持外置 base URL；因此不能再说“改 base URL 就必然解决全部接口问题”。本版明确选 Chat Completions，避免隐式协议选择 [S08]。这不表示当前 DeepSeek 一定不支持 Responses，只是本项目采用一条简单明确的共同路径。

### N02：JSON Object + 原本地 Schema

固定 SDK 支持 `providerOptions.openai.structuredOutputs=false`，会使用 `json_object` 而非 `json_schema` [S09]。DeepSeek 官方 JSON 指南要求 JSON 模式以及明确的 JSON 格式提示 [S10]。

目标：

```typescript
const result = await generateObject({
  model,
  schema: ResponseSchema,                 // 原路由 schema 保留
  prompt: renderedOriginalPrompt,         // 原业务模板 + 项目输入
  providerOptions: { openai: { structuredOutputs: false } },
  maxRetries: 0,
});
```

若 SDK 不会自动把本地 schema 说明进 prompt，则在传输/格式层添加仅描述字段的 JSON 输出要求，业务 prompt 仍留原文和项目实例。记录原模板 hash、渲染输入 hash、最终请求 hash。不能在解析失败时返回一份手工填充 JSON。

non-thinking 字段若 SDK 未直接透传，在 `auditedFetch` 的 JSON 请求体添加 `thinking:{type:'disabled'}`，保存最终出站请求（脱敏），其他业务内容不改。它是本地 fetch 包装，不新增网络代理，不替换供应商响应。

### N03：响应有效性与项目映射

输入继续使用原 `eventSequence`、`perspectives[]`、`customPrompt` 等实际字段；首场只有一个 perspectives 项。一个任务项对应一个输出；输出非空、有预期 reflection、通过 Zod，且序号/映射一致。

本次 `customPrompt` 只追加项目约束：中文、君天离受限视角、既有事实、当前场景输入范围；不把它改成另一套生成评分。原 route 没有 task id 返回时，本场用唯一项确定对应，多项离线用索引/数量核对；不得声称多任务语义全通过。

选择哪些 NK routes 首次开放时写进配置。用户可点击到的生成路由必须统一迁移和检查；未迁移的隐藏/禁用且不在本次功能声明内，不在页面上留一个仍发 GPT 的入口。

### N04：安装与运行

在带补丁的 NK 构建目录运行 `npm ci`；若修改 package.json 或 lock，先在该适配版本生成匹配锁，再 `npm ci` 重建验证。不要 `npm install --force` 掩盖依赖冲突。启动时显式 `next start --hostname 127.0.0.1 --port <配置端口>`；端口冲突由工具选空闲端口并更新同一运行配置，不新建服务架构。

Next build 导出/类型错误属于本阶段正常修复；只在实际错误表明 Node 版本不匹配时选择匹配的独立版本。安全修复允许小版本更新并检查 route 合同，但不借机重写 UI。

## T5. 统一请求、重试、费用与证据

### T5.1 默认工程参数

| 参数 | 本版默认 | 含义 |
|---|---|---|
| 新增生产 API | DeepSeek `deepseek-flash` | 请求不使用旧 GPT 标记；保留真实返回 model |
| 默认 base URL | `https://api.deepseek.com/v1` | 不转发到未知第三方；执行时对官方文档及真实响应核对 |
| thinking | disabled | 显式工程选择；保留原非思考 sampling 的作用 |
| 同时在途请求 | 1 | 首场串行，减少重复计费和追踪混乱 |
| 网络重试 | 最多 2 次额外尝试 | 仅连接/429/可恢复 5xx；401/403/参数错误先修配置 |
| 格式修复 | 最多 1 次专门格式修复 | 同结果提取，不改批评逻辑；失败转根因修复 |
| 内容盲重抽 | 禁止 | 修订有具体问题单；两轮无改善先修 Brief/输入 |
| HTTP 读超时 | 默认 180 秒，可按实际流式行为调整 | 不是“到了就重发”；不判超时等于未计费 |
| 初轮 API 费用保护 | 10 元人民币，持久化覆盖本轮全部 run | 本版保守工程默认，不是用户原先指定，也不是硬保证实际账单；不自动充值/扩大 |
| 文学字数 | 不设机械定值 | 按一场完整戏完成；输出上限只做协议/费用防护 |

不再沿用旧 `$12`；重启进程/换 run_id 不重置本轮费用保护。费用保护只管理新增生产 API，不虚构能控制 Codex 订阅用量。

请求前按官方最新价格快照、预估输入和协议最大输出检查余量；最大输出取供应商可用上限与预算可承受量中更小者。它不规定故事写多少字。账单与预估存在偏差，所以应表述为“估计支出保护”，不能承诺绝不超一分钱。

收到 `finish_reason=length`：保留不合格完整 raw；依据供应商上限/剩余预算提高本场输出空间或定点续写，然后检查拼接重复与完整性。不拿截断正文当交付；不为了塞进上限删故事功能。

### T5.2 防止 SDK 与外层重试相乘

SDK `max_retries/maxRetries` 设 0，由一个外层控制器决定有限重试并记账；原调用函数内部若自带循环，只在本次选中路径检查和约束，不额外叠一层无界 retry。

可恢复请求按 `Retry-After` 或退避重试，记录每次 attempt。读超时/连接断开后可能已产生费用，先标 `OUTCOME_UNKNOWN` 并保存已有 request-id/响应；能查回则查回，不能查回才由 Controller 在余量内决定一次重发，不声称 exactly-once。

### T5.3 最小记录结构

每个请求一个 JSON 原件与索引，至少记录：
`run_id, sample_id, stage, tool, function, source_commit, patch_id, input_sha256, final_request_sha256, attempt, requested_model, served_model, provider_request_id, time, http_status, finish_reason, usage_raw, response_sha256, status`。

Key 和 Authorization 在任何落盘记录前去除，不能“先写含 Key raw 再脱敏”。完整原稿/请求正文留私有 `runs/`；公共证据仅 hash、版本和不含剧情的总结。

只在已验证返回的 usage 字段基础上拆分 input/output/cache；未提供的字段为 UNKNOWN。估计费用有 price_source 和时间，结算费用只有账户可核账单才能填。流式处理保留所有有效正文片段和最终 usage，不将 reasoning 字段当成故事正文。

### T5.4 断点续做

每一阶段保存 `PENDING/RUNNING/SUCCEEDED/FAILED/OUTCOME_UNKNOWN/ACCEPTED`；脚本只写到 SUCCEEDED，ACCEPTED 来自真实 Controller 消息。

复用键至少包括：source ZIP 身份 + 上游/补丁/锁身份 + 当前模板/配置 + 输入文件 hash + stage + sample_id。输出文件 hash 符合且运行成功可复用；阶段是否正式接受另看 Controller 消息。

即使未发生阶段 commit，已经落盘且能证明来源的成功调用仍可重验后复用，不能为了“未提交”重复付费。只有真实受影响的后续阶段失效。

## T6. 薄生产入口的模块边界

不要编写一个巨型通用引擎。最少实现这些职责，可合并成少量文件：

| 入口/模块 | 输入 | 输出 | 不允许承担的职责 |
|---|---|---|---|
| `studio.ps1` | 命令、配置、run id | 调用对应步骤、退出码、产物路径 | 自主发明剧情、自动签质量、无限扩样 |
| `prepare_runtime.py` | 参考源、补丁、锁 | 可重建的运行目录 | 修改原稿、清空未知目录 |
| `source_import.py` | 实际 ZIP/已有输入 | 安全解压、manifest、源索引 | 根据文件名猜 Canon |
| `provider_io.py` | 明确请求/配置 | 真实响应、usage、重试/费用记录 | 改写供应商响应、隐藏模型、自动充值 |
| `critics_bridge.py` | Plot/句段文件 | 原 CritiCS 输出 | 自己生成“类似 CritiCS”的意见 |
| `cnw_step.py` | 实际上游模板+项目输入 | 指定的 Plot/Card/Brief/Prose/Revision 文件 | 自创文学理论或把工程 agent 文本冒充 Flash |
| `export_readthrough.py` | 已接受样本与前后原文 | 离线 HTML/TXT/MD | 改正文、悄公开上传 |

`cnw_step.py` 渲染原模板和本项目约束，再调用 Flash；输入源定位与外部事实选择可由 Codex 完成，但所有冒称生产 API 生成的正文必须有相应请求原件。没有把“一键通用自动工作流”当成本轮交付范围。

## T7. 提交与恢复的具体检查

使用显式文件列表提交，不 `git add .` 把私有内容混进去。提交前检查 staged 文件及差异、忽略规则、Key 特征和原稿路径；路径过滤之外仍要人工看新增文件摘要，不能只信 secret scanner。

原子模块保持来源参照；新增补丁、依赖锁、脚本纳入根 repo。每阶段候选普通 push 后用远端 ref 和 commit 的 tree 交叉核对，不把 `git push` 退出码当唯一证据。

最终 main 发布先核对其是否当前分支祖先；不是则检查差异/PR。快进不能覆盖未知并行工作，push 拒绝时不得使用 force。发布失败与本地成品交付分开记录；不要因此销毁或重做文本。
