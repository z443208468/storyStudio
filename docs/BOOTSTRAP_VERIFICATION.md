# 干净克隆：离线 CNW 验证环境

这是 R5 §09.2 的可复现准备步骤。它准备源代码、固定方法参考与验证所需的 CritiCS 依赖；不选择真实 DataHome、不导入旧项目、不调用 Provider、不授权费用、迁移、生产或正式晋升。当前 V2 原生 Live 入口仍未开放，不能据此启动真实创作。

## 1. 声明工具与源代码

已验证工具：Windows PowerShell 7、Git、Python 3.13（验证套件）、Python 3.11（锁定 CritiCS 依赖）、uv。Python 3.13 须安装 `httpx==0.28.1`、`pytest==9.1.1`；pytest 9.1.1 自带 subtests 支持。CritiCS 全部依赖由 `requirements/critics-api.lock` 指定。无需常驻 NK 服务。

联网取得代码时，使用一个**新空目录**：

```powershell
git clone --recurse-submodules https://github.com/z443208468/storyStudio.git <new-empty-directory>
Set-Location <new-empty-directory>
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git submodule status
```

校验所检出的候选 C/T；三个固定上游必须与下表及 Git gitlink 一致。空的 gitlink 目录不算源码已安装。

| 子目录 | 固定 commit |
|---|---|
| `third_party/claude-novel-workflow` | `97ad71fe5e5e76a82275c6c63d4add06fb60ab6e` |
| `third_party/CritiCS` | `fbf66cbc913012c6f80af1687e27f0ce350475e3` |
| `third_party/narrative-keyframing` | `b857f34b7d371ae82c30e00eb021884c14d08ae9` |

**完全离线路径**：使用包含候选 main 与上述 commit 对象的本地 Git 缓存/审查源码 bundle。主库 `git clone --no-local --no-recurse-submodules <main-git-cache> <new-empty-directory>` 后，为每个子模块指定含有对应固定 commit 的本地 Git 缓存，再由 Git 按父仓库 gitlink 正式初始化：

```powershell
git submodule init
git config submodule.third_party/claude-novel-workflow.url <claude-novel-workflow-git-cache>
git config submodule.third_party/CritiCS.url <CritiCS-git-cache>
git config submodule.third_party/narrative-keyframing.url <narrative-keyframing-git-cache>
git -c protocol.file.allow=always submodule update --init --checkout --no-fetch -- third_party/claude-novel-workflow third_party/CritiCS third_party/narrative-keyframing
git submodule status
```

将 `<...-git-cache>` 替换为本机包含对应提交对象的仓库路径。初始化结果必须显示三个固定 SHA 且没有 `-` 或 `+` 前缀。仅复制 Git 源码对象。不得复制原工程 `runtime`、`workspace`、`runs`、`.env`、Provider raw、小说数据或真实费用账本。

## 2. 先记录纯源码状态，再 bootstrap

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -File tools/studio.ps1 doctor -AppOnly
```

纯源码 doctor 应报告 `project=NOT_SELECTED`、`provider_call=none`、`generic_live_production=NOT_RUN`，作者参考为 `RUNTIME_MISSING`。可选组件可能 `UNAVAILABLE` / `IDENTITY_MISMATCH`，它们没有被构建，不视作 READY。引擎文件检查使用实际 `config/policies/`；作者 workflow/roles 的完整性由单独的固定参考 blob/hash 检查，不要求不存在的根目录模板副本。

在已经安装上述 Python/工具、且 uv 公开包缓存包含完整 lock 的机器上：

```powershell
pwsh -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/bootstrap_verification.ps1 -Offline -Python313 <python-3.13-executable> -Python311 <python-3.11-executable>
```

脚本核对三个固定源码 commit 与 clean 状态，捕获 CNW 固定参考，通过现有 `build_critics.ps1` 从 Git archive 应用已哈希绑定 patch/lock，建立新的 CritiCS Python 环境，并用 `uv pip install --offline` 安装 lock、`uv pip check --offline` 核查依赖。它拒绝覆盖已有参考/build/env，适用于新的空 clone；中断后的目录保留，重新验证使用另一个新目录。

**缓存缺失时明确失败**，不会隐式转联网或借用旧环境。可先在用户选定的联网准备环境安装 Git/Python3.13/Python3.11/uv，以及验证库：

```powershell
uv pip install --python <python-3.13-executable> --index-url https://pypi.org/simple httpx==0.28.1 pytest==9.1.1
pwsh -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/bootstrap_verification.ps1 -Python313 <python-3.13-executable> -Python311 <python-3.11-executable>
```

未传 `-Offline` 时只允许 uv 从声明的 PyPI 索引取得 lock 中的软件依赖，仍不调用模型。离线验收应在取得源/依赖缓存后，新建另一个 clone 用 `-Offline` 重新准备；不能把联网准备命令称作断网运行。

准备后的 doctor 应显示 `ENGINE_READY`、`core_runtime=READY`、`author_reference=PINNED_REFERENCE_VERIFIED`、`optional_critics=AVAILABLE_PINNED`。NK 未构建/启动，可选状态如实保留；本轮完整模型链 fixture 的 NK/CritiCS 均 DISABLED，组件 ENABLED_BUT_UNAVAILABLE 另有失败负例。这不证明新环境的 NK/CritiCS Live 功能或费用授权。

## 3. 跑真实消费者的离线套件

从该 clone 根目录执行；Python 3.13 的路径是上一节显式选择的验证解释器：

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = (Get-Location).Path + [IO.Path]::PathSeparator + (Join-Path (Get-Location).Path 'tests')
& <python-3.13-executable> -m pytest tests -q
git status --porcelain
```

套件使用自包含虚构项目与临时 DataHome。模型传输模拟输出标 `MOCK_ONLY / SIMULATED`；完整阶段、工作流、读取、持久化、恢复与导出运行真实消费者。保留命令/退出码、完整 stdout、源码 SHA、阶段请求及非空文件 SHA；`git status` 应为空，模拟不得过 Live/正式晋升门。README、脚本成功或测试数量不替代精确候选 Controller 签收。
