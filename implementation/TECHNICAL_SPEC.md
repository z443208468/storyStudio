# StoryStudio 通用实现与部署边界

当前权威是 [R5](../plans/MASTER_PLAN_GENERIC_APP_R5.md)及精确签收。原P2技术规范已在仓库外原字节备份，旧命令/默认预算不是当前配置。本文不把目标架构或已有接口宣称为最终生产验收。

## 模块与真实消费者

| 模块 | 当前职责 |
|---|---|
| project_paths / project_transactions | 显式DataHome、注册实例、锁、路径/权限与事务保护 |
| cnw_input_pack / cnw_native_pack / cnw_pack_app | 包归档校验、材料/要求封存、任务依赖、应用自建合同/Run/attempt与job恢复 |
| cnw_project / cnw_contract | 不可变source/Manifest/Index、V1/V2合法来源、项目政策、合同及离线身份预检 |
| cnw_roles / cnw_runner / cnw_recovery | 固定方法读取、真实阶段执行/持久化、上游SHA消费、失败历史和受影响恢复 |
| cnw_lint / cnw_review | 双Lint、独立五Lens、逐Finding三Verifier、Completeness和修订反馈 |
| cnw_live_authorization / cnw_operation_authorization / controller_trust_loader | 请求/实现身份、独立Controller与Owner许可、受保护部署信任验证 |
| cost_guard / p2_cost_guard | 一个RunAccount、共享slot/账本、累计预算/次数、reserve/settle/UNKNOWN |
| cnw_nk_adapter / cnw_critics_adapter / critics_bridge / p2_06_critics_run | 固定NK/CritiCS原生方法、实际输入结果/父Run/费用绑定，可选辅助 |
| cnw_import_workflow / cnw_maintenance / cnw_operations / cnw_arc / cnw_sprint | 官方导入/维护/批准修订/Arc/Sprint触发职责；不代替11阶段 |
| cnw_export / studio.ps1 / studio_health | 可读候选导出、显式入口派发、离线组件身份检查 |

`p2_cost_guard.py`和`p2_06_critics_run.py`虽保留历史文件名，已有通用生产消费者，不能按名字移除。历史Policy/snapshots及受限旧身份映射保留原SHA；新项目不继承旧故事事实、许可或预算。旧数据依旧原位受保护，不声称全部已搬到DataHome。

## 固定源码与依赖

三上游gitlink、patch/lock及许可证保留。按 [bootstrap](../docs/BOOTSTRAP_VERIFICATION.md)在新clone验证固定commit，实际准备参考/构建/env；不把空gitlink当源码、不复制旧私有runtime/项目。cache缺失时离线明确失败，不悄悄联网。Node用于真实shim测试，CritiCS依赖只由lock安装。缓存/构建和私有数据的正式迁移另受危险门控制。

## 模型、请求与费用

Provider/模型/endpoint、token cap、extra参数和费用Policy由冻结当前配置及许可核验，不使用本文写死默认值或历史campaign无上限授权。输出token与文学ADVISORY目标不同。保持真实返回usage/model，截断/非法响应明确失败，成功或UNKNOWN不重复请求/清零。Key和Authorization不得进入Git、请求原件或公开证据。

V2授权在高低入口、slot/reserve前与实际发送边界核验；重建精确请求，检查当前资料、合同、source/Policy/Workflow、实现和期限。运行状态自报、普通签收JSON、单有Key或工程ACCEPT不能授权发送。批内读取去重不跨请求缓存许可。辅助ready后仍重验原PENDING/账户/消息/cap，失败保留原归属。

## 恢复、测试与交付

请求/产物/回执/版本私有保存，阶段身份包含实际构造器和依赖；新实现不冒称旧签名仍有效。匹配阶段复用，受影响阶段显式失效/恢复，原文件及账本历史不覆盖。

验证用自包含临时虚构项目，只替换最终传输边界；实际读取、校验、写入、审稿/修订/导出函数运行。标注MOCK_ONLY/SIMULATED并测试拒绝Live/正式晋升。普通pytest或清Key不是系统断网证明。

每Atom汇总全部发现问题、集中修复和统一复验，独立Controller对精确C/T全范围签收、冻结、正常推送及回读后才开始下一Atom。必要旧行为按冻结身份复用；发生真实退化须修复，不删oracle或重写历史。当前产品终验和生产信任部署仍未完成。
