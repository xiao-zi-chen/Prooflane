# 开始使用

**简体中文** · [English](getting-started.en.md)

控制台组织任务，执行器在目标系统运行应用。也可以将任务导出，在测试者的电脑上独立执行。

## 安装控制台

需要 Python 3.11+。下载或检出完整项目，在包含 `requirements.txt` 的目录执行命令。

### Windows

在 PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

默认启用本机执行器。桌面已登录且未锁屏时，它可以领取 Windows 任务。

也可以运行 `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1`；脚本会创建虚拟环境、安装依赖并启动服务。

### macOS / Linux：仅运行控制台

以下命令不启用本机 GUI 执行器，适合整理任务或给其他测试者导出执行包：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PROOFLANE_LOCAL_WORKER=0 python -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

实际运行应用还需安装平台依赖并配置权限，见[节点接入](multiplatform.md)。macOS / Linux 的桌面适配器尚待实测，控制台能启动不代表 GUI 测试通过。

### 确认启动

打开 `http://127.0.0.1:8765/`，应看到“测试概览”。`GET /api/health` 返回服务和执行器状态。首次启动会创建数据目录和注册凭据，位置见[配置说明](configuration.md)。启动失败时见[问题排查](troubleshooting.md)。

## 运行示例

在 Windows 控制台点击“创建示例任务”。它会准备三份 Notes 示例并提交相同的四步操作：等待窗口、输入笔记、保存、检查文本。

Windows 示例编译依赖 .NET Framework 的 C# 编译器。macOS 示例使用 PyObjC / AppKit，Linux 示例使用 GTK 3；后两者需要对应机器和依赖，不能在 Windows 上执行。

- 有匹配节点的平台开始运行，结束后显示截图、录像和报告。
- 没有节点的平台停在“等待节点”，没有运行截图。
- 选择步骤、放大图片或切换录像；“平台对照”显示各平台逐步结果。

## 提交自己的应用

1. 打开“发起测试”，选择平台与架构。
2. 上传对应系统的构建，单文件最大 300 MiB；压缩包保留应用实际目录结构。
3. 填写主窗口标题及应用路径。安装模式还需安装后的完整程序路径；Windows 安装器需静默参数。
4. 配置 3–5 步验收，写清控件名称或 ID，以及预期文本。截图验收步骤需要人工复核。
5. 需要对照时点击“添加另一个平台”。各平台步骤名称和动作一致，定位信息与预期文本可分别调整。
6. 点击“开始测试”，查看任务状态。

步骤字段见 [API](api.md) 和 [JSON 示例](../examples/run-spec.json)。示例中的全零 `package_id` 是占位值，提交前需替换为上传接口返回的 ID。

## 由其他测试者执行

在等待平台的结果区域点击“导出执行包”，或进入“执行策略”。选定具体任务后下载 ZIP；需要附带构建时勾选“将应用文件一起放入 ZIP”。

测试者按包内 README 预检并运行，返回 `receipt.json` 和 `evidence.zip`，无需连接你的控制台。分工和复核要求见[执行策略](execution-strategy.md)及[证据验收](handoff-acceptance.md)。

同一执行包内包含中英文说明、验收表和邀请草稿，可按语言选择阅读。

独立结果不会自动导入控制台。需要持续领取任务和自动回传时，再[接入在线节点](multiplatform.md)。

## 理解结果

| 界面状态 | 含义 |
| --- | --- |
| 等待节点 | 目标系统尚未执行 |
| 通过 | 当前配置的检查通过；覆盖范围以本构建和场景为限 |
| 待复核 | 存在人工检查或证据问题，需要查看截图和报告 |
| 失败 | 安装、操作、断言或采集失败，需结合日志判断原因 |
| 已取消 / 已中断 | 执行未完整结束；保留已有证据，重试前确认应用状态 |

停止服务用 `Ctrl+C`。停止前先处理运行中的任务；重启不会自动重做中断的安装。构建和证据默认保留，需要自行安排留存和清理。

返回[文档目录](README.md)。
