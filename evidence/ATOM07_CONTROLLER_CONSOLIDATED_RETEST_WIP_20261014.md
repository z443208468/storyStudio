# Same Controller original consolidated repair/evidence review

Writer transcription of the complete reply from the existing readonly
`/root/goal_controller_61_restart_20261013`. No precise new C/T was available;
this reply does not grant overall acceptance, push or next Atom permission.

## 合并只读结论

**本轮两项源码修复在已核范围内未发现新反例；ATOM07整体仍未收口。当前阻塞是完整消费者链持续失败，ACL超时根因尚未解释。** 无精确新C/T、推送或08许可；f8 RETURN保留。

### 1. 集中修复及统一定点证据

已核 `consolidated_ready_identity_components`：

- exit0，**6 passed / 27 subtests**；raw SHA `e3b351fe…89210b`匹配。
- 源码前后相同，记录源码与当前文件匹配。
- NK的20文件、额度组件10文件捕获SHA均匹配。
- 三种ready漂移均零生成请求；原预留身份、caps、context及非零UNKNOWN保留。
- V2发送前重验使用原PENDING行，不再次reserve；初始V2判定固定，避免等待期间降级跳门。
- `project_paths.py`、`project_transactions.py`已加入实现身份；三份隔离依赖字节变更均使旧签名拒绝。
- 合法NK→Brief/cache、外来账户拒绝、模拟防Live及V1兼容断言实际执行。

这关闭了本轮两根的**定点证据缺口**，不构成整体07签收。

### 2. 完整链失败：已证与未证

最新单槽完整链：

- exit1，源码稳定；raw SHA `67049117…5ae4ea8`匹配。
- 六阶段完成，在五Lens请求的账户核验中失败。
- 实际栈为：

```text
NativeReadBatch.finish
→ cost_guard.for_run
→ build_run_contract_preflight
→ 注册/权限校验
→ whoami.exe communicate 超过10秒
```

这是实际权限检查不可完成；不是已证实的签名、Key或ACL内容错误，也不是NK ready修复失败。尚未到Refine，不能证明text-refine和后续复审通过。

独立四次ACL诊断原件SHA匹配，耗时均短且成功。**它只证明独立场景可用，不能解释完整链失败。**

### 3. 调用循环与资源检查结果

源码确有重复校验路径：

- [cnw_test_live_transport.py](D:/CangqiStudio/StoryStudio/tools/cnw_test_live_transport.py:79)：history开始、结束派生账户。
- [cnw_critics_adapter.py](D:/CangqiStudio/StoryStudio/tools/cnw_critics_adapter.py:80)：native batch开始、结束派生账户。
- [cost_guard.py](D:/CangqiStudio/StoryStudio/tools/cost_guard.py:307)：派生账户再次构造真实预检。
- [cnw_project.py](D:/CangqiStudio/StoryStudio/tools/cnw_project.py:862)：预检重算包含注册校验与Plot请求构造。
- 高入口、槽内、reserve及发送前各自重新执行相关门。

**重复负载已由源码确认，但没有实际计数，不能认定它就是超时原因。** 本轮未发现这条路径重新进入Provider的无限递归，也未找到已确证的资源泄漏：native局部缓存不跨调用，服务wrapper恢复cwd，HTTP capture在finally恢复，真实ACL调用委托原 `subprocess.run`。

尚缺整链中的CLI耗时、数量、进程/句柄轨迹；不能以静态检查宣称资源无泄漏。

### 4. 唯一下一诊断范围

建议只做**一次带观测的有界消费者复现**：

1. 新虚构fixture，真实前六阶段及native Plot五请求；随后只执行一次合法Lens请求。
2. 不伪标五Lens整阶段完成，不继续完整11链。
3. 仅在现有CLI subprocess委托边界记录：
   - 命令basename、线程、单调时钟起止、timeout、exit/异常；
   - 调用栈函数名摘要、累计数量、同时在途数量；
   - stdout/stderr SHA，不公开SID；
   - native完成、Lens前及终态的本进程句柄/线程数量。
4. 非native命令直接委托**安装wrapper前保存的真实函数**，避免诊断wrapper自身递归。
5. 第一次失败或该Lens结束即停止并保留证据；不重试，不调整10秒，不缓存权限结果，不替换授权/阶段函数。

此诊断用于确定失败发生在哪个真实CLI调用及负载条件，**不产生Atom PASS**。根据结果再决定是否需要局部去重或资源修复，当前不先改安全门。

原完整链失败、旧超时/过期记录与后续Live导出说明差异均保留。真实整包生产、可信部署、TS恢复及cutover未由本轮证明。
