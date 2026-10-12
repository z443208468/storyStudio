# ATOM-09 冷克隆全套退回及最小修正

候选 `b024c9432b714dded7be94caff507a10cd9cb8bf` / Tree `1bb4d9cb635f474ad60d8a3e003ebb0a31603ad3` 的独立 Controller 原始裁决为 `CODE_FIX_VERDICT=RETURN`、`EARLY_CNW_E2E_GATE_VERDICT=RETURN`、`ATOM09_STATUS=RETURN`、`GIT_PUSH_AUTHORIZATION=NOT_AUTHORIZED`。不推送、不追认历史 ACCEPT。

精确候选的独立干净克隆 `pytest tests -q` 实际退出码 1：6 failed、300 passed、87 subtests；原始日志 SHA=`533b710c135d3f68d63f380e919b3b7415b690401e68d14db34b77d20f8e1bd0`，外部文件 `cold_clone_b024c94_full_offline_suite.raw.txt` 全部保留。

## 六项根因与修正

1. `test_cnw_adapters` 的 empty Conversation framing、native plan proposal，以及 `test_cnw_runner` 的 native CritiCS result，需明示 CritiCS source+patch build 和锁定 LangChain 的公共依赖运行时。冷 clone 未准备这些 ignored 构建产物，不能以原机已有运行时冒称纯净成功。新候选在隔离 clone 中用固定上游 Git 对象、仓库 patch/lock、公开包的本机 uv 缓存执行 `--offline` 构建/安装；不复制旧 runtime、账本或项目。缺缓存时真实报告不可取得，不伪造模板或依赖。
2. Native proposal 测试也假定已有 `runs/` 父目录；测试 setUp 显式建立自己使用的父目录，临时 proposal 内容和原断言保留。
3. CritiCS bridge 测试 patch `tools.p2_cost_guard.LEDGER`，但实际调用者使用 `p2_06_critics_run.p2_cost_guard` 的模块别名，导致触及真实 ledger 路径。修正为 patch 实际调用者的 LEDGER，并断言虚构 ledger 仍为零请求；生产调用链不改，真实账本字节不改。
4. 两项 policy snapshot 测试证明 Windows checkout 自动 CRLF 变换会破坏冻结策略字节。`.gitattributes` 对文本规定 LF，历史 active `config/production.example.json` 单独 `-text` 保留其原始混合 CRLF 字节。该文件工作树 SHA 一直为 `a7b5e8284264bff0bd8c40960eda1a8f073bfb5e11e395f5c329c7d2b8bdef8a`，与原冻结 snapshot 相同；过去 Git 的文本规范化曾存为 `51cb3eb5e9e9eb8cd1ed4f8757d0c874c99a45ce20321ae47b9aa3b25c3e6013`。本次只让正常新提交保存现有原字节，内容在 CRLF/LF规范化后完全相同，不修改旧 Git、snapshot、历史合同或运行。该文件 `whitespace=cr-at-eol` 仅识别其必要的历史 CR，不关闭其它空白或安全检查。

## 定点验证及未扩张的状态

`cold_clone_failure_roots_scoped` 实际命令：`python -m pytest tests/test_cnw_adapters.py tests/test_cnw_runner.py::RunnerTests::test_native_critics_result_reaches_refine_and_is_verified_on_reuse tests/test_critics_bridge_datahome.py tests/test_policy_snapshots.py -q`。退出码 0，31 passed，原始输出 SHA=`ffff407676ae753d9fbc8ffe356cbb130f2a2d8b18a19b3895f96fc934c7420e`。这是主工作树定点验证，不能代替追加精确候选的独立冷 clone 全套。

新候选仍须完成所有 fixed third_party pin、source/config SHA、完整 suite、实际11阶段与公开工作流产物的重新验证，交独立 Controller 按精确 C/T 审查。候选形成时该门尚待执行，不自签。ATOM-07 仅限定离线状态，生产 W10/TS 信任与授权待定；`CUTOVER_BLOCKED=true`、`PRIVATE_MIGRATION=NOT_RUN`、`GENERIC_LIVE_PRODUCTION=NOT_RUN`。
