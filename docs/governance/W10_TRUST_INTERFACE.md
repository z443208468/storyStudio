# W10 可信 Controller 接口

此接口把确定性身份核验、独立签收和 Provider/费用授权分开。本文与代码只定义信任边界，不表示生产信任端已经部署。

## 离线身份报告

`tools.cnw_w10_policy.validate_per_run_bindings()` 读取项目合同、Run 合同快照、`run_state`、当前策略和固定 Workflow，并验证来源、manifest、实例身份及旧项目外部映射。成功时返回 `OFFLINE_BINDINGS_VALIDATED`，报告包含完整绑定字段、`identity_sha256` 和预检文件哈希。预检 JSON 中的 `status`、reviewer 或 acceptance ref 不参与身份层授权；`provider_call_authorized` 必须是布尔 `false`。

此报告只用于离线对账。它不能被 Provider 当作运行授权。

## 独立 Controller 签收

部署环境需提供 Python 模块 `storystudio_deployment_trust.controller_attestations`，模块导出 `get_controller_attestation_verifier()`。模块必须安装在 StoryStudio Writer 无法修改的仓库外部署位置，并返回具有 `verify(signer_id, message, signature) -> bool` 的验证器。信任根和签名私钥由独立 Controller/部署主体管理；不得放在 StoryStudio 仓库、项目 DataHome、预检 JSON 或 Writer 可写目录。

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

生产验证器由部署提供，不由 Writer 通过调用参数注入。单元测试里的 verifier stub 和测试签名只验证协议，不是信任根，不能配置到生产部署。

## Provider 和费用授权

可信 Controller 签收不等于 Live 权限。Provider 调用仍需要独立、真实的用户 Live 授权、有效 Key、费用政策/预算和该请求的可信签收。离线报告和工程 Controller ACCEPT 均不足以 reserve 或发送请求。当前 ATOM-07 离线修正不提供这些生产授权，也不执行 TS resume。
