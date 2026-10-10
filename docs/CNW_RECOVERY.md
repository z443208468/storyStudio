# CNW 恢复与参考资料重开

固定官方依据为 `97ad71fe5e5e` 的 `templates/CLAUDE.md` 日志/状态要求、生产手册 current state/索引，以及各岗位读取合同。恢复缓存是本地运行适配，不是新创作阶段。

## 正式入口

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/studio.ps1 resume -ProjectRoot workspace/cangqi_cnw_public_restore_20261011 -RunId CNW-RESTORE-J19-20261011-01
```

live `resume` 核原身份后继续普通 11 阶段。`show-run` 单独查看。`produce`、live `step` 与 `resume` 共用实际消费核验；缺少旧执行身份的阶段须重新走执行器，精确相同成功请求可复用已付费 raw。旧状态不会直接升级为新方法证据。没有可复用请求时仍须环境密钥与既有成本护栏，不能将调用失败视为已完成。

offline/fixture `resume` 只报告需显式 step，不隐式调用生产 API。旧非 CNW receipt 入口仍只读。

## 参考资料纠偏后

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/studio.ps1 refresh-references -ProjectRoot workspace/cangqi_cnw_public_restore_20261011 -RunId CNW-RESTORE-J19-20261011-01 -Reason '来源审计后的当期人物资料纠偏'
```

此操作记录原因、旧/新参考哈希，先重开实际直接消费者，不调用模型。之后 resume 按产物内容传播：改变 Style 不重跑 Plot；Brief 若仍逐字相同，可复用 Prose。审稿资料仅改变某 Lens 请求时，其他 Lens 精确请求仍复用，当前审稿索引重新组成。

原稿、manifest、合同及运行合同副本改变会拒绝继续；不能用上述操作静默重冻。冻结 Canon 的创作决策仍需作者授权；本入口只处理已合法决定的资料变化，不代替官方 TODO_CONFIRM/作者决策。

执行身份包含实际角色消息、固定模板内容、该角色来源与补充资料、相关 builder/执行器、模型/端点/transport、工作流。Prose 身份与请求仍仅由 Brief 和选中声线构成。阶段顺序不自动充当内容依赖。Completeness 本 run 的反馈供后续复审使用，不倒推失效已经完成的初审；其他 run 的反馈会进入下次初审。

## 历史与边界

已完成状态必须有相应文件和哈希；复用前核产物、sidecar、原始请求/响应和 NK 反思；成功 CritiCS 支持由原生 adapter 核其实际输入快照。新正文落盘而新支持未完成时，旧回执仍只证明旧输入，不能与新稿交叉核验。替换的支持结果保留 support_hook_attempts。篡改会停止，不以新付费调用掩盖。

重开时旧产物复制到 `artifacts/history/`，旧索引字节保留，其内文件另有归档映射；历史回执进入 provider_attempts，精确请求缓存仍可核 raw 后重新激活当前覆盖。原字节和请求 ID 不删除。显式 invalidate 同样归档。

本次证据是受控离线普通阶段运行。多轮修订中断、同一 J19 最终真实链组合及可读导出仍按既定余项验收，不在此宣称完整生产已通过。
