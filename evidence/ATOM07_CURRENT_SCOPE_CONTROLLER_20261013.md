## 进入07的基线成立

独立回读本地、origin/main及远端main均为：

`84e022de0fee6eb7d7eec4c248703621129491e1 / 40399e2b5832798522ec6fa1945cd6605c75c32f`

06冻结记录与原裁决关联一致。**现在仅允许07施工；本回复不签07完成，不开启08/09。**

## 当前07的实质缺口

| 缺口 | 实际位置 | 最小收口 |
|---|---|---|
| V2 Live创建永远拒绝 | [produce](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:1026) | 区分无Provider的Run准备与实际生产授权，建立合法准备→受检授权→执行路径 |
| 通用请求永远拒绝 | [_require_generic_provider_authorization](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:702) | 消费独立可信预检、Owner Live/费用许可及实际账户；高、低请求边界均复验 |
| W10独立预检验证后仍永远拒绝 | [verify_run_preflight](D:/CangqiStudio/StoryStudio/tools/cnw_live_provider.py:77) | 同样消费独立Owner许可，不能仅修Runner而留下另一条不可用或绕过路线 |
| 注册操作只有模拟许可 | [_require_project_operation_authorization](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:597) | import/maintenance等实际Provider操作接入各自冻结请求身份，不伪造章节合同 |
| 新许可期限/额度尚未接入共同账本 | [cost_guard](D:/CangqiStudio/StoryStudio/tools/cost_guard.py:257)及p2 primitives | reserve在共同锁内执行许可累计额度；settle保持原归属与历史费用 |
| 真实可信部署尚未证明 | [controller_trust_loader](D:/CangqiStudio/StoryStudio/tools/controller_trust_loader.py:254) | 保留部署接口及缺部署Pending；不得把测试验证端认作生产部署 |

旧08b限定离线接受可保留，其关闭门、模拟身份及恢复证据不是上述新增生产适配的接受。原RETURN不追认。

## 对拟议模块的范围判断

你提出的“共同bindings、两类签名、真实创建与请求消费、共享ledger额度”**属于07有限依赖范围，可以据此施工**，但须满足以下约束。

### 1. 请求、工程签收、Owner许可分开

`08_review/live_authorizations/<run>.json`可由应用生成**unsigned请求或证据索引**；文件存在、自报ACCEPT或摘要吻合都不能授权。

分别验证：

- Controller预检签名：冻结合法身份，继续保持`provider_call_authorized=false`。
- Owner Live/费用许可：代表所有者**已经存在**的计划内付费授权，由独立受信任端限定具体操作、Provider、政策、期限和额度。

部署端必须按purpose及签署者角色区分两者；不能让一个普通ACCEPT凭据兼任Owner许可。不得让Writer生成自己的可信私钥、签名或`true`开关。

### 2. 先解决创建与签收的循环

当前existing-Run预检需要真实Run，而`produce(live)`在创建之前拒绝。

最小可行方式是：在完整合同/来源/注册检查后，允许`create_only`准备一个**未获生产许可的独立Live Run**，零Key、slot、reserve、网络；随后产生真实Run绑定请求并取得可信签收。准备状态不能写成生产授权成功。

pre-run与existing-Run授权主体应共用稳定身份。`observed_run_state_sha256`作为读时观测项保留，不能令每次正常阶段更新都使原许可自动失效。也不得为了批准Plot要求未来Cards、正文或审稿回执。

### 3. 签名必须绑定真正的执行对象

除§07原身份外，新包路径还须绑定job、attempt、task及应用选定Run；有源时绑定真实选段/Pointer，无源时绑定真实Canon/Arc/Style和合法前章。

Provider/model/endpoint、不可变policy与pricing身份、允许stage/role及token上限、期限和有限额度应明确。后续具体消息与前驱产物由真实消费者在请求边界重新派生验证；不能凭同一个Run ID接受不同输入。

原生attempt沿用06已接受的严格映射，不另造合同、来源或生成器。

### 4. 共同账本保持唯一

你提出的锁内grant累计约束是必要的：

- 固定许可/预算归属ID；renew、重签或换文件不能清零已用额度。
- 累计同时考虑既有reserve、SETTLED及UNKNOWN，保持原共同并发额度和全局policy约束。
- reserve前及等待slot后重新验证当前期限、范围和实际费用上下文。
- 已发起请求的settle继续使用**原context/许可归属**；许可后来过期、撤销或输入变化，不能导致费用丢失或UNKNOWN变零。
- 失败不得重新reserve/send求绿；缓存消费也不能绕过当前授权检查。

额度采用既有费用policy，本次范围审查不凭空设预算数值。

### 5. 所有可达消费者要共用门

至少覆盖：

- Runner创建、`cnw_live_call`及低层实际输送；
- W10 `complete/_complete_in_slot`；
- registered import/maintenance的front、实际请求及缓存恢复；
- NK、CritiCS的实际父Run/账户/slot输送；
- `accept_controller_role_output`现有签收入口。

普通CNW流水线不应新增“用户逐角色手填签收”要求；已有W10阶段接受入口仍须真实验证stage/request/receipt/output签名，不能弱化。工程Controller也不能代替五Lens、三Verifier或作者Canon批准。

## 必要离线验证

用真实注册临时项目、真实签名fixture与真实生产消费者，只替末端HTTP/native模型边界。不得mock授权函数求通。

最小正反范围：

- 合法身份、两类适用签名与有限许可，使真实请求消费者到达末端替身；不能只证明拒绝。
- 无部署、无签名、Writer可写信任来源、错签署角色/purpose、普通JSON、布尔/类型别名拒绝。
- 两项目、两attempt、同名Run、选A/选B、INSERT/ADAPT、模拟前章及schema降级不能串用许可。
- 过期/预算不足/token或model错配、并发预留、续签保留累计费用、UNKNOWN及中断settle。
- 已缓存请求在身份、许可或实际消息变化后拒绝；旧请求和产物保留。
- 真实V1入口及00–06受影响冻结功能回归；源码未变部分按精确身份复用，不泛化重跑完整09。

测试成功须标明SIMULATED，不能通过`verify-live`或正式晋升。

## 独立部署责任与阶段边界

Writer负责消费者、请求格式、接口及必要测试；独立部署方负责信任根、签署者角色、真实签收决定和Owner许可签发。部署端不能只是盲签Writer提交的JSON。

现有固定验证器接口限制依赖和加载来源；若真实验证实现需要依赖，须明确受保护的部署契约，不能绕开加载器或自造密码算法。真实部署权限及信任根未验收时，仍是`ATTESTATION_PENDING`。

依据§07.2b，**可信部署Pending不必否定已闭合的离线工程接口验收**；但代码必须已经有合法许可可走通的适配路径，不能继续永久硬拒绝。真实部署和实际用户包生产仍是后续必须完成的门，不能消失。

```text
CURRENT_ATOM=07
CURRENT_REVIEW=SCOPE_GUIDANCE_ONLY
NEXT_ATOM_PERMISSION=08/09_WITHHELD
GIT_PUSH_AUTHORIZATION=NONE
TS_LIVE/RESUME=NOT_AUTHORIZED
CUTOVER_BLOCKED=true
INPUT_PACK_TO_STORY_GATE=NOT_COMPLETED
```

本轮只读核对代码、计划、旧裁决与冻结记录；未测试、编辑、读取Key或调用Provider。