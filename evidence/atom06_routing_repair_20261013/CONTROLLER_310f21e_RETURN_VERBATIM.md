## 精确裁决

```text
C=310f21e42e72cd03b824512683b80329ea833048
T=063a7aa7f40e984f716b5f2cca19d0e860174b91

CURRENT_ATOM_CLOSURE_VERDICT=RETURN
METHOD_FIDELITY_VERDICT=RETURN_INPUT_MAPPING_EXTENSION
FROZEN_FUNCTION_REGRESSION_VERDICT=RETURN_CURRENT_EXTENSION_GUARANTEE
FREEZE_SCOPE=REVIEWED_EVIDENCE_ONLY_NOT_ATOM06_ACCEPT
NEXT_ATOM_PERMISSION=ATOM07_WITHHELD
GIT_PUSH_AUTHORIZATION=NO
```

### 唯一已确认阻断根：原生attempt绑定仍未重验任务材料定位和适配选择

[validate_binding](D:/CangqiStudio/StoryStudio/tools/cnw_native_pack.py:399)已经正确比较原注册源映射、材料文件集合及其SHA，但没有从已核原声明重新验证这些字段：

- `original_work_order`
- `native_context_file`
- `native_index_file`
- `adapter_choices`中的第五Lens职责及integrations

正常构造器[_task_index](D:/CangqiStudio/StoryStudio/tools/cnw_native_pack.py:313)按原声明生成它们；读取器却仍信任binding自身的选择。

例如，将任务A的`original_work_order`改成同组任务B已经封存的requirements文件，保留原任务声明、完整材料集合和所有原材料SHA，并同步重算derived/binding/contract SHA：

- [frozen_task_sources](D:/CangqiStudio/StoryStudio/tools/cnw_task_requirements.py:182)会读取改选文件；
- `verify_bound_task_context`从同一个改写index重新推导；
- [_draft](D:/CangqiStudio/StoryStudio/tools/cnw_native_pack.py:347)及合同比较也从该index读取要求。

因此，现有SHA闭合不能证明合同仍消费声明任务A的要求。第五Lens/辅助开关存在同类自引用问题。这违反§0.3a完整映射及06项目职责绑定；生产门目前关闭，不消除这项实现缺口。

**最小修正：**依据已核`source_task.declaration`、原项目组及包SHA重算上述固定定位和adapter字段，再比较binding；保留现有源映射、文件集合及SHA检查。

**最小复验：**

1. 同组不同任务requirements互换，同步重算派生及合同身份，仍须拒绝。
2. context定位替换或非法新增、原index定位替换须拒绝。
3. 第五Lens职责或integrations改写并重算SHA须拒绝。
4. 合法原生attempt及旧v1/offline消费者保持原行为；原件不改，拒绝前零Run执行、Provider和费用调用。

只需修这个根及受影响验证，不增加验收平台。

## 本轮已核证范围

独立确认本地C/T、父链`85cf861→9c026e89→310f21e`及远端仍为`85cf861`。第二提交是源码归档改`.source`并更新索引，归档字节保持。

独立重算结果：

- 73份记录Git字节SHA全部匹配；
- 28份源码归档及声明的Git LF身份匹配；
- 14个冻结模块与85cf861整个Git字节相同；
- Runner只有`produce`和`_nk_pov`两个顶层函数变化；
- 102份实际捕获阶段/导出文本SHA、60次请求和raw响应SHA匹配；
- attempt测试重构原件SHA匹配原check，且是当前文件真实前缀；后来附加的排序组件未冒称旧执行。

核证原始结果：

| 记录 | 结果 | 原raw SHA256 |
|---|---|---|
| attempt_scoped | 8 passed / 3 subtests | `c91da0ddb449a282ab4eb25b310d26d5f4f94c2c56526cd8b776510a96ec0454` |
| shared_consumers_current | 19 passed / 4 subtests | `0eddce0ec2f53072ec1913eb7d9408372e043c1c052fd2c510f27231e82921ef` |
| final_method_components | 80 passed / 15 subtests | `ddb5be2933f6c0de00eab51154b87b7d9610fa38b03f3bab0533c3eb9c2c70a1` |
| Python3.11 | 7 unittest OK | `352b3ba907c2f3ad84da1d5c6a7e1a403e817a4e4e63a015febc20300c024365` |

旧失败、fixture纠正及中断记录保留。上述数字是读取原始记录，**不是Controller重新运行测试**。

已读实际效果支持：共享受检链、两层Lint、独立五Lens和逐Finding三票、遗漏→Refine→新稿复审、NK新结果/缓存进入Brief、CritiCS结果进入Refine及pending/cache拒绝、V1四请求兼容。先前提出的源映射、完整Live验证和pointer丢失CAS三个根已按限定范围修复；NK两处`MATERIALIZED`返回修复也成立。它们不能覆盖本次发现的任务文件定位缺口。

## 冻结功能回归单独裁决

| 原冻结范围 | 原C/T参考 | 当前判断 |
|---|---|---|
| 00来源/历史保护 | 26b72cea /535496ba | 固定上游97ad71及旧参考C/T、clean已回读；治理和pin未改 |
| 01治理入口 | 736b411 /e9d2a206；后继049b0d2 /0554196 | 活动计划59459…及治理未变，可保留 |
| 02策略合同 | a00eb1a /69d6e9e6 | 配置/政策无差异；相关消费者未变范围按原身份复用 |
| 03来源、要求→合同 | 77ab5f7 /2a794325；34955bd /0e1f521 | 旧接受不撤销；**新增attempt分支的任务材料对应保证尚未闭合** |
| 04正式包入口/模式 | bcbc9ef /d4a40b3d；2b4dcd0 /847cc552；4efa777 /66ef287 | 旧入口保留、真实Live拒绝及offline共享链有证据；新增分支仍受上述映射阻断 |
| 05隔离/事务/费用/辅助账户 | 85cf861 /48c9b06 | 核心事务、账本、锁、账户及bridge模块未变；当前辅助消费者和拒绝回归支持原冻结范围复用 |

没有证据据此推翻原00–05 ACCEPT；但新增分支尚不能承接03/04已冻结的“正确任务材料进入合同和消费者”保证，因此**本候选不能取得完整冻结功能保护通过**。

真实账本、TS状态及保护锁的本轮SHA来自Writer保护记录，与先前冻结锚一致；本轮未打开这些私有原件，不将该报告表述为Controller重新读取原字节。

## 边界与后续

保留所有历史RETURN原判，不回填旧07/09祖先签收。允许Writer仅按上述根追加修复和必要复验，再形成新C/T；当前不得推送，也不得开始07。

生产授权适配仍未部署；Live成功、合法Live前章及用户整包真实交付未验证。计划内必要付费验收授权已存在，但本次RETURN没有解除代码、可信签收、Provider或费用门。`CUTOVER_BLOCKED=true`，TS恢复及私有迁移未授权。

本轮未修改文件、运行测试、读取凭证或调用Provider。