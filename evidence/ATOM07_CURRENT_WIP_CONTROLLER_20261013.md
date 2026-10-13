预生成签收方案可行：**不必先创建未授权Run**。当前使用真实pre-run计算，再核existing-Run等价，方向符合07。但本轮仍是WIP，尚不能收口。

## 当前最小修正

### 1. Run许可不能授权任意消息

[RunAccount.verify_request](D:/CangqiStudio/StoryStudio/tools/cost_guard.py:189)目前只验证operation请求；章节路线没有验证`messages/role/output_cap/extra`。新授权模块只检查Run、stage和额度。因此合法Plot许可可能被直接调用者用于错误role或任意消息。

建议复用、必要时提取**现有纯请求构造器**，在真实高层及低层请求边界验证：

- stage与role对应；Lens/Verifier只允许真实当前任务中的身份；
- 当前合法前驱产物及完整消息字节；
- 严格整数token上限、实际output cap和extra；
- 续写、长度修复、Refine/Re-review等合法变体，绑定实际已有回执/候选与对应构造规则。

**不用逐消息外部签名。** Owner许可冻结操作范围和额度；实际消息由受检岗位构造并在发送前重算。不能只接受调用者写出的“expected SHA”或可同步重哈希的请求记录。

W10别名统一至实际stage后，也必须在真实`complete/_complete_in_slot`核验当前role和消息，不能只调用`require_run_authorization(stage=None)`。

### 2. unsigned请求发布需可恢复

[publish_request](D:/CangqiStudio/StoryStudio/tools/cnw_live_authorization.py:193)直接`open("xb")`写最终路径。部分写失败会留下同名残文件；重入随后永久报`LIVE_AUTHORIZATION_REQUEST_CHANGED`。

复用06已有完整临时写、字节核验、原子独占新增helper即可。保留失败attempt；已有完整文件只核验复用，不能覆盖任意已有文件。

### 3. 许可需在实际输送前再核验

目前高/低入口及锁内reserve均有检查，但[实际HTTP](D:/CangqiStudio/StoryStudio/tools/cnw_runner.py:811)前没有最后复验。reserve之后可能发生过期、许可/输入变化。

将最后校验放在实际HTTP/native输送前，覆盖当前许可、消息和请求范围。若已预留后拒绝，按原会计语义保留/结算原归属，不能丢费用、清UNKNOWN或重新reserve/send。

### 4. 代码身份不能只绑定workflow模板

当前bindings绑定workflow、来源及Plot请求，但需要确保07授权适配和岗位构造变化会使既有许可失效。复用既有受检builder/transport身份或批准的代码身份，选择最小稳定方案；不要另造运行状态系统，也不要要求未来产物才能批准Plot。

## 已有良好边界

- Controller预检仍为`provider_call_authorized=false`；
- Owner使用独立purpose及验证方法；
- 预算在共同ledger锁内按实例+Run累计，换签名文件不会清零；
- settle仍使用原context；
- app/native自动发布unsigned请求，保持用户无需填写内部身份。

这些只说明设计方向，不能替代实际消费者验证。

## 最小负例

优先补合法checked Plot正例及下列拒绝：

- 合法Run许可下的错误role、任意/跨项目消息、修改extra或cap；
- 合法续写消息与伪续写消息的对照；
- 请求发布部分写故障及同尝试恢复；
- reserve后许可过期/改变，零HTTP且原会计记录保留；
- 代码/构造身份变化后旧许可不得复用。

测试当前HMAC验证端是**测试用密码学MAC验证fixture**，不是已部署生产签署者。末端模拟产生的证据须明确区分模拟与Live形状，并用实际验证器证明其不能取得Live接受；`SIMULATED`字样或“状态尚未等于Live接受”本身不构成该反证。

注册operation、辅助组件和旧mapped W10路线仍按你披露的缺口继续补齐；现在不签07、不推送、不开放08/09。未运行测试或改文件，也不猜测正在运行的Plot失败原因。