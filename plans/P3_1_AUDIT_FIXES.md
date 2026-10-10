# P3.1 独立复核纠正记录（仅高影响项）

此版替换前一 P3 候选。基于 StoryStudio `main@939eca90c030cf726b1879e2b1115f0e07ed6f6c` 与 CNW `@97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` 的代码和固定文档，再检查实际本机 WIP 仍是 Codex 责任。

| 问题 | P3 原缺陷 | P3.1 具体修法 | 拦截点 |
|---|---|---|---|
| W04/W06 前置死锁 | W04 要验四岗，Prose W06 才编写 | W04 只验新项目导入+Plot/Card/Brief+Prose 合同，W06 验生成器 | W04/W06, M03 |
| 未真正支持新剧本输入 | M04 提及 importer，W00–W11 无施工/来源导入验证 | W04 加 `cnw_project.py` 的 `project init/import-source`，W09 从两份真实虚构 `.md/.json` 原文开始 | B01/W04/W09 |
| W07 提前要求 Live ID | W10 之后才允许一场实测 | W07 `MOCK_ONLY` 独立隔离验收；W10 必需真实模型各角色+账单证据 | D01/W07/W10 |
| 外部 Controller 幻觉 | standalone runner 假设随时可获 Codex 子智能体接受 | CLI 生成 `READY_FOR_EDITORIAL_REVIEW`，只能使用真实外部审阅证据 promote | B07/W05 |
| 单场验收被冒充全线 Live | W10 只有 Scene Live，W09 只模拟 Episode/Sprint | 分别记录 Scene Live / Episode Offline / New Project Offline，Episode Live 显示 NOT_RUN | E10/W11 |
| 候选分支未明确 | main 已有 P2 代码，可能将未签候选直接推 main | 安全新工作分支，提交后 Reviewer、remote readback，最后安全归并 main | 0A/W02 |
| 费用跨项目误授权 | 原 ledger 是 P2 单一活动；新项目可能自建 ¥10 预算 | 首场继续旧账本；通用账本可参数化但需要实际额外授权；默认不增加预算 | W05/E03 |

## 复核边界

- ZIP 结构、文件 SHA256、提取脚本静态语法与隔离模拟 Git 仓的幂等/dirty 拦截可以在本环境测试。
- 用户 Windows 的 W00 原文真实复制、依赖安装、P3 新功能代码、真实中文写作和真实费用属于后续执行，不在此文件里冒称成功。
- 公开 CNW 提供方法文档、样板和模板，不是原作者隐藏生产 Agent 的可安装程序；本工程只能实现有来源的公开方法。
