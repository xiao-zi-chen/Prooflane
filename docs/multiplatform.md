# 原生多平台节点接入

**简体中文** · [English](multiplatform.en.md)

## 控制台和节点的区别

本页用于执行者接入长期在线节点。单次协作优先使用 [策略交付流程](execution-strategy.md)：我们提供方案和工具，执行者在自己的机器上独立运行并交回证据，无需我们的控制台在线或分享节点凭据。

控制台保存各平台构建、共用验收场景、节点清单、租约和证据。节点运行在目标操作系统的交互桌面中，执行该系统的构建。Windows 包不会通过模拟被当作 macOS 测试，也不会将一个平台的结果自动复制给另一个平台。

当前可信操作员模式默认仅监听 localhost。可以在控制台所在机器直接使用网页；远程浏览器和节点通过 SSH 私有端口转发访问。同一控制台可同时连接不同系统的节点。每个交互桌面只启动一个节点；同一台机器不要同时启用本机节点和另一个远程节点抢占相同桌面。

## 1. 准备控制台

安装 `requirements.txt` 后启动：

```bash
python -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

纯控制台模式使用环境变量 `PROOFLANE_LOCAL_WORKER=0`。默认首启生成 `data/agent-token`，将其内容以可信方式复制到测试机的 `node.token`。若设置了 `PROOFLANE_AGENT_TOKEN`，使用该变量对应的注册凭据，文件内容不会自动同步。注册后节点使用独立凭据。完整说明见[配置说明](configuration.md)。

## 2. 准备目标机器

### Windows（已实测）

Python 3.11+，安装 `requirements.txt`。在已登录、未锁屏的桌面里启动。Windows UI Automation 用控件名称或 Automation ID 定位；截图和录像通过 PrintWindow 采集应用自身内容。已有 EXE、MSI、ZIP 样本运行证据。

### macOS（实验适配器，待实机验证）

在真实 Mac 或合法授权的 macOS 测试环境安装 Python 3.11+，然后：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-macos.txt
```

在系统设置中给实际启动节点的终端 / Python 进程授予辅助功能及屏幕录制权限，再重启节点。权限不足时不会显示为就绪。

- ZIP 应包含一个 `.app`，也可指定包内路径。ZIP 中的链接会被拒绝；带 Framework 链接的完整应用优先使用 DMG。
- DMG 只读挂载，复制其中唯一的 APP 到运行目录，再根据 Info.plist 中的主程序启动，结束后卸载。
- PKG 使用系统安装器，必须提供安装后的完整 APP / 可执行文件路径。不会自动提权、输入密码或关闭 Gatekeeper。需要额外授权的包会失败并返回安装日志。
- 控件名称来自 AXTitle / AXDescription，控件 ID 为 AXIdentifier，类型如 AXButton、AXTextField。点击使用 AXPress，输入使用 AXValue。
- 窗口采集按目标进程的窗口 ID 执行，需要屏幕录制权限。进程输出和匹配的 DiagnosticReports 会随报告返回。

这些 API 适配尚未在真实 Mac 验证；沙盒、应用签名、弹窗、LaunchServices 和特定 GUI 框架可能需要进一步调整。

### Linux（实验适配器，待实机验证）

需要 Python 3.11+、X11 会话、AT-SPI / PyGObject、D-Bus 和 XComposite。以下是 Debian / Ubuntu 的安装示例，需由测试机维护者执行：

```bash
sudo apt update
sudo apt install python3-venv python3-gi gir1.2-atspi-2.0 gir1.2-gtk-3.0 at-spi2-core libatk-adaptor dbus-x11 xvfb xauth
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-linux.txt
```

从已登录的 X11 桌面启动节点，保留 DISPLAY 和 DBUS_SESSION_BUS_ADDRESS。Wayland 不支持。也可由操作员准备专用 Xvfb / D-Bus 桌面，但这不等于操作系统或文件隔离。

