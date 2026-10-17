# API

默认地址为 `http://127.0.0.1:8765`。完整请求和响应结构由 `GET /openapi.json` 提供；当前没有启用 Swagger UI 或 ReDoc 页面。

## 请求约定

操作员 API 的修改请求需要 `X-Prooflane-Client: web`。浏览器发送 `Origin` 时，它必须与请求 Host 一致。这个请求头用于跨站请求防护，不是用户身份认证。

节点 API 使用 Bearer 凭据。注册时提交注册凭据，后续请求使用注册响应返回的节点专属凭据。节点流程见[节点接入](multiplatform.md)。

| 状态码 | 常见含义 |
| --- | --- |
| `400` | Host 不在允许范围等请求问题 |
| `401` / `403` | 缺少凭据、客户端标记，或节点不拥有该任务 |
| `404` | 任务、构建或证据不存在 |
| `409` | 当前任务状态不允许该操作 |
| `413` | 上传文件超限 |
| `422` | 输入、构建格式、平台或场景校验失败 |

错误细节读取响应 JSON 的 `detail`，具体状态码以接口返回为准。

## 上传构建并创建任务

以下 Python 示例使用运行依赖中的 `httpx`。把 `path/to/Notes.exe` 换成实际 Windows 构建；成功提交后，在线节点可能立即执行应用。

```python
import json
from pathlib import Path

import httpx

package_path = Path("path/to/Notes.exe")
spec = json.loads(Path("examples/run-spec.json").read_text(encoding="utf-8"))

with httpx.Client(
    base_url="http://127.0.0.1:8765",
    headers={"X-Prooflane-Client": "web"},
    timeout=120,
) as client:
    with package_path.open("rb") as stream:
        response = client.post(
            "/api/packages", files={"file": (package_path.name, stream)}
        )
    response.raise_for_status()
    spec["package_id"] = response.json()["id"]
    response = client.post("/api/runs", json=spec)
    response.raise_for_status()
    print(response.json()["id"])
```

示例以 Notes 的控件和窗口标题为目标。换用其他应用时需调整这些字段，不要只替换文件路径。

## 任务字段

| 字段 | 要求 |
| --- | --- |
| `platform` | `windows`、`macos`、`linux`；默认 `windows` |
| `architecture` | `any`、`x86_64`、`arm64`；默认 `any` |
| `package_id` | 上传接口返回的 32 位十六进制 ID |
| `mode` | `portable` 或 `installer` |
| `app_path` | 压缩包内主程序相对路径，或安装后程序的完整路径 |
| `install_args` / `app_args` | 字符串数组，不是整条 shell 命令 |
| `window_title` | 主窗口标题，不能为空 |
| `steps` | 3–5 个步骤；字段约束见 [models.py](../prooflane/models.py) |

步骤动作包括 `wait_window`、`click`、`type_text`、`assert_text`、`screenshot`。点击和输入必须提供 `target` 或 `automation_id`；文本检查必须提供非空 `value`。单步 `timeout` 为 2–60 秒，默认 15 秒。

平台对照提交 `name` 与 2–3 个 `targets`。每个目标是完整任务配置，步骤名称和动作一致；同一平台与架构组合不能重复。

## 常用接口

| 方法与路径 | 用途 |
| --- | --- |
| `GET /api/health` | 服务与本机执行器状态 |
| `GET /api/platforms` | 平台能力和节点状态 |
| `POST /api/packages` | multipart 上传构建，返回 ID 和 SHA-256 |
| `POST /api/runs` | 创建单次运行 |
| `GET /api/runs` | 最近的运行记录 |
| `GET /api/runs/{identifier}` | 任务详情、步骤与证据索引 |
| `POST /api/runs/{identifier}/cancel` | 请求取消 |
| `POST /api/runs/{identifier}/retry` | 用原包和场景创建新的运行 |
| `POST /api/runs/{identifier}/review` | 提交 `step_index`、`decision`、`note`；索引从 0 开始 |
| `GET /api/runs/{identifier}/bundle` | 下载证据 ZIP |
| `GET /api/runs/{identifier}/artifacts/{filename}` | 读取单个证据文件 |
| `POST /api/campaigns` | 创建平台对照 |
| `GET /api/campaigns` | 对照列表 |
| `GET /api/campaigns/{identifier}` | 对照详情 |
| `POST /api/demo` | 创建 Windows 示例任务 |
| `POST /api/demo/campaign` | 准备三平台示例并创建对照；需要 Windows 示例编译环境 |
| `GET /api/strategies` | 平台执行策略 |
| `GET /api/strategies/{kind}/kit` | 下载说明包或绑定任务的执行包 |
| `GET /api/strategies/{kind}/invitation` | 获取邀请文字，不发送消息 |

执行包和邀请接口可带 `run_id`。执行包接口可再带 `include_package=true`，将原构建包含在 ZIP 中；此参数必须与具体任务一起使用。`kind` 为三种平台标识之一。

## 结果与兼容性

运行的 `status` 描述执行状态，不能从节点在线状态推断任务通过。平台对照需同时看 `complete`、`passed` 和各目标结果；结束并不必然通过。

API 目前随预览版演进，尚无稳定版本兼容承诺。接入代码应保留错误响应并以当前 OpenAPI 为准。独立回执的 `schema_version` 当前为 `1`；它与控制台运行 ID 是不同的结果记录，不能直接写回数据库。

返回[文档目录](README.md)。
