# ATOM07 精确候选裁决

```text
REVIEWED_COMMIT=b93d0094003ca93428ab18fd5def6d29119543d0
REVIEWED_TREE=8c4b97ac61092c9522a674c67625b88df19b8db7
REVIEWED_PLAN_SHA=408864DEFBE39C7CCD6A113C53614378688B18FD2EB48AC0A58ED6D246B6A247

CODE_FIX_VERDICT=ACCEPT_CURRENT_ATOM07_SCOPE
METHOD_FIDELITY_VERDICT=ACCEPT_CURRENT_APPLICABLE_METHOD_SCOPE
FROZEN_FUNCTION_REGRESSION_VERDICT=ACCEPT_CURRENT_AFFECTED_00_06_SCOPE
ATOM07_OFFLINE_ENGINE_VERDICT=ATOM07_OFFLINE_ENGINE_ACCEPT
CURRENT_ATOM_CLOSURE_VERDICT=ACCEPT_ALL_CURRENT_OFFLINE_ENGINE_GATES
ATOM07_STATUS=OFFLINE_ENGINE_CLOSED; PRODUCTION_TRUST_DEPLOYMENT_PENDING
GIT_GOVERNANCE_VERDICT=ACCEPT_EXACT_CANDIDATE_AND_PRESERVED_HISTORY
GIT_PUSH_AUTHORIZATION=YES_CONDITIONAL_EXACT_NORMAL_FAST_FORWARD
NEXT_ATOM_PERMISSION=ATOM08_SAFE_ENGINEERING_ONLY_AFTER_PUSH_AND_EXACT_REMOTE_READBACK
```

这是**当前07全部适用离线工程门接受**，不是最后组件的局部接受，也不是Live或最终输入包交付接受。审查未运行测试、修改文件、读取凭证或调用Provider。

## 精确对象与证据

独立核对：

- HEAD、Tree、父提交与请求一致；远端`main`仍为冻结06的`84e022de0fee6eb7d7eec4c248703621129491e1`。
- f8→b93的**237个候选路径**，物理字节与候选Git blob全部一致。
- 最终完整运行的67项源码，当前SHA与运行记录一致；40项实际签名实现输入与Git字节一致。
- 33组raw/check逐项重新哈希，无差异；其中失败和主动停止仍保留原退出码。
- b93仅追加五份harness归档。归档与记录SHA匹配；重建的旧harness明确标为按已记录SHA恢复，不冒充 untouched original。
- 最新实际未跟踪项为**9项**：六份旧05日志、两份06冻结原件、一个slot lock。均未夹入候选、未删除。
- CNW仍固定`97ad71fe5e5e76a82275c6c63d4add06fb60ab6e`；旧参考仍为`26b72cea…/535496ba…`且干净。
- TS状态及真实账本仅做SHA核对，分别保持`3bae0722…42ee0d`、`c8b0705f…e0ab9b`。

活动计划、AGENTS和治理指针一致。原f8 **RETURN／NO_PUSH不改判**；本次裁决只接受后继b93精确树。

## 当前07全部门的实际闭合

| 当期门 | 核证结论 |
|---|---|
| 合同、来源、实例、Policy、Workflow预检 | pre-run与existing Run使用真实预检绑定；旧项目、异源、异合同、实例及实现身份不能互换解锁。没有要求未来文学回执才能创建合法Run。 |
| 独立可信预检与Owner许可分层 | 两purpose、两个独立authority接口；工程结果保持`provider_call_authorized=false`。普通JSON、Key或CLI参数不能放行。签名重建结束再次检查期限。 |
| 实际请求及费用消费者 | 章节高低入口、W10、注册操作及辅助路线消费实际角色／消息／cap／extra／来源身份；共同slot、单一账本、锁内累计预算与次数保持。续签不能清除原费用和UNKNOWN。 |
| f8根一：legacy revision放行 | 无生产许可的旧revision_apply返回None后再次明确拒绝；实际high/low负例在Key、slot、reserve及HTTP前停止。合法signed批准修订另有实际消费和缓存证据。 |
| f8根二：辅助授权不可用 | NK关联Brief；CritiCS Plot关联Plot、Text关联Refine。实际输入、action、父Run、账户、原生结果及费用被绑定，辅助没有替代CNW岗位。 |
| 恢复、pending与cache | current／pending／attempt共享枚举；原输入快照、回执、费用及结果重读。批内去重仅减少同一次读取，保留逐票验证、文件末端复核和账户重派生，不跨请求缓存许可。 |
| 模拟／Live隔离 | 原生raw、receipt、hook及CNW回执保留模拟标记；同步重标、context退出、历史attempt/pending等负例拒绝。真实verifyLive拒绝本轮模拟。 |
| ADVISORY篇幅政策 | 新V2合同明确版本；超限、欠产不产生纯长度追加请求。真正遗漏仍进入Refine及新稿复审；旧无字段合同保留旧语义。 |
| NK实际发送边界 | 实际reserve与shim使用同cap；真实messages估计受预留／Owner限制。ready等待后重验原payload、许可、账户、PENDING行及原cap；拒绝时不重新reserve，原context保守UNKNOWN。 |
| W10适配 | V2受检整阶段执行、packet与execution锁、实际高低入口及共享slot成立；旧manual接受不能降级V2。Python正向消费者与真实PS授权边界负例分别记载。 |

