## 合并只读判断

本轮没有新C/T，**不作08接受、推送或09开启许可**。上一完整九类清单继续有效；此次新增治理问题并入同一清单。

### 1. AGENTS四行存在需要澄清的适用范围

实际新增位于 [AGENTS.md:25](D:/CangqiStudio/StoryStudio/AGENTS.md:25)。当前SHA：

`11f15061153c63570ef68b8a67f7addcc6c72cb8cef7421c1d71433ba36d67f1`

它将“新建或独立维护的小说项目”固定到`workspace/projects/<project_id>/`，同时把合同／Run／账本留在仓库外DataHome。**现有文字没有明确排除通用应用新建的注册项目，不能由Controller自行认定仅适用于手工小说目录。**

与冻结01–07的关系：

- 应用注册根是`DataHome/projects/<project_instance_id>`，同一实例承载已封存材料、Canon／Arc／Style、合同和Run。
- 显示`project_id`允许重复，不能替代内部实例身份作为唯一目录键。
- 把注册项目的材料移到`workspace/projects`、仅留下Run，会改变角色读集、合同路径、来源冻结、费用账户及签名绑定。
- “已有项目不移动”保护现存实例，但没有解决**将来由应用新建实例**的规则冲突。

**来源分类：新增治理变更，修改者／原始授权范围未核实。** mtime和Writer脚本未写该文件，均不足以证明是谁修改、或授权只限手工项目。

最小处理路径：

1. 保存当前四行及SHA，不回退、不擅自夹入08候选。
2. 查原始人类指令。若明确只是独立手工小说目录，可据该指令补充限定：
   > 本目录约定适用于独立手工维护的小说源项目；不改变R5通用应用已冻结的DataHome注册实例、材料／合同／Run所有权。应用仅按明确来源选择导入并封存必要材料。
3. 若原指令没有该限定，请所有者确认范围。若要求应用也拆分材料与Run，属于冻结存储合同变更，**不能在08文档整理中实施**。

当前仍可继续不依赖该解释的公开文档／归档整理；不得据四行创建、迁移或重构应用项目存储。

### 2. 当前实际源码影响没有扩大成存储改造

独立核对40项冻结07签名实现输入，当前实际字节变化只有`tools/cnw_export.py`。`git status`中其他核心文件虽有stat-modified显示，所查Git diff没有相应内容改动。

13项验证记录为exit0，raw SHA：

`c4c71be4eb3d0161c05229c409e5c26bc0a744b8debc9effdef5ff141e47be13`

其source清单**没有AGENTS**，因此不能用这批结果证明新增治理规则兼容。Export新SHA也不能继承旧许可。完整08候选仍需核最终物理／Git字节、实际导出语义、文档／parser及冻结功能影响。

### 3. 14项历史证据分类应保持明确

四项新R5源码preimage必须保留：

- `atom06_current_20261013/source_bytes/tools/p2_06_critics_run.py.source`
- `atom06_current_20261013/source_bytes/tools/p2_cost_guard.py.source`
- `atom07_nk_advisory_20261013/source_bytes/tools/p2_cost_guard.py.source`
- `atom07_w10_v2_20261013/source_bytes/tools/p2_cost_guard.py.source`

它们用于冻结证据和字节身份追溯，**不能因文件名含P2而退役或归入旧实验清理**。

其余10项顶层P2/P3记录目前仅列名、未改，这个边界正确。以后若要替换／移出当前HEAD，必须逐项证明原件备份、SHA、历史引用及新索引；零字符串命中不能直接授权删除，尤其不能删原裁决或把旧状态重新写成当前接受。

### 4. 共同收口要求

把治理范围澄清记录与原九类清单、历史映射、最终文档／导出回归、源码身份和保护SHA一起交精确08候选。当前源映射SHA`543946cf…98f70`匹配，但它仍是Writer映射记录，**不是归档或功能接受**。

```text
ATOM08_CURRENT_CLOSURE=NOT_ACCEPTED
GOVERNANCE_SCOPE=UNRESOLVED_FOR_NEW_REGISTERED_APP_PROJECTS
FROZEN_01_07_STORAGE=UNCHANGED; DO_NOT_RESTRUCTURE
NEXT_ATOM_PERMISSION=WITHHELD
GIT_PUSH_AUTHORIZATION=NONE
PRIVATE_MIGRATION=NOT_RUN
CUTOVER_BLOCKED=true
```

本轮未运行测试、修改文件或读取私有稿件／凭证；未将WIP和局部验证扩大为阶段签收。
