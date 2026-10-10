# 官方初始导入与普通 INBOX 增量

固定基准：CNW `97ad71fe5e5e` 的 Workflow 01/02 与完整 `templates/CLAUDE.md`。正式初始入口 `cnw_project.py initial-import --project-root ...`；增量 `update-inbox --project-root ...`，或 `incremental-update --workspace-root ... --project-id ... --input ...`（PowerShell `project-incremental`）。

普通 `_INBOX` 项目完成语义初始导入即可增量，不要求本地旧 manifest。已有 INBOX 文件直接读取，不再复制成另一来源；外部 UTF-8 MD/TXT/JSON 文件按原字节 staging。无完整旧 manifest/index/candidates 时不创建/覆盖这些旧式文件。已有完整旧索引的项目复用旧 staging；有 pending 时先恢复并明确新输入尚未处理。

语义增量按来源路径/SHA 只选择新增或变化原件，读取旧 Canon/设计作判断，保留旧结论前缀和日志；只追加适当资料。场卡、Plot、普通审稿 Markdown 可成为增量消费者；正文与修订稿仍通过专门入口。增量不重复要求初始 bootstrap 文档。实际矛盾由模型识别后留双方待作者决定，执行器不自动裁决。

引用是来源线索，不等于语义核验通过。真实原件、固定方法、已传入项目文档分别绑定身份；额外未核实引用原样标记，不伪造哈希或作为验证支持。非 TODO 段须至少有实际输入绑定。模型返回官方工作/来源日志时保留内容，另追加确定性来源哈希和执行记账。

日志输出路由修复可使用已付费原响应：只允许 `allowed_existing_documents` 扩展两个官方日志路径，完整系统提示、原件、既有正文、其他 payload、模型、容量、端点/指纹均须相同；请求和 raw 仍核哈希。单独记录 `response_reconsume`，原回执身份不改。其他输入/方法变化不能走此分支。

无新增/变化立即报告 `NO_NEW_OR_CHANGED_SOURCES`，不付费。输出局限保留诊断；初始或增量完成不代表故事内容全正确或用户已接受。
