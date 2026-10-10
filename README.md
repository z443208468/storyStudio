# StoryStudio P2：保留开源生产方法，修复并适配实现，交付《苍歧》可读场景

版本：P2 / 2026-10-10。类型：完整执行方案，不是已经实施或验收成功的报告。

## 本轮唯一结果

在现有 `D:\CangqiStudio\StoryStudio` 工作之上，部署并打通 CNW + Narrative Keyframing + CritiCS 的项目适配版，以 `deepseek-flash` 为新增生产 API 后端，为《苍歧》JUN-SINGLE-02.3 生产一场君天离单 POV 的完整日常戏；交付初稿、工具意见、修订稿、前后文连读版和可再次使用的本地生产入口。用户判断作品是否满意，验收子智能体负责中途验收与纠偏。

**“不改原来的生产工作逻辑”不等于“不修 bug、不改依赖、不换 API 配置”。** 本版允许必要的实现修复、依赖治理、Flash 接入、结构化输出适配及项目模板填写；禁止另造一套算法冒充上游，禁止安装成功冒充作品完成。

## 使用

把整个 ZIP 交给原 Codex 会话，要求先读 `CODEX_START.md`。从当前工作树继续，不清空、不重建、不重做已确认成果。首次工作是替换旧版冲突规则并恢复 I01 的工程修复，不是再次申请用户批准 G00。

本包是替换式方案，不是给旧版附加一条例外。`AGENTS.md`、两份治理文件及旧计划入口均有替换内容；旧文件在 Git 历史中保留，历史审查与失败证据不得删除。

## 文档入口

- `CODEX_START.md`：原会话启动和接续指令。
- `plans/MASTER_PLAN_P2.md`：8 个阶段，逐步动作、输入、产物、验收和恢复位置。
- `implementation/TECHNICAL_SPEC.md`：CritiCS、NK、依赖、API、补丁和本地执行入口的具体实现。
- `implementation/PRODUCTION_SPEC.md`：源稿、Canon、Plot、Scene Card、Brief、试写、审稿、修订和交付。
- `implementation/ACCEPTANCE_SPEC.md`：原方法保真、功能、内容、断点续做和验收证据。
- `reviews/CONTROLLER_PROMPT.md`：同一个独立验收子智能体的完整职责。
- `reviews/P2_DESIGN_REVIEW.md`：旧版问题的逐项处置，不冒称独立签收。
- `reviews/SOURCES.md`：本轮实际核查的固定源码与官方接口资料。

## 已知接续点，而非必须回到的版本

本轮远端读取的候选分支 `codex/g00-governance-candidate` 指向 `2586d378669b74d4fc9e4460aa80f2cd8a908038`，包含 I01 失败报告；I00 记录提交为 `47394d3432fe8b8fe0c0d52edba50c602099e9af`。这些只是读取时的参考。执行时以现场 HEAD、工作树和原 Controller 消息为准，禁止 reset 到这些版本。

本包没有访问你的 Windows 本机、读取真实 Key、实际调用付费 API、修改远端仓库或生成项目正文。技术步骤与运行结果严格分开：修复/适配完成后必须按本包做真实验证。
