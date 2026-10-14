# CNW 费用、权限与恢复

合同/来源离线核验、工程Controller接受、可信生产预检、Owner Live/费用许可和创意批准分别核对。预算、Key或新Run本身不能授权模型调用。章节及注册operation请求绑定和真实消费者已有当期07离线工程证据；生产信任尚未部署，当前通用包真实生产未运行。

## 共用实际账户

`tools.cost_guard.for_run`从注册Run、冻结合同/operation输入及当前Policy推导实际RunAccount。`tools.p2_cost_guard`保持一个实际配置账本和provider slot，记录实例/项目/Run/stage、请求/输入与许可归属；不是给每个辅助子目录另开预算。Resolver不能授权请求，必须先核当前真实请求的Controller与Owner许可。

累计预算、调用次数、输入/输出token cap在共享锁内检查；NK/CritiCS用相同父账户。续签或新Live attempt不清除旧费用，发送失败/未知保守保留UNKNOWN，不能清零或假定未计费。ready等待后重验原输入、许可、账户和PENDING行；结果重读核费用行与原请求、receipt和输出SHA，不能重reserve同一次请求来制造成功。

本轮只用临时虚构账户验证，不打开Key文件、不调用真实Provider、不改真实费用记录。`PENDING`和`UNKNOWN_NOT_ZERO`保留原归属、历史和非零占用；没有有效权限不能借缓存/pending继续生产或正式发布。

## 历史政策不是通用默认

历史共享campaign的限额变更记录及原文见仓库外 `atom08_public_originals_b93d009.zip` 中 `docs/CNW_COST_ACCOUNTING.md`，逐文件SHA见 [08盘点](../evidence/ATOM08_READONLY_INVENTORY_20261014.md)。原配置、价格快照、policy snapshots和账本历史均有消费者而保留；本轮不重写它们。

`p2_cost_guard set-limit`操作实际配置的共享账本，没有任意项目/DataHome选择开关；不要把它当独立项目预算接口。历史某campaign的无上限授权不扩大到新项目，文档不代用户设置/清零预算。实际调整须对应明确授权和现有正式费用路径，不用工程测试操作真实账本。

当前 `GENERIC_LIVE_PRODUCTION=NOT_RUN`、`PRIVATE_MIGRATION=NOT_RUN`、`CUTOVER_BLOCKED=true`。Owner已授权计划内必要输入包付费验收，实际执行仍须当前精确代码/方法、可信签收、身份/Provider/费用门通过；该授权不含旧TS恢复或cutover。
