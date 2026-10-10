# CNW 官方项目维护入口

固定方法：`claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的 Workflow 04、05；不加入逐话 11 阶段。

入口会实际调用已授权 DeepSeek Flash，使用既有共享成本护栏；进程需已有 `DEEPSEEK_API_KEY`。来源、请求、回执和恢复事务留在 Git 忽略的私有项目目录，不把密钥写入请求存档。

## Canon Audit

```powershell
python tools/cnw_project.py canon-audit --project-root D:\CangqiStudio\StoryStudio\workspace\PROJECT
python tools/cnw_project.py canon-audit --project-root D:\CangqiStudio\StoryStudio\workspace\PROJECT --scope light --chapter 07_draft/episodes/ep01.md
python tools/cnw_project.py canon-audit --project-root D:\CangqiStudio\StoryStudio\workspace\PROJECT --scope targeted --target timeline
```

全量默认交叉读取全部 `07_draft/`、`03_project_design/`、`90_canon/`、`06_plot/`。Brief/索引标为规划资料，不充作实际故事。轻量选新增正文，仍读 Canon/设计/Plot；定点明确子系统，仍跨实际来源查找。

完整原样报告：`08_review/continuity_audit.md`。行动项文本去重追加：`90_canon/unresolved_questions.md`，既有作者处置保留。追加 `00_meta/ai_work_log.md`。不改锁定 Canon、不自行裁决，不自动启动正文或修订。下一步按官方进行作者分流；需要正文修改时使用 Workflow 03。

## Handoff

```powershell
python tools/cnw_project.py handoff --project-root D:\CangqiStudio\StoryStudio\workspace\PROJECT --pipeline
```

跨当前项目资料生成官方八节紧凑交接；自动流水线接收时 `--pipeline` 增加 Context Pack。统计分开正文和规划文件，Unicode 非空白字符数不冒称词数；实际章数、最新章及完成比例依项目证据，缺证据留未知。

发布 `93_exports/handoff_brief.md`；旧交接原字节保存在 `93_exports/archive/handoff_<SHA256>.md`；追加工作日志。Handoff 读取当前审计和未决问题，不代作者解决它们。

PowerShell 同步入口：`tools/studio.ps1 canon-audit -ProjectRoot <私有项目> -AuditScope light -AuditChapter <正文路径>`；定点用 `-AuditScope targeted -AuditTarget timeline`。交接用 `handoff -ProjectRoot <私有项目> -Pipeline`。

## 重入与证据

项目锁、完整文件快照、原请求/raw 回执、preimage/postimage journal 和 pending 指针支持同一事务恢复。来源或目标在执行中被外部修改时报告冲突；适配身份改变后不按新方法恢复旧 pending。

同一输入的已完成重入比较合法发布后来源身份、官方/项目指令、实际请求适配及模型配置，重新核原 request/raw 回执，复用已付费结果。自身问题清单、日志和交接发布不会导致同一次操作重复收费。

模型错误判断原样保留供作者审查。此入口不保证每条 Finding 正确，不追求把诊断样本手改到完美。
