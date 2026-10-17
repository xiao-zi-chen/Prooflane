# 配置说明

配置通过启动进程的环境变量传入。默认监听 `127.0.0.1:8765`，用于本地或私有连接。

## 控制台

| 配置 | 默认值 | 用途 |
| --- | --- | --- |
| `PROOFLANE_DATA` | 项目根目录的 `data/` | SQLite、构建、运行证据和注册凭据的位置 |
| `PROOFLANE_LOCAL_WORKER` | `1` | 仅值为 `1` 时启用本机执行器；设为 `0` 只调度其他节点 |
| `PROOFLANE_AGENT_TOKEN` | 数据目录中 `agent-token` 的内容 | 覆盖本次服务使用的节点注册凭据；不会同步改写文件 |
| `PROOFLANE_ALLOWED_HOSTS` | 无额外主机名 | 逗号分隔的额外 Host；默认已允许 `127.0.0.1`、`localhost`、`testserver` |

Host 白名单只检查请求主机名，不是访问控制或账户认证。监听地址和端口由 Uvicorn 的 `--host`、`--port` 指定。

Windows 纯控制台示例：

```powershell
$env:PROOFLANE_LOCAL_WORKER = '0'
$env:PROOFLANE_DATA = 'D:\ProoflaneData'
.\.venv\Scripts\python.exe -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

这些变量影响当前终端及其子进程。普通运行保持单个 Uvicorn 进程；启用本机执行器时不要使用 `--workers` 或自动重载，以免竞争桌面、重复启动或中断任务。

## 数据位置

| 路径 | 内容 |
| --- | --- |
| `data/prooflane.db` | 构建元数据、任务、节点和平台对照记录 |
| `data/packages/` | 上传的原始构建 |
| `data/runs/<id>/` | 单次运行的工作目录、日志、媒体和报告 |
| `data/agent-token` | 初次启动生成的节点注册凭据 |
| `agent-data/` | 在线节点自己的缓存与执行数据 |
| `results/<id>/` | 独立执行包产生的回执、证据 ZIP 和内部执行目录 |

自定义 `PROOFLANE_DATA` 后，控制台上述路径相对于新目录。在线节点和独立执行器使用各自的 `--data` / `--output`，不复用控制台的数据目录。

当前没有自动留存清理、数据库迁移命令或在线备份接口。完整备份应在任务结束、服务停止后复制数据目录，并保留原路径关系；数据库内含构建路径，迁移到其他路径需另外验证。恢复时使用匹配的代码版本和依赖，避免把只复制数据库当成完整备份。

## 节点参数

```bash
python -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name test-node
```

| 参数 | 默认值 / 要求 |
| --- | --- |
| `--server` | `http://127.0.0.1:8765`，可指向 SSH 私有转发入口 |
| `--token-file` | 必填；保存注册凭据的 UTF-8 文件 |
| `--data` | 当前目录下的 `agent-data` |
| `--name` | 当前机器名；建议改为不含个人信息的测试机名称 |
| `--once` | 只完成一次领取尝试或一个任务后退出，适合调试 |

注册凭据用于换取节点专属凭据。改变注册凭据不会撤销已注册节点的凭据；当前没有网页撤销接口。疑似泄露时先停止服务及受影响节点，再检查数据目录和连接记录，见[安全说明](../SECURITY.md)。

Linux Xvfb 辅助脚本使用 `PROOFLANE_LINUX_NODE_ROOT` 指定虚拟环境和节点数据的根目录，默认 `~/.local/share/prooflane-linux`。它不会安装系统依赖，依赖准备见[节点接入](multiplatform.md)。

## 独立执行参数

```bash
python -m prooflane.handoff --manifest scenario.json --package "应用文件路径" --check
```

`--manifest` 默认 `scenario.json`，`--package` 必填，`--output` 默认 `results`。`--check` 只校验任务、构建、系统、架构和桌面就绪状态，不启动应用。

移除 `--check` 后执行。退出码 `0` 表示自动检查通过，`2` 表示待复核，`1` 表示未成功完成；回执中的 `review_status` 始终从 `pending` 开始。具体回传要求见[证据验收](handoff-acceptance.md)。

返回[文档目录](README.md)。
