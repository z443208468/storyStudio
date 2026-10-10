# Codex 唯一执行入口 —— P3 原作者工作流逐文件映射施工

你是 StoryStudio 的单一 Writer；已有 `/root/g00_reviewer` 或当前获用户委任的**独立只读子智能体**是本项目 Controller，按真实源码/功能成果逐阶段 ACCEPT/RETURN。用户最高约束不由你放宽。

## 任务判定

此前的 NK、CritiCS、DeepSeek Chat 以及成本/证据机制已经真实部署并用于一次 smoke test。用户**没有要求推倒重建**。当前要完成的是以前的 P2 计划没有落实的**原作者 CNW 正式生产流水线**，具体缺口见 `MASTER_PLAN_P3.md`、`mapping/P3_SOURCE_TO_CODE_MATRIX.md`，禁止凭旧 EP001 短稿/旧 checkpoint 重新签产品完成。

## 第一个动作必须是“拉本机原文、完整读原文”，而不是开始改生成脚本

1. 对照当前 Windows 本地仓库：`git status --short --untracked-files=all; git rev-parse HEAD; git ls-remote origin refs/heads/main; git submodule status`。截至工单研究时，GitHub 主线 HEAD 为 `939eca90c030cf726b1879e2b1115f0e07ed6f6c`；远端旧候选分支已删除/不在分支列表。现场更新优先复用，禁止 reset/clean/force/rebase。
2. 检查固定作者仓库 `third_party/claude-novel-workflow` 的 HEAD 为 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`，保持 tracked 文件无修改。把本包提供的 `tools/capture_cnw_reference.py` 放到当前 repo `tools/`；运行：

   ```powershell
   & D:\CangqiStudio\StoryStudio\runtime\envs\critics-api\Scripts\python.exe tools/capture_cnw_reference.py --repo-root D:\CangqiStudio\StoryStudio
   ```

   成功后在本机 `runtime/reference/cnw_97ad71fe5e5e/` 能找到实际**原文件副本**，有 `CNW_LOCAL_REFERENCE_MANIFEST.json`，每个文件有 Git blob 和 SHA256。整套文档/模板真实按字节复制，不要只写“已阅读”。如果 pinned submodule 需初始化，只对现有固定 submodule 初始化，不拉别的版本。
3. 独立 Controller **完整读取本地** `episode_production_manual.md`、`manuscript_review_rubric.md`、`templates/config/workflow.template.yml`、`ai_roles.template.yml`、`plot/scene_cards/writing_brief` 三模板、`docs/THREE_LAYER_REVIEW.md`、`_workflows/03_revision.md`、`README.md` 与本包 `reference/CNW_ORIGINAL_SOURCES.md`。
4. 然后完整打开当前 `tools/studio.ps1`, `tools/p2_06_draft_run.py`, `tools/p2_06_revision_run.py`, `tools/p2_06_critics_run.py`, `tools/critics_bridge.py`, `tools/p2_cost_guard.py`, `config/production.example.json`, `implementation/*.md`，对本包 M01–M38 **逐项在实际本地代码核对**；若后来已经修复某项，复用并附当前 diff 与执行证据。

## 按 W00→W11 做，不要再设计一个替代版工作流

- 按 `MASTER_PLAN_P3.md` 的 W00–W11 依赖和 `spec/CNW_ROLE_INPUT_OUTPUT.md` 完成。**这些文件是执行合同，不是已落实功能。** 源码需按 `mapping/P3_SOURCE_TO_CODE_MATRIX.md` 对应 F01–F07 真正实现；缺功能就开发，已有工具就调用。
- 原作者 11 阶段：Plot → Scene Cards → Writing Brief → Prose → L1 → L2 → 5 independent lenses → 3 verifier → completeness → refine → re-review；在此之外再接既有 NK/CritiCS，各自真实消费、不要彼此冒充。
- 不要把作者的 5,000 日文字符机械换成中文字数。单场/整话在 Scene Card 和 Brief **事先写定合同目标与每段分量**，不能执行脚本私设 `500–700`；不合格的短稿不准 PASS，文学类 minor 也不应导致无意义删掉所有可见动作。
- 文本质量由 source beats、对白动作、人物区别、趣味/读者获得、前后文与规模共同确定，光“无 Canon 冲突”不合格。
- 只有 W09 里两份不同 fiction fixture 确认**新 ID 生产**，以及 W10 《苍歧》同一场真实重验后，才能称“正式生产流可用”。旧 `studio.ps1 scene` 的 `CHECKPOINT_REUSED` 只算旧历史回放。

## 成本/目录/提交约束

所有使用 DeepSeek 的原岗位调用要复用既有成本预留/usage ledger，模型 `deepseek-flash`，不能换 GPT，不自动充值，不把密钥写入公开仓。所有稿件、原始日志、作者示例参考、私有源稿置于 Git 忽略的 `workspace/`, `runtime/`, `runs/`, `deliverables/`。保留已有原厂固定子模块，生产增量能力只加自己的代码；修 bug 不需要重新问用户，真实跨越创作/付费授权才需用户决定。

## 绝不允许的“完成”说法

- 不允许“P2-07 已 ACCEPT，因此 P3 产品已 DONE”。
- 不允许“已写入 README 因此原作者整套方法已部署”。
- 不允许“Controller 检查了五个方面”代替五个独立审稿角色。
- 不允许“CritiCS Inspector 就是 CNW 三 verifier”。
- 不允许“输出少于合同是文学上自然凝练”而不提供前置批准和逐 beat 证据。
- 不允许 `studio.ps1` 只读 EP001 仍声称能生产新的作品。
- 不允许为了快重新用单句 Prompt 随意创造一套文学方法，或删除作者既有阶段。

## 提交验收形式

每阶段只交**当前 Atom** 的 `C/T + 原 source snapshot manifest hash + 真实源码 diff + 通过/失败的功能测试编号 + 本阶段私有产物 hash + Controller 的 ACCEPT/RETURN`。Controller 纠偏要写具体文件/函数/失败测试；可以在当前 Atom 修复正常 bug，不无限新增验收表。每阶段正常 push→remote readback，已通过的工具/请求无相关变更就不重放。P3 结束停在 `ENGINEERED_WORKFLOW_READY_FOR_USER_READING`，用户亲读前禁止 `USER_CREATIVE_ACCEPTED`，禁止真实批量写下一话。
