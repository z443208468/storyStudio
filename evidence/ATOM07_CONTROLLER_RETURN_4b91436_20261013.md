```text
CONTROLLER_VERDICT=RETURN
ATOM_ID=ATOM07
REVIEWED_COMMIT=4b91436dcdb7afe18b2bcc1503e49cdbd3e57a21
REVIEWED_TREE=b112fa7d42d6264d732cbfc525083929d2393ee2
REVIEWED_PARENT=50ee75fa147c068d84dd35e5375c1bc668cf2c46
REVIEWED_PLAN_SHA=AE5A1959EEAB75AD6A8F41460C38BF9678284C1D51A8D63B25CE37F7CB4F5183
GIT_PUSH_AUTHORIZATION=NO_PUSH_AUTHORIZATION
```

**唯一剩余根因仍是Windows大小写所有者识别。**[cnw_runner.py:505](/D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:505)在`resolve(strict=True)`后，仍以大小写敏感的`.name`识别`imports/maintenance/94_runtime`。

当前负例覆盖“实际目录小写、传入路径大写”。若**磁盘实际目录本身大写**，Windows仍允许公共操作使用小写路径访问，但`resolve()`返回实际大写拼写；此处仍不能识别操作所有者。再重标schema，便可能进入旧Provider门。

最小修正是对这两个保留父目录名使用`casefold()`比较；保留先执行的no-traversal/reparse检查。现有同一个测试加入“实际目录大写＋schema重标”的高/低入口负例，断言在slot、缓存、reserve、HTTP前拒绝。不扩展授权系统。

我已读取七路径精确差异、最终8项测试、三处缓存`extra=None`、原始失败及纠偏。唯一登记、严格模拟标记、实际请求/输出绑定、缓存恢复门和最终模型替身方向可保留；V1 model/cap/fingerprint检查仍在。本候选未修改CNW角色消息、读集、三票阈值或Canon/Workflow业务职责。

| 裁决项 | 当前结论 |
|---|---|
| CODE_FIX | **RETURN**：上述同根因分支未闭合 |
| ATOM07_OFFLINE_ENGINE | **RETURN**，停留07 |
| METHOD_FIDELITY | 本差异范围未观察到CNW方法漂移；不能替代候选整体接受 |
| EARLY_E2E | 本候选精确冷clone尚未终态，暂不签收 |
| 历史保护 | 直接回读TS状态和真实账本仍匹配冻结SHA；未运行生产或恢复 |
| GIT_PUSH | **禁止推送4b91436** |
| 下一Atom | 尚不进入08 |

原始日志哈希已核对。`../`本来被原路径门拒绝；我此前认定其为生产旁路的论证错误，原指导与纠正应保留。真实大小写别名红测确实到达禁止的mock cost guard四次，零实际请求。新根因针对实际目录拼写，不能由已有别名绿测证明关闭。

冷clone当前只有中间输出；继续保存它的最终raw和身份，不把后来返修追写到此候选。修正后追加正常提交、新C/T及受影响复验，再交我审查。限定接受和推送回读后才进入08安全源码/文档；09仍承担包job自动完整调度至导出的产品门。

`W10_ATTESTATION_PENDING`、TS Live未授权、恢复资格未成立、`CUTOVER_BLOCKED=true`保持。Controller未跑测试、改文件、调用Provider或提交推送。