没有发现本审查范围内仍未修复的当前07源码阻断项。

## 方法与冻结功能保护

最终完整链原raw：

`7446516ae0878992e4fab51602042bf6b5a8ee7d838707e9c1d22f9c1cd2ab59`

正常exit0；75份捕获文件独立重算零差异、合同匹配Run。实际具有：

- 11阶段、16个CNW请求；
- 五个独立Lens；一个实际Finding三票、2/3确认；
- Completeness遗漏及native Text选择进入Refine；
- 两个受影响Lens读取实际新稿复审；
- native Plot5次、Text3次；24行共同临时账本均SETTLED；
- pending/cache不追加服务或费用，模拟拒绝Live。

冻结保护按**84e基线**判断，未用“相对f8未变”替代：

| 冻结范围 | 当前保护依据 |
|---|---|
| 00–02：治理、实例路径、配置与原政策 | 原接受链保留；受影响入口指针及实现身份核对，旧权限／路径／事务实现未改。 |
| 03–04：来源与包声明、合同路由、显式CLI | 当前包attempt、来源重绑定、旧Run／合同保护及W10实际入口回归；未变化部分继承原身份。 |
| 05：费用、候选、晋升／作者批准 | signed操作、批准副本、原稿／Canon保护、共享费用SETTLED／UNKNOWN、旧无许可路线拒绝。 |
| 06：四角色、审稿、修订、恢复、辅助 | 当前共享消费者与完整辅助链覆盖实际改动；独立核对229个记录为未变化的顶层函数／class定义，零差异。 |

M01–M12及M14–M16的当前受影响职责、读边界和消费者效果接受。M13原Sprint策略及未受影响实现继续按冻结证据复用；完整五话及三类包产品终验仍属09。此次不新签旧私人Live replay，也不代签用户创意接受。

## EARLY及遗留问题的完整边界

1. **EARLY／Export：限定证据复用接受。**  
   新native-enabled Run没有Export。旧disabled EARLY、旧导出实物及负例按原来源复用，不能拼接成新Run导出。`legacy_native_export_compat_final`仍是1失败／19通过；七个Export案例通过，不改整批结果。

2. **错误索引和审计：已正确限定。**  
   初版缺失canary断言无效并保留；v2只报告实际Prose payload键。12项历史非签名文件仅声明LF等价；全67 current=test与实际签名／改动源码byte-exact硬门保持。没有改旧源码或属性掩盖失败。

3. **历史ACL超时：原失败保留，环境原因未证明。**  
   后继有界诊断及最终完整链实际成功。没有放宽权限、扩大生产timeout或用重跑抹掉旧失败。

4. **后续产品问题：managed Live导出说明仍待08/09收口。**  
   [cnw_export.py:225](D:/CangqiStudio/StoryStudio/tools/cnw_export.py:225)的固定模拟说明／offline恢复指引不能用于未来Live交付。此问题在84e/f8已有、此次未改；列入后继范围，不阻断当前07离线工程接受，也不授权提前09施工。

## 冻结、推送与下一阶段

冻结本次精确C/T、活动计划身份、原RETURN、证据SHA、允许复用范围及上述限制。

仅当远端`main`仍为`84e022de…`时，允许正常快进：

```text
84e022de → f8c72d59 → fcf85845 → b93d0094
```

这接受的是**最终修复树**，不回填f8为ACCEPT。远端变化须重新审查；不得强推、改历史或夹带未跟踪文件。

正常推送后必须回读：

```text
REMOTE_COMMIT=b93d0094003ca93428ab18fd5def6d29119543d0
REMOTE_TREE=8c4b97ac61092c9522a674c67625b88df19b8db7
```

回读一致并保存本原始裁决／冻结记录后，**只允许ATOM08不删除、不迁移、不切换私有数据的安全工程**。08仍须精确候选独立收口，才能开始09。

```text
W10_PRODUCTION_TRUST_DEPLOYMENT=ATTESTATION_PENDING
GENERIC_LIVE_PRODUCTION=NOT_RUN
INPUT_PACK_TO_STORY_GATE=RETURN/NOT_COMPLETED
OWNER_PLANNED_PAID_ACCEPTANCE=AUTHORIZED; EXECUTION_GATES_STILL_REQUIRED
TS_LIVE_AUTHORIZATION=NOT_AUTHORIZED
TS_RECOVERY_ELIGIBILITY=NOT_ESTABLISHED
PRIVATE_MIGRATION=NOT_RUN
CUTOVER_BLOCKED=true
USER_CREATIVE_ACCEPTED=PENDING_USER_READING
```

当前接受完整关闭07当期离线工程范围；真实部署、真实Provider及用户实际输入包**全部声明任务**的CNW生产、审查和分别导出仍未完成。
