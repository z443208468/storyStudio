# CNW 触发式标准操作与普通修订计划

固定方法：CNW `97ad71fe5e5e` 的完整 `templates/CLAUDE.md` Standard Commands / Folder Classification / Safety for Long Projects，Canon policy，以及各操作对应模板。它们不增加逐话生产阶段。

```powershell
pwsh -NoProfile -File tools/studio.ps1 standard-operation -ProjectRoot '<selected absolute project root>' -Operation extract_canon -SourceFile '<project-relative source>' -OperationTarget '当前章节的角色知情范围'
pwsh -NoProfile -File tools/studio.ps1 standard-operation -ProjectRoot '<selected absolute project root>' -Operation revision_plan
```

| Operation | 读取与产物 |
|---|---|
| `decompose` | 明确选定原稿及既有结构资料；章节/场景索引、场卡和 `07_draft/decomposition/` 派生分解副本。原稿与既有正文不覆盖 |
| `extract_canon` | 原文、Canon 与来源记录；`90_canon/` 有来源事实。角色知情和玩家披露、已发生和条件设想、观察和推断区分。未锁定摘要可保留旧字节后追加有日期/来源的更正；锁定决策不自动改变 |
| `jet_diagnostic` | 原稿、Arc/主题及项目已选 JET；诊断写 `91_jet_engine/diagnostics/` 和 `08_review/`。不替项目选 OS，不套示例故事 |
| `character_os` | 人物原文、行为/关系/时间范围；`03_project_design/characters/`，voice-only 用人物声线文件。观察与动机推断分开，不新增经历或晋升 Canon |
| `revision_plan` | 所有实际 MD/TXT/JSON review、有关正文、Canon 和核心；官方 `09_revision/revision_plan.md`。P0–P3、源章节/场、问题、修法、Canon 影响。核心改变标 `REQUIRES AUTHOR DECISION` |
| `revision_apply` | 用户明确选择的批准文件、计划及章稿的字节 SHA、保护资料与项目实例；只按已批准项修订，另存 `09_revision/approved/<批准文件SHA>/`，保存 diff、批准快照及工作日志。原稿、Canon 不改，不自动晋升 |

四种提取/诊断及批准后修订须指定实际源；可重复 `--source`（Python）或用 `-SourceFile` 数组（PowerShell）。`OperationTarget` 是范围说明，不替代来源事实。普通 Revision Plan 接受 beta/audit，没有五 Lens 回执不构成拒绝理由，也不伪造经过三反证的 Finding。

## Workflow 03 用户批准后的修订

先审阅 `revision_plan.md`，再由用户在项目 `00_meta/author_decisions/` 保存明确批准的 JSON，并显式执行：

```powershell
pwsh -NoProfile -File tools/studio.ps1 standard-operation -ProjectRoot <项目绝对路径> -Operation revision_apply -SourceFile 07_draft/episodes/EP001.md -RevisionApproval 00_meta/author_decisions/revision.json
```

批准文件字段：`schema_version=cnw_workflow03_user_approval_v1`、`author_decision=APPROVE_SELECTED_ITEMS`、`project_instance_id`、`plan_sha256`、`draft_sha256`（所选原章路径→字节 SHA）、`protected_sha256`（01_theme、02_logline、90_canon 全部 MD/TXT/JSON 文件路径→字节 SHA），以及 `approved_items` 列表，每项为 `chapter` 和 `plan_excerpt`。excerpt 是用户批准的计划中完整一行，不接受空的全计划批准。文件由用户明确选择，模型返回的批准字段不授予任何权限。

项目、计划、原章或保护资料身份变更会拒绝执行；每个章稿均须有具体批准项。标记 `REQUIRES AUTHOR DECISION` 的核心变更不在此普通修订入口执行，须单独处理核心/Canon 决策。此批准只授权指定修订项，不授权 Provider、费用、Controller 签收或正式晋升。实际注册 operation 授权适配已接入，要求独立 Controller 预检及 Owner Live/费用许可绑定真实请求、批准快照和保护资料。无许可的注册项目以及未绑定旧 V1 修订路线仍在 Key、slot、reserve、HTTP 前拒绝；生产信任未部署时不能执行真实修订。离线模拟消费成功不等于已验收 Live 修订。

候选稿、批准快照、修订记录和工作日志在同一 maintenance 事务中保存；中断后复用原回执恢复，不重新请求模型。不同批准文件产生独立目录；既有候选不得覆盖。正式晋升仍需单独明确操作与对应审查。

模型返回文件映射与处理报告，执行器实际落盘；不是只导出提示词。完整官方方法与项目文件全文进入请求，归档原 request/raw。路径身份统一；选定原稿、master Canon、既有锁定记录及跨职责路径拒绝覆盖。报告/日志与选定原文碰撞在模型调用前拒绝。Canon/角色既有记录仅允许完整旧字节后追加，更正前的旧字节留历史。真正矛盾保留双方交作者决定。

`extract_canon` / `character_os` 更新既存资料可返回 `append_sections`，只提供带日期/来源的新段落，执行器保留原字节（含混合换行）后追加。不能与 `documents` 使用同一路径，不能借此改变原稿、master Canon 或已锁定记录。锁定识别依据明确状态字段、标题、表格状态；官方人物表 `Canon Status=Canon` 也表示锁定。一般政策说明中提到 locked/Canon-promoted 不表示整个派生文件已锁定。

所有操作复用 maintenance 事务、恢复、来源/适配身份、成功回执及成本护栏，并记录读了什么、创建/更新、假设、未决问题和一个下一动作。工作日志为操作记录，不作为标准操作故事输入；后续合法追加保留完整旧日志前缀，可复用不变结果，删除/替换旧记录仍拒绝。

本轮 Canon Extraction / 普通 Revision Plan 有真实代表；其他三项为离线，Live 未运行。不得用计划生成成功声称批准、晋升或创意通过。
