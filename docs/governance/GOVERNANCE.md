# StoryStudio 治理 P3：原方法落实与产品质量复核

## 1. 当前权威与状态

当前唯一活动计划为 `plans/MASTER_PLAN_P3.md`，按 W00–W11 及相应验收合同执行。P2 的计划、实现、日志和签收保留为历史事实；不得把历史工程 ACCEPT 扩写成 CNW 全流程或文学质量通过。P2-06/07 的旧 EP001 定位为 `HISTORIC_SMOKE_SAMPLE`。当前状态以 `evidence/P3_CURRENT_STATE.md` 为准。

已验证的环境、NK Live、CritiCS Live 可按原身份复用；CNW 全生产仍为 `NOT_VERIFIED`，产品里程碑重新打开。此分类用于防止状态混淆，不撤销既有 P2 技术签收。

## 2. 方法与适配边界

CNW 固定上游公开文档、模板和方法为工作流依据；项目可增加本地 Canon、知识边界、语言适配与确定性调度。保留 Plot → Scene Cards → Writing Brief → Prose、Layer 1/2、五个独立 Lens、三个独立 Verifier、Completeness、Refine、Re-review 和晋升/索引职责。NK POV 与 CritiCS 剧情批评按其原职责接入，不能替代 CNW 角色。

适配应记录来源与实际运行证据。不宣称私有脚本、研究模型、论文复现实验或作者专属评分体系已原样部署。输出规模在模型调用前由场景合同和可追溯的内容节拍确定；不得以旧的 500–700 字限制或事后降标通过。

## 3. Writer 与独立 Controller

Writer 执行；受委任的独立只读子智能体担任 Controller。Controller 按 P3 Controller 指令审查当前 Atom 的原件、实现、差异、测试与 C/T，给出 ACCEPT 或具体 RETURN。Writer 不得自签。Controller 工程签收不代替用户对作品的创意接受。

验收限于当前阶段、必要依赖和实际功能/安全影响。对可逆机械问题直接修复并复验；对无关问题不扩范围。已经由同一身份验证的环节可复用。API 调用受既有 DeepSeek Flash 授权和费用护栏约束，不改用其他供应商、不泄露密钥、不超出剩余预算。

## 4. 作品和私有数据

源稿、密钥、请求响应、运行产物和交付稿保留在忽略目录。不得把私有创作材料推入公开仓库。只重做已批准的 J19 插场，不扩写第二场或批量内容。Canon、时间线、人物知识边界和前后锚不得被候选正文反向改写。

`USER_CREATIVE_ACCEPTED` 只能由用户亲读后决定；工程完成状态可记为 `ENGINEERED_WORKFLOW_READY_FOR_USER_READING`，不能替代用户判断。

## 5. Git 与阶段记录

当前沿唯一 `main` 分支推进。每个 W 阶段先冻结候选 C/T，由 Controller 独立检查；接受后正常提交、推送并回读远端。禁止创建多余分支、force-push、破坏性 reset/clean，或覆盖未审查的用户 WIP。状态记录忠实区分候选、签收与推送，不伪造审查 ID 或供应商证据。
