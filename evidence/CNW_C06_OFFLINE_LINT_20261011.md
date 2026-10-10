# C06 — J19 项目两层确定性 Lint 离线补证

2026-10-11。仅恢复用户指定的两条项目候选规则，并对已保存的同一 J19 v0/v2 离线执行。官方基准为 `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的 `docs/THREE_LAYER_REVIEW.md`、`templates/92_style_engine/forbidden_patterns.template.md`。两条具体正则来自本项目既有约束及本次用户指令，不冒充官方通用正则。

## 配置与来源

真实规则文件：`workspace/cangqi_cnw_public_restore_20261011/92_style_engine/forbidden_patterns.md`。现有 `tools/cnw_lint.py::project_rules()` 已能按 Layer 读取 `Rule | Pattern | Cap` 表格，处理正则内部管道字符并保留语义条目，因此本次无需修改加载器。

| Layer | Rule | Pattern | Cap | 当前规则源行 |
|---|---|---|---:|---:|
| 1 / surface | 演出说明标记残留候选 | `〔(?:镜头\|空间\|导演\|切点)[^〕\n]*〕` | 0 | 19 |
| 2 / structural | NPC明确内心断言候选 | `(?:思柔\|柳浅\|明穗).{0,12}(?:心里\|心中)(?:在)?(?:想\|觉得\|知道\|明白)` | 0 | 40 |

规则文件字节 SHA256：修改前 `4e22c8f3732d172808304a32fe8f2266eddfe152d3a0ffed8f3184f9b0347395`；修改后 `53fea6581547e6b4dd3473325cefeff6383ec1d9e1c0cca980c0b594207339bd`。

原 Layer 1 三条、Layer 2 八条语义规则的身份和描述均保留，Layer 3 原文保留。知识共享、物件推断、未来秘密和关系变化等仍由已有语义 Lens 判断。正则结果只为 `CANDIDATE_ONLY`，含上下文；不自动断言对白错误或把猜测判为事实错误。

## 真实离线执行

输入目录：`workspace/cangqi_cnw_public_restore_20261011/runs/CNW-RESTORE-J19-CURRENT-20261011-02/artifacts`。

新证据目录：`workspace/cangqi_cnw_public_restore_20261011/94_runtime/offline_lint/C06-J19-20261011-01`。四次均使用现有 CLI，各自退出码 0；完整报告分别为 `v0.surface.json`、`v0.structural.json`、`v2.surface.json`、`v2.structural.json`。

```powershell
$project = 'workspace/cangqi_cnw_public_restore_20261011'
$run = "$project/runs/CNW-RESTORE-J19-CURRENT-20261011-02/artifacts"
$output = "$project/94_runtime/offline_lint/C06-J19-20261011-01"
foreach ($version in @('v0', 'v2')) {
    foreach ($layer in @('surface', 'structural')) {
        .\runtime\envs\critics-api\Scripts\python.exe -m tools.cnw_lint $layer "$run/prose.$version.md" --rules "$project/92_style_engine/forbidden_patterns.md" --output "$output/$version.$layer.json"
    }
}
```

| 输入 | Layer | 可执行规则数 | 命中数 | 报告状态 | 命中行号/内容 |
|---|---|---:|---:|---|---|
| v0 | 1 | 1 | 0 | LINT_CLEAN | 无；findings=[] |
| v0 | 2 | 1 | 0 | LINT_CLEAN | 无；findings=[] |
| v2 | 1 | 1 | 0 | LINT_CLEAN | 无；findings=[] |
| v2 | 2 | 1 | 0 | LINT_CLEAN | 无；findings=[] |

四份报告均绑定上述新规则 SHA256，`text_modified=false`。零命中仅说明指定的两种形状没有匹配，不能证明语义无问题、成品通过或历史生产已执行新规则。

v0 原文件字节 SHA256 为 `53ae037f5a8925200a87d0217c7072405cc3669d758c92948fea7a2ebf1a3c9e`，v2 为 `96468c380f41da7c8ae353c21912e6d379de640b8b1632d82b01989c56aea200`。CLI 的 `source_sha256` 对读取后的 UTF-8 文本计算（Windows 换行归一化），分别为 `69c9b960ae7ef84845fa43d036f2d5c3ec628247f6218d32d6096324d7308d6a`、`6ea8caa065b860d9e0b03f861ddd9ac9e03cfc7a3939f22a057c3e9b7c77a3d2`，与文件字节哈希分开记录。

## 历史保护与验收范围

`evidence_summary.json` 保存规则前后哈希、规则行号、四份结果和六项受保护文件的前后字节哈希。原 run_state、历史两份 Lint、v0、v2 和费用账本全部未变；历史 Lint 仍如实记录当时 `NO_EXECUTABLE_RULES`。不更新旧 run 的冻结输入或运行阶段，不以新配置追认历史生产。

`python -m unittest tests.test_cnw_review`：12项离线测试通过（0.020秒），含两项新回归：四类标记/跨行边界/上下文，NPC断言及猜测仍只作为候选。新增付费调用 0；正文未删除或改写，未新增文学验收门。

独立只读 Controller 已对真实规则、四份报告、语义规则保留和六项保护哈希给出限定 ACCEPT；精确提交范围及正常 main 推送回读随交付核验。私有规则与正文通过独立本地补证包交付，不进入 Git。外部审查尚未独立核验私有材料，本次补证不替代外部审查，不更改当前候选 `REVISION_REQUIRED`、整体 Atom 或用户创意接受状态。
