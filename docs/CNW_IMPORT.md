# CNW 初始导入与增量更新

固定公开方法来源：`MintoTsukino/claude-novel-workflow@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`。
StoryStudio 的 Workflow 01/02 执行器显式加载该版本的操作提示词；本地文件不会因 API 调用而自动加载。

## 通用注册项目路径

新项目必须在显式选择的私有 DataHome 中注册。以下命令只说明命令结构，不会为你选择目录或授予 Provider/费用权限：

```powershell
.\tools\studio.ps1 setup -DataHome "<selected-private-data-home>"
```

选择且只运行以下一种新项目创建方式：

```powershell
# 空白项目，不导入来源
.\tools\studio.ps1 project-init -ProjectId "<project-id>" -DataHome "<selected-private-data-home>"

# 或：创建项目、初始化模板并封存第一份来源
.\tools\studio.ps1 project-import -ProjectId "<project-id>" -DataHome "<selected-private-data-home>" -InputFile "<source-file>"
```

这两个命令都会创建新的项目实例；不要对同一新项目连续执行。需要将原稿加入已经存在的项目时，使用：

```powershell
.\tools\studio.ps1 import-source -ProjectRoot "<registered-project-root>" -InputFile "<source-file>"
```

`project-import` 与 `import-source` 保存原稿字节、不可变来源修订和待确认候选；它们本身不运行完整语义 Workflow 01，也不调用 Provider。使用命令输出中的 `project_root` 作为后续明确项目上下文。

## 语义 Workflow 01 与 Workflow 02

完整 Workflow 01 由 `initial-import` 执行。它读取项目 `_INBOX`，调用配置的语义组织流程，并使用当前共享 Provider/费用守卫：

```powershell
python tools/cnw_project.py initial-import --project-root "<registered-project-root>"
```

这是可能产生费用的真实 Provider 操作。R5 通用化施工期间不得执行；只有单独取得 Live/费用授权并满足项目预检后才可调用。没有这项授权时，保留 `SOURCE_IMPORTED` 与 `TODO_CONFIRM` 状态，不能把原稿封存结果称作语义导入完成。

完成 Workflow 01 后，`project-incremental` 会向现有项目追加来源并运行 Workflow 02：

```powershell
.\tools\studio.ps1 project-incremental -ProjectRoot "<registered-project-root>" -InputFile "<new-source-file>"
```

该操作要求已有 `00_meta/import_state.json`，并调用 Provider 与共享费用守卫，可能产生费用；它同样需要单独的 Live/费用授权，R5 通用化施工期间不得执行。若只需封存新增来源而暂不做语义处理，使用 `import-source`。增量来源与语义结论应分别保留来源身份、SHA、状态及冲突，不得自动把冲突提升为 `CONFIRMED`。

## 旧项目根兼容入口

`initial-import --project-root ...` 与 `update-inbox --project-root ...` 仍兼容已有私有项目根。它们需要显式根路径，不得默认回退到旧项目目录。新注册项目的原稿封存应使用上述注册入口；语义 Workflow 01/02 与原始来源导入是不同操作。

原始文件、语义输出、运行回执和费用账本都留在项目私有数据目录，不进入 Git。

## 失败与恢复

导入流程使用来源快照和事务记录；原始材料不被归纳流程改写。中断恢复必须匹配已冻结的输入与前态；外部修改或冲突时保留现场并返回错误，不能覆盖旧结果。

自动化测试使用明确标记的模拟响应。它们能验证请求构造、消费者、冲突保留与恢复路径，不能证明真实材料的语义归纳质量或 Live Provider 可用性。Workflow 01/02 的通用注册项目消费效果仍须由 R5 对应 Atom 的离线全链和独立 Controller 验收。