- 接收 AppImage、ZIP、tar.gz；压缩包中请指定 Linux 主程序相对路径。
- tar.gz 和 ZIP 拒绝越界路径及链接；保留普通可执行权限，不恢复 setuid 等权限。
- 不调用 apt、dpkg 或 rpm 安装客户系统包。AppImage 依赖宿主机的 FUSE / 运行环境，缺失时会在进程日志中报错。
- 控件名称来自 AT-SPI name，控件 ID 为 accessible ID（应用需提供），类型为 role name。
- 采集使用 XComposite 的窗口 pixmap，不回退截取整个用户桌面。运行在 Wayland、自绘界面、无可访问性信息等情况下，不承诺兼容。
- 记录 stdout / stderr、退出码，以及可用时的 coredumpctl 信息；缺少崩溃采集能力会标明证据限制。

无现成桌面时，可以在准备好上述依赖后使用项目的 Xvfb 辅助脚本：

```bash
bash scripts/start-linux-x11.sh --server http://127.0.0.1:8765 --token-file node.token --name linux-xvfb
```

脚本创建独立 X11 / D-Bus 会话，使用用户目录中的虚拟环境和节点数据，不安装系统软件。此脚本目前仅有 Bash 语法检查，尚无 Linux GUI 运行记录。WSL2 / Xvfb 结果应按实际环境登记。

## 3. 连接控制台

如需私有转发，在目标机器另开终端：

```bash
ssh -N -L 8765:127.0.0.1:8765 user@controller-host
```

然后从目标机器的交互桌面运行节点：

```bash
python -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name my-native-node
```

不要通过 SSH 后台会话启动 GUI 节点；SSH 仅用于控制台连接。节点默认数据目录为 `agent-data/`，可用 `--data` 修改。不要把多个机器或控制台的同一个数据目录混用。`--once` 适合调试，只处理一次领取尝试 / 任务。

注册、平台匹配、下载、运行、回传都需要有效凭据。租约每次续期 45 秒，节点心跳保持下载和回传阶段的租约。断开超过时限的任务标记“已中断”，不会自动重装。节点保存本地证据，过期结果不会覆盖控制台的新状态。节点退出后再次启动会注册新的节点标识，旧标识显示离线。

## 4. 共用场景并覆盖平台差异

在 Windows 控制台的“测试概览”点击“创建示例任务”，可提交三平台 Notes 示例。Windows 包是编译后的 WinForms EXE；macOS APP ZIP 内含使用 PyObjC AppKit 的 Python 主程序；Linux ZIP 内含使用 GTK 3 的 Python 主程序。后两者以 `#!/usr/bin/env python3` 启动，必须先激活上述节点虚拟环境再运行 agent。Linux 的 GTK 3 依赖由 `gir1.2-gtk-3.0` 提供。当前后两种示例尚无对应系统的运行验证结果。

默认四步为启动窗口、输入笔记、保存、检查提示。Linux 使用 AT-SPI 控件名称，Windows / macOS 使用控件 ID。没有就绪节点的目标保留等待状态；新增远程节点会自动领取匹配任务。截图对照、录像和报告只显示实际回传的证据。对照页选择任一步骤即可同时查看该步骤在各平台的结果。

在提交页的额外平台卡片中填写窗口标题及路径。若第 2 步在 Windows 使用 `automation_id=saveButton`，而 macOS 使用标题 `Save`，可填写：

```json
{"2": {"automation_id": "", "target": "Save", "control_type": "AXButton"}}
```

允许覆盖字段为 target、automation_id、control_type、value、timeout。序号从 1 开始；步骤名称和动作保持一致。平台对照页不会把“等待节点”“跳过”“待复核”算作成功。

## 真实验证的边界

- 控制台与独立 Windows 节点的完整 HTTP 交互已经实际执行 GUI 验证；这是一台物理 Windows 上的两个独立进程，不是跨网络、跨操作系统的证明。
- 平台 / 架构筛选、认证、竞争领取、租约过期和对照逻辑有自动化测试。
- macOS / Linux 目前只有实现与静态 / 协议验证，没有对应实机执行结果。
- 未实现 Android / iOS、虚拟机编排、快照恢复、多租户隔离或公网账户系统。
- 不应将客户提供的未知程序直接运行在有私人数据的日常主机。测试服务仍需原生系统的专用、可还原环境。
