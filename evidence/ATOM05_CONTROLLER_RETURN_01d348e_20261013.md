## 精确后继裁决

C=`01d348e4ccb2bd905cb1ea30ba64bde0b429f8e0`  
T=`82c10d66aea1c5fc5fb2136c918251eb97afdb5d`  
父=`3a911ab51ca849925e3d526a964b048a4304587b`

```text
CURRENT_ATOM_CLOSURE_VERDICT=RETURN
METHOD_FIDELITY_VERDICT=RETURN_FOR_UNGUARDED_REGISTERED_NATIVE_ENTRY
FREEZE_SCOPE=PRIOR_ACCEPTED_SCOPES_PRESERVED; NO_NEW_ATOM05_CLOSURE
NEXT_ATOM_PERMISSION=DENIED
GIT_PUSH_AUTHORIZATION=NO
```

### 上次根因已修复

`_validated_native_materials()` 已由 main 和下层共同调用，注册 input、实际消费的 critique 或 output 不能降级到无父 Run 的 legacy 路线。

已核实新增真实入口负例、V1 兼容及注册组件效果；35 passed/20 subtests、Python3.11 三例的 raw 与最终源码匹配。八份新增记录 Git 字节 SHA 全匹配，两个新捕获中的费用上下文、请求/响应/输出、非零 UNKNOWN 和实际回读一致。

**原 `3a911ab` RETURN 原文 SHA 精确匹配 `899bd275…53d78b5c`，原判不改写。**

### 当前唯一明确阻断：独立 bridge CLI 未经过费用边界

[critics_bridge.main](D:/CangqiStudio/StoryStudio/tools/critics_bridge.py:125) 与其 `__main__` 仍可直接接受注册项目材料和输出目录，然后：

1. 创建 native 目录；
2. 调用 `configure_provider()`；
3. 直接运行 `Critic`、`modifiedStoryline` 或 `Refinement`。

该入口没有父 Run、RunAccount、共同槽位或 accounting，也不经过已修复的 P2 wrapper 授权。**Build 就绪、Key 可用时，这条 CLI 路径仍可调用模型。**本轮没有执行它；这是实际源码调用链中的 §05.2 消费者缺口，不是缺 Key 或 cutover 问题。

### 最小返修与复验

- 普通 bridge CLI／无受检上下文的 main，对任一注册 input、实际 critique 或 output，在 Key、目录创建和 native 前拒绝。
- wrapper 内部调用须传递并核对已验证的父 Run、child、材料归属及费用边界；不能用 CLI 布尔开关或普通 JSON 放行。
- 补直接 bridge 入口组合负例，核零 Key、零费用、零 native、输入不变；验证有效 wrapper 仍走真实共享账本/槽位，以及合法 V1 兼容。
- 保留原生方法，不 mock 授权求通过，不开展06。

此前晋升恢复、NK 及未变费用证据继续保留，按身份复用；133例仍只代表原版本范围。当前计划 SHA 未变，前序00–04及全部历史裁决保持。

**ATOM05 全部当期工程门尚未闭合，两个本地05提交均不得推送，06不得开启。**本轮未运行测试、改文件或调用 Provider。