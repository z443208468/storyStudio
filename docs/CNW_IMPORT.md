# CNW 初始导入与增量更新

使用固定作者版本 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的 Workflow 01/02。
以下命令从仓库根目录运行；项目位于私有 `workspace`，原稿、归纳内容、API 回执和事务记录不进入 Git。

## 初始导入

先用 `cnw_project.py init` 建立项目，再将 UTF-8 Markdown、文本或 JSON 材料放进项目 `_INBOX`。
也可用现有 `import-source` 命令保存不可覆盖的原始副本与索引。原始暂存不代表语义导入完成。

```powershell
python tools/cnw_project.py initial-import --project-root D:\CangqiStudio\StoryStudio\workspace\my_project
```

该命令实际调用已配置的 DeepSeek Flash，沿用现有全局预算账本及环境变量 `DEEPSEEK_API_KEY`。
输入较长时按带重叠的片段读取，随后组织项目资料。原稿中的直接陈述、推断和疑问分别记录为
`CONFIRMED`、`INFERRED`、`TODO_CONFIRM`；Canon 中仅放来源支持的直接陈述。

输出包含作者要求的项目索引、来源日志、主题、Logline、项目设计、Arc 索引、Canon、人物资料和交接摘要，
以及工作日志、待确认问题、带来源哈希的分类记录。缺少事实时记录疑问，不补造事实。
来源直接陈述并不自动解决相互矛盾的材料。

## 增量更新

在 `_INBOX` 添加或修改材料后运行：

```powershell
python tools/cnw_project.py update-inbox --project-root D:\CangqiStudio\StoryStudio\workspace\my_project
```

仅对新增或哈希变化的材料执行抽取；读取既有 Canon 与设计文档作为比对依据。
既有内容保留，新增结论以带日期记录追加。矛盾同时引用旧、新说法，写入
`90_canon/unresolved_questions.md`，不替作者选定一个版本。
同实体、同属性的不同引文也会保守地列入待确认，可能包含同义表述。

`incremental-update --workspace-root ... --project-id ... --input ...` 会先暂存指定文件，再执行同一增量流程。
无新增或变化时不会调用模型。

## 失败与恢复

原始材料不会被归纳过程改写。每次保存选中材料的字节快照；模型响应与费用回执沿用生产调用留证。
写入采用前后内容校验和事务记录。中断后重跑同一命令可继续写入，不重新执行已完成的归纳调用。
如果来源或目标文档已被外部修改，命令会报告冲突并保留现场。

当前工程测试使用明确的模拟响应。它们覆盖入口、来源绑定、冲突保留、追加与恢复，不能证明真实小说材料的归纳质量。
