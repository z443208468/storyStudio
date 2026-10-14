## 合并结论

本轮是 **ATOM07 WIP整体复核及候选准备指导**，不是精确候选签收。

- 当前 HEAD仍为 `f8c72d59b070a3544047189de0fb31f3b138e6df`／Tree `ee325b8429aadc8f68e3d6091204dc4e9f997765`；原 **RETURN／NO_PUSH** 保留。
- `origin/main`仍为冻结06的 `84e022de0fee6eb7d7eec4c248703621129491e1`。
- 在此前整体调用链审阅及本轮核证范围内，**未发现新的、尚未修复的07生产源码阻断根因**。这不等于保证全部应用代码没有其他问题。
- 现在可以准备正常main精确候选；仍须独立完整07裁决。**当前不授权推送或进入08。**

## 本轮实际核证

| 范围 | 独立核证结果及限制 |
|---|---|
| 最终完整辅助链 | 原raw SHA为 `7446516ae0878992e4fab51602042bf6b5a8ee7d838707e9c1d22f9c1cd2ab59`；正常exit0。67项记录源码前后相同，当前物理SHA也全部匹配。 |
| 捕获与身份 | 自行重算75个实际捕获文件，**零差异**；冻结合同SHA与Run一致。 |
| CNW实际消费者 | 11阶段物化；16个CNW请求，五Lens、三Verifier、Completeness、Refine及两项受影响复审都有实际记录。Canon Finding的三票是2票未反驳、1票反驳，实际聚合为CONFIRMED。 |
| 修订效果 | 实际Completeness遗漏、CritiCS选择进入Refine请求；新稿删除错误兄妹关系并增加归还工具的下一行动。两个复审请求实际读取修订稿，报告candidate SHA对应该稿。 |
| 辅助及费用 | Native Plot5次、Text3次；共同账本24行均SETTLED、归属父Run。实际测试保留pending/cache不重启服务、不增加调用或费用，以及verifyLive拒绝模拟的断言。 |
| 字节门 | 40项实际签名实现输入，当前SHA与报告相符且原物理字节等于Git过滤字节。 |
| 运行性质 | 全部为虚构临时实例、末端模拟；CNW回执为MOCK_ONLY／SIMULATED。**没有真实Provider成功，也没有该新Run的Export。** |

以上依据 [最终捕获](/D:/CangqiStudio/StoryStudio/evidence/atom07_auxiliary_repair_20261014/consolidated_final_native_full_chain_after_preflight.consumers.json.critics_signed.json)、[修正后的消费者索引](/D:/CangqiStudio/StoryStudio/evidence/atom07_auxiliary_repair_20261014/consolidated_final_native_full_chain_after_preflight.consumer_index_v2.json)及实际测试断言；我没有运行测试。

## 全部当前剩余清单

| 项目、位置 | 判断、来源与最小处理 |
|---|---|
| 初版消费者索引的虚构canary断言 | **本轮外部审计错误**，不是生产代码退化。初版原件必须保留并标无效；v2只能证明实际Prose用户payload含`writing_brief/voice_samples`，不能宣称验证了未提供的canary。冻结canary负例继续保留自己的来源范围。无需改生产代码或重跑完整链。 |
| 全67文件一律要求physical=Git的初版审计 | **外部provenance规则范围错误**。12项确为未修改历史文件；我逐项核对了其当前SHA与最终测试记录，以及对f8、84e的声明换行等价，均成立，且不属于实际签名实现输入。可以按下述规则修外部审计，不需修改这12项或`.gitattributes`。原强门失败记录保留。 |
| 历史Windows ACL超时 | 旧失败仍是事实；不能宣称已查明杀软、资源泄漏或权限故障。修正后的有界诊断与最终全链已经完成，当前可运行门已取得成功证据。保留旧10秒超时、2000次上限停止和错误driver原件；**不再把解释全部环境暂态作为07新前置**，也不扩大生产timeout或缓存权限。 |
| 精确候选、冻结及Git治理 | **尚缺新C/T**。须核候选Git字节、全部范围及证据，再给当前07完整裁决。WIP通过不能替代此门。 |
| managed Live导出说明 | [cnw_export.py:225](/D:/CangqiStudio/StoryStudio/tools/cnw_export.py:225)仍对managed job写固定模拟／Live未授权说明和offline恢复命令。这是84e/f8已有、此次返修未改的产品差异；归属后续08/09说明与正式包Live导出收口。列入后续清单，**本轮不得提前施工，也不得宣称Live整包已完成**。 |

当前已修的NK ready重验、实现身份、预检重复计算及验证结束期限检查，分别位于 [cnw_runner.py:1645](/D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:1645)、[cnw_live_authorization.py:81](/D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:81)及 [cnw_live_authorization.py:187](/D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:187)。本轮没有发现需要再次扩大这些修复的具体反例。

## 准许的最小审计修正规则

**认可仅修外部provenance审计：**

1. 全67项仍严格要求：`current physical SHA = 最终测试记录SHA`，且测试before/after相同。
2. 所有实际签名实现输入、此次候选改动源码严格要求：`physical bytes = 候选Git blob bytes`。
3. 对12项未修改历史文件，逐项列原raw SHA、Git blob SHA、f8／84e来源、声明的LF差分及适用AST证据。明确这是身份／等价核对，**不是新C/T重新执行证据**。
4. 不把准许的12项扩大成“全源码字节完全相同”；不归一化它们来消除旧失败；不改历史Run、签名、raw或清单。

## 旧Export及冻结功能的复用边界

可以保留既有disabled EARLY链／Export／负例作为**原执行身份下的有限证据**。本轮已经核到：

- `operation_early_e2e_regression`原raw SHA `9df70718f89f51f5358e9e8ab66fc5bf33b085b8ae2f5fd43bd33b95617ae90c`，两项通过。
- 旧Export正文、修订稿、来源连读及manifest有实际保存内容。
- 当前Export与原物理preimage仅LF变化，AST相等；当前`tests/test_cnw_export.py`与兼容批次记录SHA完全相同。
- `legacy_native_export_compat_final`中七个Export案例实际通过，但整批仍是**1失败、19通过**，不得写成整批PASS。
- 当前EARLY测试与84e、f8 Git字节相同；其旧运行check没有列该测试文件SHA，这个来源限制须保留。

因此，不要求仅为本次辅助授权返修另生成一次disabled完整链；也**不能把旧Export接到新native-enabled Run上，声称该新Run已经导出**。受影响冻结功能继续按既有逐函数／模板身份和当前共享消费者范围核证，不能将“相对f8不变”改写成“相对冻结06全部不变”。

## 可落实的候选准备范围

纳入非敏感的：

- 原f8 RETURN、失败／停止／过期／ACL超时及错误索引原件；
- 最终完整链raw、check、75文件capture、audit、v2消费者索引；
- 修正后单Lens诊断及原错误driver记录；
- LF前preimages、换行等价、PS解析、最终签名实现输入及修正后的provenance清单；
- 已核定复用的组件raw/check、原始Controller指导、冻结06与TS／真实账本保护记录。

随后提交精确C/T，按完整07门重新裁决，包括 **FROZEN_FUNCTION_REGRESSION_VERDICT**。本轮未重新遍历全部未修改旧脚本和第三方实现，也没有验证真实信任部署、真实付费输送、真实用户整包全部任务或Live导出。

**NEXT_ATOM_PERMISSION=WITHHELD；GIT_PUSH_AUTHORIZATION=NO。** 历史RETURN及失败保持原判；TS恢复、迁移、cutover保持原边界。
