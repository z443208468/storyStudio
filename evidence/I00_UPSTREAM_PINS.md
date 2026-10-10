# I00 上游固定与不可变性记录

状态：候选，等待 Reviewer 与 Controller 对精确提交/树及远端回读签收。

## 根仓库基线

- I00 起始本地 HEAD：`046365ef7e61ffc913a704e3a2e40abcd41fd28a`。
- 执行前工作树：干净。
- 执行时远端 `main`：commit `06c66de7c7f18263039ea19a47e84c29716cde4b`；其 tree 本轮未重新核验。
- 操作：仅按活动计划 I00 增加三个 Git 子模块、项目自有 `.gitignore` 与本证据文件；未安装、构建、编译或运行上游工具，未读取密钥、调用 API 或读取源稿。

## 上游身份与许可证

| 名称 | 来源 URL | 固定 commit | commit tree | Git link | 许可证与 LICENSE SHA256 |
|---|---|---|---|---|---|
| claude-novel-workflow | `https://github.com/MintoTsukino/claude-novel-workflow.git` | `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` | `f06a7b693fda124761b69ad40ab483cc82960219` | `third_party/claude-novel-workflow` | `LICENSE`，文档/模板为 CC BY 4.0；示例故事材料另受保留版权条款约束。SHA256 `D22CCE5D74CE7DE6FD0857BBD385C1102EAECE72058BC200AF51EDCE0285B36B` |
| narrative-keyframing | `https://github.com/zhangchaodesign/narrative-keyframing.git` | `b857f34b7d371ae82c30e00eb021884c14d08ae9` | `3960b25cb52265933e0fa4897d1319ad6161bf9c` | `third_party/narrative-keyframing` | `LICENSE`，MIT。SHA256 `FE246457C6DF082E7AACA06CFA4DFAA819625FABAC934294B5F3ECCF7C2AB51D` |
| CritiCS | `https://github.com/EMNLP-2024-CritiCS/Collective-Critics-for-Creative-Story-Generation.git` | `fbf66cbc913012c6f80af1687e27f0ce350475e3` | `c48be7d9cbeb680238a9e832be86bdf167c305a9` | `third_party/CritiCS` | `LICENSE`，MIT。SHA256 `60D066E7EA78E1953DE130D4BFC5A7E346A5113D396690ABDB2FD99A6D6E8B04` |

许可证路径由各固定 commit 的只读 `git ls-tree -r --name-only HEAD` 查询确认；本记录不重新发布许可证文本。Git index 中三个路径均为 mode `160000`，其 gitlink SHA 与固定 commit 一致。

## 工作区核验

- 三个 Vendor checkout 的 `HEAD` 分别等于上表固定 commit。
- 三个 Vendor checkout 的 `git status --porcelain=v1` 均为空。
- 根 `.gitignore` 逐条核验忽略 `/inputs/private/`、`/workspace/`、`/runtime/`、`/runs/`、`/.env` 与 `/.env.*`，并豁免 `/.env.example`；`git check-ignore -v --no-index` 对上述路径返回对应规则。
- 没有创建或读取任何密钥文件，也没有输出密钥内容。

## 原始命令回显摘要

```text
VENDOR=claude-novel-workflow EXPECTED=97ad71fe5e5e76a82275c6c63d4add06fb60ab6e ACTUAL=97ad71fe5e5e76a82275c6c63d4add06fb60ab6e TREE=f06a7b693fda124761b69ad40ab483cc82960219 DIRTY_COUNT=0
VENDOR=narrative-keyframing EXPECTED=b857f34b7d371ae82c30e00eb021884c14d08ae9 ACTUAL=b857f34b7d371ae82c30e00eb021884c14d08ae9 TREE=3960b25cb52265933e0fa4897d1319ad6161bf9c DIRTY_COUNT=0
VENDOR=CritiCS EXPECTED=fbf66cbc913012c6f80af1687e27f0ce350475e3 ACTUAL=fbf66cbc913012c6f80af1687e27f0ce350475e3 TREE=c48be7d9cbeb680238a9e832be86bdf167c305a9 DIRTY_COUNT=0
```
