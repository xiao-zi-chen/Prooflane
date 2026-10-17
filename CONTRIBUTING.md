# 贡献指南

**简体中文** · [English](CONTRIBUTING.en.md)

欢迎提交可复现的问题、文档修正和范围明确的改动。较大的设计调整建议先说明使用场景、现有问题和预期行为，再开始实现。

项目仍处于预览阶段，尚未指定开源许可证。参与前请先与维护者确认贡献和后续发布的许可安排；本文不要求转让版权。

## 准备开发环境

需要 Python 3.11+；前端语法检查使用 Node.js 22 或更高版本。普通控制台开发不需要 macOS / Linux 的桌面依赖。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

后面的 `python` 指虚拟环境解释器。若 PowerShell 禁止激活脚本，可用 `.\.venv\Scripts\python.exe` 替换，不必改变全局执行策略。

## 按改动选择检查

| 改动 | 最少检查 |
| --- | --- |
| Markdown、图片、文档链接 | `python scripts/check_docs.py`，检查页面渲染；示例命令有改动时核对实际行为 |
| Python、接口、包处理或调度 | `python -m pytest -q`；行为变化补充有意义的回归用例 |
| 前端 | 下方三项语法检查，以及涉及页面的桌面和窄屏交互 |
| 桌面适配、安装、采集 | 对应系统上的实际应用测试，保留环境和证据；没有设备时标记未验证 |
| 执行包及其文档 | 导出通用包和绑定任务包，检查内容与链接；运行逻辑变化时再验证独立执行 |

```bash
python -m pytest -q
python scripts/check_docs.py
node --check static/app.js
node --check static/workspace.js
node --check static/strategy.js
```

`pytest` 使用临时数据目录，主要验证模型、API、包边界、调度和导出；Windows 用例还会编译示例，但不执行 GUI。不要把 CI 的多系统通过称为三平台桌面验收通过。

[CI 工作流](.github/workflows/checks.yml)在 Windows、macOS、Ubuntu 上配置 Python 3.11 / 3.12 的代码测试，并检查文档和 JavaScript。工作流文件本身不是运行成功的证据，应查看具体提交的 Actions 结果。

## GUI 和浏览器验证

先启动本地服务并确认执行桌面空闲。浏览器脚本使用 Playwright 的 Microsoft Edge 通道，需要本机安装 Edge。

| 脚本 | 前提与影响 |
| --- | --- |
| [e2e_windows.py](scripts/e2e_windows.py) | Windows 桌面；会创建任务、运行和安装自带样本 |
| [browser_check.py](scripts/browser_check.py) | 已运行的控制台；有 Notes 样本时会提交并执行 Windows 任务 |
| [browser_workspace.py](scripts/browser_workspace.py) | 默认创建三平台示例；可指定 `--existing-campaign` 复用已有四步结果，使用 `--keep-demo` 保留等待任务 |
| [browser_multiplatform.py](scripts/browser_multiplatform.py) | 验证多平台表单和等待状态；会创建测试任务 |
| [check_strategy_delivery.py](scripts/check_strategy_delivery.py) | 需要已有 Windows 四步演示和等待中的 Linux 任务；会导出并独立执行 Windows 样本 |
| [e2e_remote_agent.py](scripts/e2e_remote_agent.py) | Windows 桌面和空闲端口 8766；启动临时控制台与 HTTP 节点，执行样本 |
| [msi_check.py](scripts/msi_check.py) | Windows、Python 3.11 / 3.12；构建、安装、验证并卸载 MSI 样本 |
| [capture_check.py](scripts/capture_check.py) | Windows 执行器空闲；检查应用被遮挡后的采集 |

这些脚本的具体前提和输出以脚本为准。GUI 测试应串行运行，使用专用测试桌面；文案或布局调整无需重跑安装器。

## 代码和文档风格

- 保持现有技术栈和目录结构。新增依赖需说明解决的问题。
- 一个改动解决一个明确问题，避免混入无关格式化。
- 用户文案直接描述操作、状态和下一步，避免口号和重复保证。
- 说明“已实现”“已验证”和“计划中”的区别，不补写未发生的测试结果。
- 新文档加入[文档目录](docs/README.md)，相对链接要能从源码检出中打开。
- 中文和英文对应页一起维护；有翻译缺口时在 PR 中说明。CI 会检查对应文件和语言切换链接。
- 会进入执行包的三份文档须能独立阅读，不依赖仓库内其他页面。
- 不提交 `data/`、`agent-data/`、`artifacts/`、凭据或客户应用；公共截图放入 `docs/assets/`，先检查内容。

## 提交 PR

说明原来的具体问题、修改后的行为、验证方式和仍未覆盖的范围。界面改动附截图；行为变更更新相关文档和 [CHANGELOG](CHANGELOG.md)。未运行的检查写“未运行”并注明原因，不用空泛的“全部通过”。

普通缺陷使用[问题模板](.github/ISSUE_TEMPLATE/bug_report.yml)，功能建议说明实际使用场景。安全问题请先阅读 [SECURITY](SECURITY.md)。

Issue 和 PR 均可使用中文或英文；仓库也提供独立的英文 Issue 表单。
