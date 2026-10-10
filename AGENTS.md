# StoryStudio — 唯一执行入口（全新空仓库重建，治理优先）

状态：**GOVERNANCE_CANDIDATE / NOT_ADOPTED**。本文件为待用户 Controller 批准的执行规则，不是已发生的签收记录。不得将旧 StoryStudio V1.0、V1.1、AT00–AT15、S00–S09 或其数据作为本轮活动指令、测试绿点、验收事实；旧材料只可用于解释已知失败，且不得复制到生产工作区。

## 启动顺序

1. 唯一 Writer/Codex 只读检查 `git status --porcelain=v1`、当前 HEAD、`origin/main` 和无跟踪文件；不得为获得干净状态而删除或覆盖。
2. 阅读 `docs/governance/GOVERNANCE.md` 与 `docs/governance/PLAN_AUTHORING_STANDARD.md` 的完整原文，逐条检查不可变边界、黑名单、角色权限与验收证据。
3. **G00只建立治理文件**；用户 Controller 尚未批准 G00 前，`plans/MASTER_PLAN_FROM_EMPTY.md` 仅是非活动候选，禁止克隆上游、下载或安装工具、读取真实 API Key、支付接口调用、生产故事。
4. G00独立只读 Reviewer 审查并报出精确候选提交/树身份与具体疑点；Writer普通 push 后提供远端原始 readback；Controller 明确批准后，才按 `plans/MASTER_PLAN_FROM_EMPTY.md` 当前 Atom 前进。
5. 每个 Atom 重复：读活动计划和原始来源 → 单一责任实现 → 完整真实证据 → 候选冻结 → 独立只读 Reviewer → 正常 push 与远端核对 → Controller 接受 → 解锁下一 Atom。审查拒绝时只修本 Atom，不自动扩大任务。

## 唯一角色

- **Controller（用户）**：唯一能批准/改变创作、模型、第三方版本、阶段范围、第三方内容改动禁令和最终作品质量的人。无用户明确消息，不产生授权。
- **Writer（Codex 主执行者）**：唯一能运行命令、修改 StoryStudio 自有代码与文档、提交和推送的人；不能签自己完成，也不能冒称 Reviewer 执行过命令。
- **Reviewer（独立只读子智能体）**：独立读计划、当前产品源码、原始证据、差异和远端读回；**只以消息返回** ACCEPT / RETURN / BLOCKED 并说明证据，不能写文件、运行脚本或测试、提交、推送、委托、做付费调用，也不能替 Controller 批准。

## 第三方永远不可变

下列全部是 **VENDOR_IMMUTABLE**，自克隆后不允许任何执行者、脚本、升级器、安装器或模型改动其 Git 跟踪的一个字节：

- `third_party/claude-novel-workflow/` 的原版文档、模板、Prompt、生产规程与文件；
- `third_party/narrative-keyframing/` 的源码、脚本、配置、Prompt、依赖清单与锁文件；
- `third_party/CritiCS/` 的源码、脚本、配置、Prompt、依赖清单与锁文件。

任何故障不得通过 `apply_patch`、`git commit`、直接编辑、`sed`、运行时模块覆盖、依赖包内 monkeypatch、替换原 Prompt、给原版程序增减模型参数来“修复”。**只在 StoryStudio 自有目录开发纯传输适配，不得复制原算法伪称原版被执行。** 原版自身缺陷 → 记录 `BLOCKED_UPSTREAM_IMMUTABLE` 并交 Controller。克隆或编译第三方时产生的构建输出放在与只读 Git checkout 分离的 `runtime/`，任何原版跟踪字节差异即黑名单。

## 工作流不可变

创作与审稿方法唯一来自原作者 `MintoTsukino/claude-novel-workflow` 的实际原文件，原版 NK/CritiCS 的功能和算法按各自源码执行。用户给定的君天离单 POV、2.3 Canon、单场先验、Flash-only 等限制独立生效。不得自创故事配比、六槽、24候选、额外评论透镜、多层审稿提前扇出、自签质量、自动整篇或五话生产。

## 必须执行的停止条件

仅以 `docs/governance/GOVERNANCE.md` 中 **B01–B14 黑名单**作为无法由当前 Atom 内机械修复解决的正式停工原因；已授权范围内的普通路径、编码、导入、命令定位等机械问题应定点修复并重验。**技术不支持严格零改动 + Flash-only 不能靠改开源源码绕过。**

任何阶段、工程状态或“HTTP 200”均不得冒称 `CREATIVE_EFFECT_ACCEPTED`。最终最小样本先提交原稿、前后上下文和批评证据给人类亲自读；用户批准前任何后续付费创作与扩量都是禁止的。
