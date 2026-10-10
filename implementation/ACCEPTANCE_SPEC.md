# P2 验收规范：有界证据、真实效果、独立判断

## A1. 三种证据，不能互相替代

1. 离线测试证明输入接线、代码行为、解析和保护规则；不证明真实 Flash 连通。
2. 真实请求证明实际工具/供应商返回和消费链；不证明故事好看。
3. Controller 完整读源与成品，证明明显事实/结构问题已检查并纠正；用户最终审阅才证明其主观满意。

不要从生成器自己的“我符合要求”字段推导通过。测试可用预写固定返回确认数据流，但 oracle 来自被检验合同和独立标记，而不是让同一个模型先编答案再给自己评分。

## A2. 本轮固定检查集

这些是必要的功能检查，不要求新建测试平台。可实现为一个 Python unittest 文件和一个 TypeScript/HTTP 检查入口，结果汇入 `P2_ENGINEERING.md`；用现有轻量测试框架即可。

| 编号 | 输入/动作 | 必须观察到的结果 | 证据性质 |
|---|---|---|---|
| V01 接续安全 | 现有 WIP/已完成子模块 | WIP 保留；已有源不重克隆；没有 reset/clean/force | 本地 Git 原件 |
| V02 可重建补丁 | 相同 source+patch+lock，两次独立导出 | 受控源码 hash 一致；原参考未被修改 | 文件/锁对照 |
| V03 CritiCS parse/import | 实际生产环境导入三个指定入口 | 无 SyntaxError/缺依赖；解释器身份明确 | 真命令与退出码 |
| V04 Voice 输入 | 带唯一标记的真实五句输入 | 标记出现在最终 Voice 请求中，而非只在调用参数里 | 离线请求捕获 |
| V05 剧情角色链 | persona 含年龄数字；三份不同批评；多行 Question | 4 个 persona 不截断；三批评进入 Inspector；原选中问题完整返回 | 固定离线响应 |
| V06 文字角色链 | Image/Voice 两份不同建议 | 原 Leader 请求实际包含两份意见，输出不被 Writer 替换 | 固定离线响应 |
| V07 非法响应 | 空 JSON、少项/多项、空 reflection、坏标签、截断 | 明确失败/修复；不返回自填合格对象 | 离线负例 |
| V08 真实出站 | NK 与 CritiCS 的 live 请求 | host=官方 DeepSeek；请求 model=deepseek-flash；真实响应原件保留 | Live，不得 mock |
| V09 Key 与私有内容 | staged 清单、公开文件、日志写入路径 | 无 Key/Authorization 值、无原稿/完整 prompt/样本正文公开提交 | 本地扫描+人工看差异 |
| V10 来源与知识 | 源 ZIP/索引/样本合同 | 输入身份、角色已知、J19–J32 条件不被伪线性化 | 源文对照 |
| V11 NK 实际消费 | request→response→Brief | 对应段/字段可定位；不是调用后丢弃 | 原文件+真实 hash |
| V12 CritiCS 实际消费 | Plot→意见→改 Plot，原句→意见→Revision | 原函数真实执行；采用/拒绝有依据 | Live + 文字对照 |
| V13 全场质量 | 前文→完整修订稿→后文 | 无重大 Canon/POV 错、无占位/截断，有行动和落点 | Controller 全文阅读 |
| V14 断点恢复 | 中断后启动同一 run，成功步骤已存在 | 不重复成功付费；不把未知结果直接标成功；已有输出不覆盖 | 调用计数和日志 |
| V15 最终复用 | 新 PowerShell 启动并加载已有样本导出 | 实际入口可用，输出完整可读，未新写第二场 | 非付费功能验证 |

离线检查需要否定案例：只放成功样本会漏掉“给假 JSON 也算成功”。安全检查不能只确认 .gitignore 存在，还要检查实际 staged 文件。

## A3. 方法保留检查

Controller 对照固定上游文件及补丁，确认：

