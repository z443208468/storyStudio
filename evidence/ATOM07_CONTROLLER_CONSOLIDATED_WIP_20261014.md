# Same Controller original consolidated WIP review

Writer transcription of the complete final reply from the existing readonly
`/root/goal_controller_61_restart_20261013`. This is a WIP RETURN inventory,
not a candidate acceptance or next Atom permission. Original reply follows.

# ATOM07 整体 WIP 合并审查

**当前确认有两项07必修源码问题，一项完整链证据缺口，一项后续产品差异。** 以下是本轮集中清单；不是 ACCEPT。

基线仍为 f8 `f8c72d59…138e6df` / `ee325b84…997765`，远端为已冻结06的84e。活动计划 SHA仍为 `408864DE…B6A247`。已读到 AGENTS 新增的整体审查、集中收敛规则。

## 一、当前07必须集中修复的两项

### 1. NK ready等待后缺少发送前重验

位置：[cnw_runner.py](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:1645)，等待始于1703行，实际生成 POST在1719行。

当前顺序是：核材料/许可/账户→预留→启动Node并等待ready→直接触发生成。等待期间许可可能到期或改变，Cards、账户或实现身份也可能变化；发送前没有再次核验。

**最小修复：**

- V2在生成 POST前重验当前payload、许可、原账户及输入额度。
- 新核验的许可须对应原预留行的 `live_authorization`，包括 bundle、Owner及identity SHA；核原费用上下文和输入/输出 caps。
- 不再 reserve，不重复扣请求次数；拒绝后使用原账户/context保守结算 UNKNOWN，停止服务，零生成 POST。
- 增加ready后材料、许可或账户漂移定点；保留合法NK及V1路线。

**Git来源：** 84e与f8均存在原来的“预留→等待→POST”结构。这不是最新cap/LF补丁新增的等待结构；07接通合法V2生产授权后，该旧结构必须补齐末端重验。

### 2. 签名实现身份遗漏注册与项目锁的实际代码

位置：[cnw_live_authorization.py](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:61)。

`implementation_identity()`仍未绑定：

- `tools/project_paths.py`：实际决定注册实例、DataHome、权限及reparse检查；被授权、账户和trust loader消费。
- `tools/project_transactions.py`：实际决定项目写锁；被合同、包任务、import/maintenance消费。

这两份代码改变时，当前签名的implementation SHA不会因此变化。它们当前与84e/f8逐字节相同，**尚未出现功能退化，但签名代码身份覆盖不完整。**

**最小修复：** 只把这两份实际依赖字节加入现有身份清单，不改其权限/锁实现。沿现有隔离源码副本测试，证明各自字节变化使原签名失效；最终身份正例重签验证。不新增签收平台或测试矩阵。

**Git来源：** 实现身份机制由07新增；遗漏在f8及当前清单均存在，不是本次NK账户返修引入。

## 二、完整链仍未证明完成

最新58009原件已独立核对：

- exit1，源码前后相同。
- raw SHA：`753805070f9fb8a505d8f79baa5a6a8c266376e5f1175a9897f7ead2003a5b30`。
- 捕获32文件 SHA全部匹配。
- 六阶段物化；五Lens执行中断；后续Verifier、Completeness、Refine、Re-review未运行。

实际失败链是：

`icacls超时 → DATA_HOME_PERMISSION_CHECK_UNAVAILABLE → PROJECT_INSTANCE_ID_REQUIRED`

这不是已证实的许可、Key或选源错误，也不证明实际ACL不合格。**环境暂态根因尚未查明，不能把失败归因已解决。**

允许新虚构完整链使用合法冻结的单槽资源配置：在签名前设置临时共享配置，保持五Lens、每Finding三票、native5/3请求各自独立。不得绕ACL、延长生产timeout或直接改已签状态求绿。并发效果继续引用原专门证据；完整链只证明该资源配置下的效果。

## 三、已修根因与回归来源

| 已确认根因 | 来源与当前状态 |
|---|---|
| legacy revision_apply 的None放行 | f8改造引入；当前恢复拒绝，实际高低负例已核。 |
| 辅助stage无法获得合法grant、text hook父阶段错误 | 07授权接线遗漏；当前父stage/hook/role及费用消费已补。 |
| registered native恢复仍使用旧run_name路径 | 历史旧路线假设在新注册链暴露；当前实际run_dir/parent/hook reader已补。 |
| native模拟身份丢失、pending/attempt未被Live门统一检查 | 07模拟/生产衔接缺口；当前共享枚举、raw标记和实际拒绝已核。 |
| native重复读取及共享槽位fanout不一致 | 原限额结构与07新增校验共同暴露；当前局部去重、末端复核及容量调度有实证。 |
| V2 excerpt生产CRLF、核验期待LF | 本轮新增精确核验与旧写入方式不一致；当前V2字节修复及V1保护定点已核。 |
| NK输入额度、shim实现身份、低入口外来账户 | 原发送/账户结构在07合法授权路线暴露；当前定点已核，尚需补上述ready时间窗。 |

81361的五项最终身份、NK→Brief/cache、8000额度/UNKNOWN及六种错误账户证据可按原范围复用。它们不能替代完整07结论。

## 四、后续Atom的产品差异

[cnw_export.py](D:/CangqiStudio/StoryStudio/tools/cnw_export.py) 在 `job_id` 非空时，无条件生成“MOCK_ONLY/SIMULATED、Live未授权”及offline恢复说明；实际Live包导出也传这个job_id。

该文字在84e已存在，f8及本轮返修未改变。应在后续08/09对应的生成操作说明与真实包导出范围纠正，按真实mode/验证状态给正确恢复入口。**本轮不授权提前修改后续Atom，也不能宣称Live导出指引已经完成。**

## 五、统一复验与最终候选材料

集中完成两项源码修复后，必要范围限于：

1. NK ready后漂移拒绝、原预留UNKNOWN保留、合法NK/V1兼容。
2. 两份依赖字节的旧签名失效及最终实现身份正例。
3. 最终字节、新签名下的完整11阶段与native Plot/Text消费、恢复、模拟防Live证据。
4. 新精确C/T：差分、物理↔Git字节、raw/check/capture SHA、冻结功能回归表及保护清单。

旧native十三类拒绝、费用SETTLED/UNKNOWN、操作/shared消费者按已核函数与LF等价范围复用。若最终修改仅是上述NK门和身份清单，**无需重复完整操作/W10/包矩阵**；完整链使用最终新签名即可。

原f8 RETURN、所有失败/停止/过期记录及00–06冻结接受范围保持不变。

## 审查范围与限制

本轮合并检查了相对84e/f8的07生产差分及授权、账户、请求重算、W10、辅助发送、native读取、缓存/恢复、ADVISORY、包attempt和导出调用链，并核对相关原始证据。未逐行重新审遍仓库全部未变实验工具、第三方运行时及所有测试；也未执行测试、读取Key或私有正文。因此不能保证全仓库绝无其他问题。

**当前仍为07未收口；NO_PUSH；ATOM08_PERMISSION=WITHHELD。** 所有者必要付费验收授权存在，但当前工程修复、可信部署和实际整包生产门不能据此视为通过。
