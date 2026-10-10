# CritiCS 生产依赖安全审计

- 审计范围：`requirements/critics-api.lock`，Python 3.11.15；扫描器：PyPA `pip-audit` 临时工具环境；原始 JSON 仅私有保存于 `runtime/build/CritiCS/p2-02-candidate-001/pip-audit.json`。
- 原始报告 SHA256：`51AE783FEB7A94371D197C0942EF177228E3E23DCE66FC8872EE1D24979D6540`
- 扫描结果：报告 27 个 advisory records、涉及 5 个包；其中存在重复别名/公告记录，因此不能称为 27 个独立漏洞，也不把结果表述为“依赖无漏洞”。

## 适用性判断

本次启用的是本机 CLI 中的 `Critic.three_critic()`、`modifiedStoryline()`、`Refinement.Two_refinement()`，仅构造文字型 ChatOpenAI 请求；无图像 URL、文件搜索工具、prompt/chain 文件加载、LangChain `load/dumps/loads` 反序列化、LangSmith prompt pull、TracingMiddleware 或外部 LangSmith tracing。桥接强制禁用 tracing，并将写入限制在私有 `runs/`。

| Advisory family reported | Selected path assessment |
|---|---|
| GraphCypherQAChain / CVE-2024-8309 | 未安装 `langchain-community`，且未构造图数据库 QA chain；GitHub advisory 将 Python `langchain` 的受影响范围列为 `<0.2.0`、community `<0.2.19`。当前 `langchain==0.2.11` 不落在前者范围。 |
| Prompt/path loaders and filesystem middleware | 生产路径不使用文件/Agent 工具、path loader 或用户提供的模板配置；唯一提示模板是受控上游 Python 常量。 |
| LangChain prompt/serialization advisory | 不接受 LangChain template 字符串或序列化构造对象；输入经 bridge 作为普通文本拼接到原提示。 |
| Text splitter XXE/URL fetch | 未调用任何 text splitter 或 HTML/XML loader。 |
| LangSmith prompt pull/tracing middleware/redaction | 不调用 prompt pull，不启动 tracing server；桥接显式关闭 LangChain/LangSmith tracing。 |
| ChatOpenAI image-token SSRF advisories | 仅发送文本，不接受 image URL，不调用 image token counting。 |

以上是按已检查调用图得出的适用性判断，不是全包安全声明。`langchain-core`、`langchain-openai` 和 `langsmith` 仍被扫描器标记为有非所选辅助功能相关公告；若今后启用这些辅助功能，必须先升级/复核其边界。依赖选择保留上游 LangChain 0.2 对话链接口，避免把工具方法替换成自制批评器。
