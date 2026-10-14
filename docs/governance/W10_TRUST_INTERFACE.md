# W10 可信 Controller 接口

此接口把确定性身份核验、独立签收和 Provider/费用授权分开。本文与代码只定义信任边界，不表示生产信任端已经部署。

## 离线身份报告

`tools.cnw_w10_policy.validate_per_run_bindings()` 读取项目合同、Run 合同快照、`run_state`、当前策略和固定 Workflow，并验证来源、manifest、实例身份及旧项目外部映射。成功时返回 `OFFLINE_BINDINGS_VALIDATED`，报告包含完整绑定字段、`identity_sha256` 和预检文件哈希。预检 JSON 中的 `status`、reviewer 或 acceptance ref 不参与身份层授权；`provider_call_authorized` 必须是布尔 `false`。

V2 使用 `cnw_run_contract_preflight_v1`，由 `build_run_contract_preflight()` 与创建 Run 前的预检共用实际合同、Plot 材料和请求的计算路径。它核验已存在 Run 的精确合同快照、项目实例、工作意图、来源修订或原创 Canon/Arc 身份、注册 Policy、Workflow、Provider Policy 与文学来源冻结。原创首章不要求不存在的来源 Manifest。V1 的 `cnw_w10_per_run_preflight_v1`、受限外部映射和历史 J19 固定身份保持独立。

此报告只用于离线对账。它不能被 Provider 当作运行授权。

## 独立 Controller 签收

首版部署接口使用 Windows Known Folder API 取得 ProgramFiles，再定位固定文件 `StoryStudioControllerTrust/controller_attestations.py`。不读取环境变量提供的部署根，不通过 `PYTHONPATH`、finder 或 `sys.modules` 寻找验证器。文件导出 `get_controller_attestation_verifier()`，返回具有 `verify(signer_id, message, signature) -> bool` 的验证器。

文件和全部祖先以只读 Windows 句柄保持到源码执行及 factory 完成，拒绝 write/delete sharing；从同一对象句柄读取安全描述符、卷/文件身份、对象类型及源码字节。核验 process 与实际 thread token 的有效权限、所有者及绕过权限，拒绝 Writer 可写、可替换、可改 ACL/取得所有权、NULL DACL、reparse 或查询失败。执行前再次核验对象和权限。Administrator 不能证明独立隔离时保持 Pending，加载器不修改权限或安装信任根。

首版要求部署文件自包含，公共信任材料嵌入受保护文件；不支持外部代码/配置依赖。AST 在执行前拒绝所有 Import/ImportFrom，包括方法内延迟导入；私有模块 builtins 在 factory 和 verify 期间仍拒绝动态导入。此约束防止再次搜索 Writer 可写依赖，不能称作 Python 沙箱。需要依赖的验证器必须等待另行审查，不能自动降级为普通 import。

信任根和签名私钥由独立 Controller/部署主体管理；私钥不由加载器读取，不得放在 StoryStudio 仓库、项目 DataHome、预检 JSON 或 Writer 可写目录。本次工程没有部署生产验证器或生成生产私钥；虚构离线测试签名不能成为生产信任根。

缺少模块、信任根、可信签名者或有效签名时返回 `ATTESTATION_PENDING` 或签名错误。单有 `ACCEPTED` 字段、普通 JSON、reviewer 名称、摘要或历史 J19 签收都不构成信任。

签名文件使用 UTF-8 JSON：

```json
{
  "schema_version": "cnw_signed_controller_attestation_v1",
  "payload": {"purpose": "...", "decision": "ACCEPT"},
  "signer_id": "deployment-trusted-controller-id",
  "signature_base64": "..."
}
```

签名消息为 `payload` 的 UTF-8 canonical JSON（排序键、紧凑分隔符、保留 Unicode）。预检签收将项目/实例、Run、工作单元、合同、工作意图、来源修订、manifest revision、来源根、选段/锚、Policy、Workflow 与离线身份 SHA 全部放进 payload。阶段输出签收还绑定 stage、stage fingerprint、角色、request ID、Provider request ID、输入 SHA、Provider 输出 SHA 和正式产物 SHA。

严格拒绝重复键和非有限数值；实际 payload 与期望 payload 的 canonical 字节必须相同，并把同一实际字节交给 verifier。布尔 `false` 与数值 `0` 不可互换。V2 Run 预检 purpose 为 `CNW_V2_RUN_PREFLIGHT`，历史 V1 为 `W10_PER_RUN_PREFLIGHT`；独立签收后的 Provider 权限仍为 `false`。

生产验证器由部署提供，不由 Writer 通过调用参数注入。单元测试里的 verifier stub 和测试签名只验证协议，不是信任根，不能配置到生产部署。

## Provider 和费用授权

可信 Controller 签收不等于 Live 权限。Provider 调用仍需要独立、真实的用户 Live 授权、有效 Key、费用政策/预算和该请求的可信签收。离线报告和工程 Controller ACCEPT 均不足以 reserve 或发送请求。当前 ATOM-07 离线修正不提供这些生产授权，也不执行 TS resume。

新 V2 的实际 `cnw_runner` 高层/低层入口均消费 `cnw_live_authorization` 的当前请求绑定，在缓存复用、Key、slot、费用和 HTTP 前核验。接口已实现且有当期07离线消费者证据；生产信任验证器与真实授予机制尚未部署，不能因此调用 Live。手工改变 Run mode 或自报 `provider_call_authorized=true` 不授予权限。

Controller 预检 purpose 与 Owner Live/费用 purpose 分离。实际注册 operation 使用 `cnw_operation_authorization` 及 `CNW_OPERATION_PREFLIGHT` / `CNW_OPERATION_OWNER_LIVE_FEE_AUTHORIZATION`，重建 operation namespace、冻结输入、真实构造器、stage/role、消息、cap 和 extras。批准修订的作者创意批准另行核验，不替代这两种许可。

辅助作用域绑定实际父阶段和输入：NK support hook 对应 Writing Brief，CritiCS Plot 对应 Plot，CritiCS Text 对应 Refine。它们共用实际父 RunAccount、slot、账本、次数和累计费用；不能借独立子目录另开预算。签名不能跨项目/Run/来源/合同/实现重放。等待辅助服务 ready 后再核原请求、许可、账户及 PENDING 行；失败保留原归属和 UNKNOWN，不能重新预留来洗掉未知费用。测试签名/模拟会话从不成为生产信任根。

W10 阶段签收在正式文件写入前严格要求匹配回执 `mode="LIVE"` 且 `fixture_only` 是布尔 `false`；缺字段、数值 `0` 和模拟标记均拒绝。下层 `accept_validated_stage()` 对非本地阶段使用相同要求；本地 Lint 继续禁止 Provider 回执。draft 不再预写正文，目标碰撞仍拒绝，只有下层签收成功才写目标。本修正不宣称下层阶段状态提交与上层文件写入已成为一个原子事务。