- CNW 的 Canon/项目设计/Plot/Card/Brief/Prose/Review/Revision 职责未被自创系统取代；模板实例的项目填写与源模板分开。
- NK 的实际路由与业务 prompt 仍处理原事件、人物、视角任务；变的是 provider/协议/必要安全与解析，不是重写为无关任务。
- CritiCS 的 `three_critic()` 仍有 persona→三类批评→Inspector，`Two_refinement()` 仍有 Image/Voice→Leader，`modifiedStoryline()` 实际接收原反馈。
- 更换基础模型意味着不宣称论文原效果复现；修掉漏输入/坏解析是恢复函数应有作用，不是取消方法。
- 未启用原研究功能明确不声明完成，不因未跑整个仓库而阻止当前实际路径验收。

CNW 三层检查也须落实：有限表层检查、上下文排除误报、Controller 全场语义审阅；这三项不能被单纯的文件存在性检查取代。

模板 hash 不同不自动失败：先看差异是否为项目实例/漏字段修复/序列化要求。反过来模板 hash 相同也不自动成功：正文根本没传入就必须退回。

## A4. 每阶段一次实质签收，不形成自引用循环

Writer 把精确代码候选 C/T 和私有产物 manifest 交同一个 Controller，Controller 读原件并输出：

```text
STAGE: P2-xx
VERDICT: ACCEPT / RETURN / EXTERNAL_INPUT_NEEDED
REVIEWED_CODE: <actual commit/tree>
REVIEWED_ARTIFACT_MANIFEST: <actual sha256 or NOT_APPLICABLE>
CHECKED: <actual code/input/output examined>
FINDINGS: <specific defects, if any>
NEXT: <authorized next step or exact corrective work>
```

用户已经委任该 agent，不再加一层“请用户批准这份 ACCEPT”。普通推送和远端 C/T 相同的回读给 Controller 核对；收到明确一致结论后，下一阶段可开始。

签收日志是“引用此前对象”的记录，不要求其 commit 同时包含自身 SHA，也不要求每次补日志重跑工具。只追加状态不触发新内容生成；任何代码/输入变化按 A5 影响图处理。

## A5. 受影响重跑，不从零开始

| 变化 | 最早重验环节 | 可直接保留 |
|---|---|---|
| 只有治理说明/状态指针，生产合同未变 | 引用及权限核对 | 已验证环境和文本调用 |
| CritiCS provider/依赖/解析补丁 | 对应导入、离线链、必要 live | 正确源稿、与缺陷无关的 NK 输出 |
| Voice 漏正文修复 | Voice 与其 Leader、受影响 Revision | 不受影响的 Plot/NK |
| NK 输出/schema/provider 修复 | NK route 与 Brief/后续真正受影响部分 | 源稿、合法 Plot |
| 源稿版本/人物知识变化 | Canon/样本合同及依赖的全下游 | 工具部署、独立协议测试 |
| Plot 行动变化 | Card→NK（必要时）→Brief→正文→相关批评/修订 | 固定环境和独立协议测试 |
| 只有正文个别措辞变化 | 对应句段、全文衔接复读 | 合法 Plot、未影响的工具结果 |
| 导出 CSS/编码变化 | 阅读文件导出检查 | 所有模型输出，不再收费 |

“必要时”不是可以随意省略：由 Controller 指明此次差异改变了哪份输入；如果某下游缓存的 input hash 已变，不能继续声称是当前版本结果。

## A6. 防止验收跑偏

优先拦截：实际缺正文、方法被替换、原稿泄露、模型错误、重复收费、缺完整戏、下一锚点被改坏。

不把以下项目当作单独停工原因：表格列顺序、命名不够漂亮、与结果无关的全仓死代码、旧历史文件仍含旧字样、原版 bug 修复本身、用户没有再次打“批准”。

控制器退回必须给修复对象和预期差异，不得只说“继续补齐证据”却不说明缺什么功能事实。Writer 不得为了获得 ACCEPT 删掉必要测试或改成自评。

## A7. 最终状态

`DEPLOYED / WORKFLOW_METHOD_REVIEWED / LIVE_CHAIN_VERIFIED / ONE_SCENE_DELIVERED / READY_FOR_USER_REVIEW` 分别有相应证据后可填写。

只有用户真实读并接受，才填写 `USER_CREATIVE_ACCEPTED`。未读的状态是等待首场审阅，不是可以冒称作品质量达标，更不授权自动扩大为整幕。发生真实外部阻塞时交付已完成文本及具体不足，明确不算完成，不能用“失败已签收”掩盖目标未达。
