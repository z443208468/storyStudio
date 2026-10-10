# StoryStudio P3：原作者正式文学工作流逐项源码映射与施工包

## 这包里是什么

这是 **完整下一版具体施工方案**，不是空泛设计纲要，也不是已经完成的产品。已经通过 GitHub 原始 Git blobs 实地核对 CNW 作者文档/模板和 StoryStudio 现有关键源码，按 source → current → target → negative test 形成可执行工单。

目录：

- `MASTER_PLAN_P3.md`：W00–W11 按依赖顺序的完整实施与验收合同。
- `CODEX_START.md`：直接发给正在跑任务的 Codex 唯一启动指令。
- `CONTROLLER.md`：委任验收子智能体的必读职责。
- `reference/CNW_ORIGINAL_SOURCES.md`：原作者源文、Git blob、关键行号和分歧说明。
- `mapping/P3_SOURCE_TO_CODE_MATRIX.md`：M01–M38 原方法到当前文件/函数的逐项映射，F01–F07 精确改动方案。
- `spec/CNW_ROLE_INPUT_OUTPUT.md`：Scene/Episode、Plot/Card/Brief/Prose、5 Lens/3 Verifier、缓存、修订、导出等数据和方法合同。
- `tests/P3_ACCEPTANCE_TESTS.md`：有正反例的 40+ 项工程/文字/安全验收。
- `tools/capture_cnw_reference.py`：在用户 Windows 上从**已有固定 Git 子模块**按字节复制作者公开文档和模板，并产生准确来源 hash manifest，不更改 Vendor、不调用付费 API。

## 与 P2.1 的核心差异

P2.1 主要列缺陷；P3 在查阅原作者真实方法和 StoryStudio 已提交代码后，**定位了每个缺口的原始文档路径、当前代码函数/行号、新目标实现与负例测试**，且 W00 明确要求先把真正的原文复制到用户本机，再实施、验收。

## 怎么交给 Codex

1. 把这个 ZIP 交给目前的 StoryStudio Codex 会话（或解压为单独的**工单输入目录**，不要直接覆盖现有产品文件）。
2. 明确要求它先完整阅读 `CODEX_START.md` 与 `MASTER_PLAN_P3.md`，W00 用本包 `tools/capture_cnw_reference.py` 真正在 `D:\CangqiStudio\StoryStudio` 复制原作者文档并核对 SHA。
3. 要求它根据 W01 再检查当前 WIP，没有按旧 `0b40876b` 强制重做/回退。
4. 由原独立 Controller 逐 W 段验收，先离线验证通用新 ID，再只重写**同一**合法《苍歧》场景；不得扩量写第二场。

**注意**：目前 ChatGPT 环境不能直接进入你的 Windows `D:` 盘，因此这里提供的是可在 Codex 当前 Windows 工作环境运行的实物提取脚本及已经在 GitHub 核查的映射，而不是声称已在你的 D 盘实际运行。运行后的本机 `CNW_LOCAL_REFERENCE_MANIFEST.json` 才是 W00 的真实完成证据。
