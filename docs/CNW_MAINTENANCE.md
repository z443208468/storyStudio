# CNW 官方项目维护入口

固定方法：`claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的 Workflow 04、05；不加入逐话 11 阶段。

入口使用实际项目材料和固定官方方法。拥有 `DEEPSEEK_API_KEY` 不表示已获运行或费用授权；工程 Controller 签收、可信生产签收、用户 Live/费用权限各自独立。

当前注册项目的维护和缓存恢复必须先经过共同授权门。`cnw_operation_authorization` 已实现实际 operation Run 的请求绑定、可信 Controller 预检和独立 Owner Live/费用许可消费；生产信任尚未部署。没有有效许可仍在 Key、slot、reserve、HTTP 前拒绝。已验证的注册项目路径使用临时虚构项目和明确模拟回执，只替换最终模型边界。下列命令是实际接口说明，本轮文档核对不执行它们。旧显式 V1 路径继续遵守其原身份和费用政策，新项目不继承旧 campaign 授权。来源、请求、回执和恢复事务保留在私有项目目录，密钥不进入请求存档或 Git。

## Canon Audit

```powershell
python tools/cnw_project.py canon-audit --project-root '<selected absolute project root>'
python tools/cnw_project.py canon-audit --project-root '<selected absolute project root>' --scope light --chapter 07_draft/episodes/ep01.md
python tools/cnw_project.py canon-audit --project-root '<selected absolute project root>' --scope targeted --target timeline
```

全量默认交叉读取全部 `07_draft/`、`03_project_design/`、`90_canon/`、`06_plot/`。Brief/索引标为规划资料，不充作实际故事。轻量选新增正文，仍读 Canon/设计/Plot；定点明确子系统，仍跨实际来源查找。

完整原样报告：`08_review/continuity_audit.md`。行动项文本去重追加：`90_canon/unresolved_questions.md`，既有作者处置保留。追加 `00_meta/ai_work_log.md`。不改锁定 Canon、不自行裁决，不自动启动正文或修订。下一步按官方进行作者分流；需要正文修改时使用 Workflow 03。

## Handoff

```powershell
python tools/cnw_project.py handoff --project-root '<selected absolute project root>' --pipeline
```

跨当前项目资料生成官方八节紧凑交接；自动流水线接收时 `--pipeline` 增加 Context Pack。统计分开正文和规划文件，Unicode 非空白字符数不冒称词数；实际章数、最新章及完成比例依项目证据，缺证据留未知。

发布 `93_exports/handoff_brief.md`；旧交接原字节保存在 `93_exports/archive/handoff_<SHA256>.md`；追加工作日志。Handoff 读取当前审计和未决问题，不代作者解决它们。

PowerShell 同步入口：`tools/studio.ps1 canon-audit -ProjectRoot '<selected absolute project root>' -AuditScope light -AuditChapter '<project-relative prose path>'`；定点用 `-AuditScope targeted -AuditTarget timeline`。交接用 `handoff -ProjectRoot '<selected absolute project root>' -Pipeline`。

## 重入与证据

`cnw_maintenance.run_maintenance(..., prepare_only=True)` 是实际 Python 准备接口，冻结请求及其 RunAccount 并发布授权请求，不执行文学模型。PowerShell 没有同名开关。生产消费须重建真实请求、资料/实现身份、stage/role/cap/extra 与许可绑定，并使用同一费用账本及并发 slot；普通 JSON、创意批准或工程签收不能代替可信许可。

项目锁、完整文件快照、原请求/raw 回执、preimage/postimage journal 和 pending 指针支持同一事务恢复。来源或目标在执行中被外部修改时报告冲突；适配身份改变后不按新方法恢复旧 pending。

同一输入的已完成重入比较合法发布后来源身份、官方/项目指令、实际请求适配及模型配置，重新核原 request/raw 回执。在其合法权限内复用匹配回执；模拟会话仅复用绑定同一临时实例、Run、请求和输出的 `MOCK_ONLY / SIMULATED` 回执。无授权不能借 pending 或缓存发布。自身问题清单、日志和交接发布不要求同一次操作再次请求模型；历史已付费回执保留原身份，模拟回执不能当成 Live。

模型错误判断原样保留供作者审查。此入口不保证每条 Finding 正确，不追求把诊断样本手改到完美。
