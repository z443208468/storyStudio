**返修候选限定接受：ATOM07离线工程门通过。允许按下述精确范围正常推送；包job自动故事交付仍未通过。**

```text
CONTROLLER_VERDICT=ACCEPT_LIMITED
ATOM_ID=ATOM07
REVIEWED_COMMIT=08b4fa44292809ce8553849945ee5a1eaf3236fa
REVIEWED_TREE=c484a92f117a12f30c35e9f31da628630ccdc900
REVIEWED_PARENT=4b91436dcdb7afe18b2bcc1503e49cdbd3e57a21
REVIEWED_PLAN_SHA=AE5A1959EEAB75AD6A8F41460C38BF9678284C1D51A8D63B25CE37F7CB4F5183
UPSTREAM_METHOD_PIN=97ad71fe5e5e76a82275c6c63d4add06fb60ab6e
REVIEWED_WORKTREE=CLEAN
```

| 裁决项 | 结论 |
|---|---|
| CODE_FIX | **ACCEPT_LIMITED**：包含返修祖先的最终树，已关闭本轮定位根因 |
| ATOM07_OFFLINE_ENGINE | **ATOM07_OFFLINE_ENGINE_ACCEPT** |
| METHOD_FIDELITY | **ACCEPT_LIMITED**：当前差异和消费者范围无方法漂移 |
| EARLY_E2E | **ACCEPT_LIMITED / SIMULATED_OFFLINE**；不等于ATOM09或包产品门 |
| 历史保护 | 本轮核对的TS、合同快照、账本及冻结基线保持 |
| INPUT_PACK_TO_STORY_GATE | **RETURN**：尚缺job自动全链至故事导出 |
| GIT_PUSH_AUTHORIZATION | **AUTHORIZED，仅限下述精确快进范围** |

实际目录和路径别名现在先经过原有traversal/reparse检查，再解析真实路径，并对两个保留目录名作`casefold()`比较。真实磁盘大写目录的红测确实到达禁止的mock费用守卫；修复后的同方法及全部8项门测试通过。三处缓存消费者明确绑定`extra=None`，唯一Run登记、严格模拟标记、实例/Run/stage/role/request/output身份检查均保留；低层HTTP入口在模拟会话内仍拒绝。

独立核对的验证原件包括：

- 精确08b冷clone：**68 passed、83 subtests、exit 0**；raw SHA `6cccd866e8f7bed29bbbe2ca55aab059f6820b054b56c275303d2dc890476550`。
- 10条命令的raw哈希全部匹配；169份记录源码逐份匹配冷clone及精确Git对象，源码未变、clone干净。
- 最终8项门测试：8 passed、37 subtests；raw SHA `c8ab6cab44609725a137f670c3d463ca83519cc58aa24fd2c8f5deb8d32e7af6`。
- Python3.13及3.11的六文件语法检查通过；**没有宣称完整行为suite在3.11执行过**。
- 原始失败、此前错误预期、我的`../`错误推断及Writer纠正均保留；4b的原RETURN未追改。

Early原件SHA为 `d51338c2aec88e040fce1f31c49f2b087de995863974532c9fcacb2a64ac6451`。已读取11阶段实际内容和16份模型请求，核对Cards/Brief消费同Run产物、Prose仅直接读取Brief/声线、五Lens独立材料、三路反证2/3、遗漏进入Refine及新全文进入受影响Re-review。初稿与修订稿并存，可读导出保持明确候选状态。该fixture的Lint为`NO_EXECUTABLE_RULES`，不将其宣称为完整禁式正负覆盖。

Workflow证据SHA为 `52e30bd1e8f8f87a480f3a5b73a7cf4c227568b1013535c749866479485893a3`。已核对导入/增量冲突保留、Audit/Handoff、独立Workflow03及恢复消费者；1111份嵌入实际文件哈希一致，17个操作Run的17份模拟回执与其请求/raw及实际所有者绑定一致。模拟票不能取得Live权限或用户创意接受。

本差异对M01–M10未改变角色、审稿和修订职责；对M11–M12仅补操作/缓存授权，来源分类、保护和批准规则保留；M13–M15的Sprint、辅助及工作意图未被替换；M16明确保持工程、模拟、可信签收、Live和创意接受分层。**完整M01–M16总验仍归ATOM09/10。**前瞻代码身份变化已明示，不宣称旧执行身份完全相同。

最后直接回读仍确认：

```text
TS_STATUS=EXECUTION_INCOMPLETE
TS_FIRST_FAILURE=DEEPSEEK_API_KEY_REQUIRED
TS_PROVIDER_REQUESTS=0
TS_STATE_SHA=3bae0722506641f1c14840d2f2568f03484cd6b1298c972baf3700d0de42ee0d
TS_CONTRACT_AND_SNAPSHOT_SHA=e70f72c935d5dbd1262537071a5f2893f9d76b265bdd7ee95c069507c6b8952c
LEDGER_SHA=c8b0705f491ef824db01be0b7991f4db9db7d84e153c26481e93a4fdcd0eab9b
FROZEN_BASELINE=26b72cea21dce45eede21cffddd4e75307d75652 / 535496ba3b8a331e12d0e5e161b15bf21a25393e
FROZEN_BASELINE_STATUS=CLEAN
```

已独立确认远端main仍为 `50ee75fa147c068d84dd35e5375c1bc668cf2c46`。**允许正常快进推送：**

```text
50ee75fa147c068d84dd35e5375c1bc668cf2c46
→ 4b91436dcdb7afe18b2bcc1503e49cdbd3e57a21
→ 08b4fa44292809ce8553849945ee5a1eaf3236fa

FINAL_TREE=c484a92f117a12f30c35e9f31da628630ccdc900
```

这是对返修后最终树及必要失败祖先的推送授权，**不追认4b当时通过**。推送后回读远端C/T；若身份或范围变化，停止复核。

回读一致后允许进入**ATOM08安全源码/文档范围**：分类整理、通用说明及必要消费者转接；撤除仍有功能的入口前须证明替代消费者并接受精确候选。**不迁移、删除或切换旧私有数据。**08当期门接受后，09再完成断网虚构包job自动全链至导出的产品验收。

`W10_ATTESTATION_PENDING`、TS Live未授权、恢复资格未成立、`GENERIC_LIVE_PRODUCTION=NOT_RUN`、`CUTOVER_BLOCKED=true`保持。真实信任部署和Live适配不追加为本轮离线前置。Controller未运行测试、修改文件、调用Provider、提交或推送。
