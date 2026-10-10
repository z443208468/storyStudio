# P2 来源核查记录

核查日期：2026-10-10。GitHub 用户仓库使用已连接工具读取。下面源码路径按固定提交定位；网页提供接口/依赖事实，执行时仍需实际验证。上游代码、官方说明和本版工程选择在文档中分开。

## S01 — CNW 文件与生产职责

`MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`

- https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/docs/ARCHITECTURE.md
- 位置：Per-Chapter File Set、90_canon、92_style_engine、07_draft、94_runtime。
- 支撑：Plot/Card/Brief/正文的职责、Canon/风格文件、可建立运行交接文件。不是全部目录齐了就算生产完成。

## S02 — CNW 项目适配与导入

- https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/docs/HOW_TO_ADAPT.md
- https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/docs/EXISTING_PROJECT_IMPORT.md
- https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/templates/_workflows/README.md
- https://github.com/MintoTsukino/claude-novel-workflow/blob/97ad71fe5e5e76a82275c6c63d4add06fb60ab6e/LICENSE
- 支撑：通用结构用于本项目、人物/世界/风格应替换为自己的内容；工作流是提示及规程而非现成 deterministic scripts。许可与示例小说不同，保留归属，不能把示例剧情并入产品。

## S03 — CritiCS 语法/默认模型

- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/setting/chatsetting/gptsetting.py
- blob：`848802dae2fcd2cf29769dc06b539f106ca1b8af`。
- 位置：`chatsettubg()`；原 `verbose=True` 后的额外字符、默认 GPT model、ConversationChain。
- 本地 Python 3.13.2 解析失败的运行事实来自用户给出的 I01 报告及远端 evidence 文件，不是本方案作者亲自运行其 Windows 解释器。

## S04 — CritiCS 剧情原调用链与解析

- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/plan/plan.py
- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/setting/promptDesign/storyline_template.py
- 位置：`three_critic`、`split_personas`、`inspector_gpt`、`modifiedStoryline`、`Story_Selector` 与原 `Question` 模板。
- 支撑：五个原角色调用、按意见修改的路径、单行提取/普通数字分割风险、未被本次选择的 selector 分支。

## S05 — CritiCS Image/Voice/Leader 与漏正文

- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/text/text.py
- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/critics/setting/promptDesign/story_template.py
- 位置：`Refinement.Two_refinement`、`voice_refinement`、`refine_prompt_voice`。
- 支撑：原 Image/Voice→Leader 链；调用方提供 story，但 Voice 模板没有 story 占位符，内容不会因此自动进入模板。

## S06 — Python 依赖冲突

- https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation/blob/fbf66cbc913012c6f80af1687e27f0ce350475e3/requirements.txt
- https://pypi.org/pypi/langchain-openai/0.1.19/json
- 支撑：原 requirements 的 `openai==0.28.0` 与 langchain-openai 0.1.19 元数据所需 `openai>=1.32.0,<2.0.0` 互斥。本文给的起始依赖集合仍需解析和运行，不称已验证锁文件。

## S07 — NK 固定模型、接口和锁文件

- https://github.com/zhangchaodesign/narrative-keyframing/blob/b857f34b7d371ae82c30e00eb021884c14d08ae9/lib/openaiServer.ts
- https://github.com/zhangchaodesign/narrative-keyframing/blob/b857f34b7d371ae82c30e00eb021884c14d08ae9/app/api/generate-perspective/route.ts
- https://github.com/zhangchaodesign/narrative-keyframing/blob/b857f34b7d371ae82c30e00eb021884c14d08ae9/package-lock.json
- 支撑：createOpenAI、gpt-4.1 常量、eventSequence/perspectives/ResponseSchema；固定锁解析到 @ai-sdk/openai 2.0.53、ai 5.0.76。

## S08 — 固定 AI SDK provider 行为

- https://github.com/vercel/ai/blob/%40ai-sdk/openai%402.0.53/packages/openai/src/openai-provider.ts
- 位置：`createOpenAI`、`createLanguageModel`、`provider.chat`。
- 支撑：该锁版支持 base URL 配置，并且默认 provider 调用使用 Responses；选 Chat 应显式调用 .chat，不只改域名。

## S09 — 固定 AI SDK JSON 选择

- https://github.com/vercel/ai/blob/%40ai-sdk/openai%402.0.53/packages/openai/src/chat/openai-chat-language-model.ts
- 位置：`getArgs` 的 structuredOutputs 与 response_format 分支。
- 支撑：`structuredOutputs=false` 对应 JSON object；本地应用 schema 检查仍需保留。

## S10 — DeepSeek 接口与 JSON

- https://api-docs.deepseek.com/
- https://api-docs.deepseek.com/guides/json_mode/
- https://deepseek.com/en/news/deepseek-v4-1-flash/
- 支撑：官方兼容 SDK 接口、`deepseek-flash` 的现行名称、JSON object 模式及 JSON 格式提示要求。中文入口存在较旧抓取版本，本版不根据旧缓存将名称改回旧模型。
- 本版只要求真实出站 model=deepseek-flash，供应商返回 alias 如实记录，不将自己的期待回填为 model_served。

## S11 — 思考模式和采样参数

- https://api-docs.deepseek.com/guides/thinking_mode/
- 支撑：thinking 开关、额外请求字段及其与采样参数的关系。默认 non-thinking 是本版工程选择，不是原论文模型设置。

## S12 — uv 独立 Python 和路径

- https://docs.astral.sh/uv/concepts/python-versions/
- https://docs.astral.sh/uv/reference/environment/
- 支撑：独立 Python 安装与解释器选择；安装/缓存目录可配置。实施时记录实际 uv 和 Python 版本，不能凭脚本示例声称本机已经安装。

## S13 — StoryStudio 接续状态

- https://github.com/z443208468/storyStudio/commit/2586d378669b74d4fc9e4460aa80f2cd8a908038
- https://github.com/z443208468/storyStudio/commit/47394d3432fe8b8fe0c0d52edba50c602099e9af
- https://github.com/z443208468/storyStudio/blob/2586d378669b74d4fc9e4460aa80f2cd8a908038/evidence/I01_NATIVE_COMPATIBILITY.md
- 支撑：读取时已存在子模块及 I01 报告，不应该重新从空仓库开始。现场更新优先，不 reset 到本记录。

## 来源之外的设计

P2 的 8 阶段、工程模块边界、10元首轮保护、重试次数、单场衔接规则和验收接口是本版给出的实施方案，已明确标为工程/项目选择；不冒称为上游固定规定。实际能否运行和作品质量仍由对应真实证据及用户阅读决定。
