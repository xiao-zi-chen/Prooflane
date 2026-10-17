"""Reusable execution plans and narrowly scoped, credential-free handoff archives."""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS = {
    "windows": {
        "name": "Windows", "audience": "拥有 Windows 测试桌面的同事、客户 QA 或测试服务商",
        "environment": "Windows 10 / 11；Python 3.11+；保持桌面已登录、未锁屏。一个桌面同一时间执行一个 GUI 任务。",
        "formats": "EXE / MSI / ZIP", "validation": "Windows 样本已有实测证据；新应用、新系统版本仍需独立验收。",
        "install": "python -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt",
        "execute": ".\\.venv\\Scripts\\python.exe -m prooflane.handoff --manifest scenario.json --package \"应用文件路径\"",
        "pitfalls": ["未锁屏的交互桌面与管理员后台会话不同；看不到窗口时先检查会话。", "安装包要提供正确静默参数与安装后的完整程序路径。", "控件定位失败时回传 controls.json，并由应用方确认控件名称或 ID。"],
    },
    "macos": {
        "name": "macOS", "audience": "拥有 Mac 的同事、客户 QA、社区测试者或可提供完整桌面的服务商",
        "environment": "真实 Mac 或运行在 Apple 硬件上的 macOS 环境；Python 3.11+；实际用户桌面；辅助功能及屏幕录制权限。",
        "formats": "APP ZIP / DMG / PKG", "validation": "适配器与示例仍待对应系统实测；交付方案不等于已通过。",
        "install": "python3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install -r requirements-macos.txt",
        "execute": "python -m prooflane.handoff --manifest scenario.json --package \"应用文件路径\"",
        "pitfalls": ["先在图形桌面的终端授权辅助功能和屏幕录制，再重启终端 / Python。", "单独记录 Apple Silicon 或 Intel；一个架构通过不代表另一个架构通过。", "带 Framework 链接的 APP 优先交付 DMG；权限、签名或 Gatekeeper 拦截应记录原始提示。"],
    },
    "linux": {
        "name": "Linux", "audience": "拥有 Linux 桌面、Linux 虚拟机或专用测试服务器的执行者",
        "environment": "优先 Ubuntu 24.04；Python 3.11+；X11、D-Bus、AT-SPI 与 XComposite。可用专用 Xvfb；记录为虚拟显示，Wayland 暂不支持。",
        "formats": "AppImage / ZIP / tar.gz", "validation": "适配器与示例仍待对应系统实测；Xvfb 结果不代表 Wayland 或物理 GPU 覆盖。",
        "install": "sudo apt update\nsudo apt install python3-venv python3-gi gir1.2-atspi-2.0 gir1.2-gtk-3.0 at-spi2-core libatk-adaptor dbus-x11 xvfb xauth\npython3 -m venv --system-site-packages .venv\nsource .venv/bin/activate\npython -m pip install -r requirements-linux.txt",
        "execute": "python -m prooflane.handoff --manifest scenario.json --package \"应用文件路径\"",
        "pitfalls": ["无已登录 X11 桌面时使用文档中的 Xvfb 命令；不要把 Wayland 会话记为 X11 验证。", "AppImage 启动失败先检查 FUSE 与运行库；归类为环境阻塞，保留日志。", "记录发行版、架构、X11 / Xvfb / WSL2，不能用一台 Ubuntu 代表全部 Linux。"],
    },
}

RUNTIME_FILES = (
    "__init__.py", "handoff.py", "models.py", "storage.py", "runner.py", "execute.py",
    "native.py", "platforms.py", "environment.py", "desktop_macos.py", "desktop_linux.py",
)
DOC_FILES = ("execution-strategy.md", "handoff-acceptance.md", "issue-template.md")


def invitation(kind, run=None):
    plan = PLANS[kind]
    task = f"任务：{run['name']}\n构建：{run['package']['name']}\nSHA-256：{run['package']['sha256']}\n" if run else "应用方将另外提供本平台构建与 3–5 步验收场景。\n"
    return (f"希望邀请你协助完成一次 {plan['name']} 桌面验证。\n{task}"
            f"环境要求：{plan['environment']}\n"
            "我们提供执行方案、验收步骤和报告模板；执行者提供已有或自行安排的测试环境。\n"
            "请先确认系统 / 架构、可执行时段、预计成本，以及是否能安装依赖并采集应用窗口。费用由双方另行约定。\n"
            "推荐在本机独立运行交付包，无需连接我们的控制台或提供机器密码。\n"
            "请返回未经删改的证据 ZIP、填写后的回执与问题记录；环境受阻也请如实反馈。\n"
            "我们复核构建哈希、步骤和证据后确认结论；交付或执行者自报成功不自动计为平台通过。")


def instructions(kind, manifest, included):
    plan = PLANS[kind]
    concrete = manifest["spec"] is not None
    launch = plan["execute"]
    if included:
        launch = launch.replace('"应用文件路径"', json.dumps(manifest["package"]["file"], ensure_ascii=False))
    steps = "\n".join(f"{i+1}. {s['title']}（{s['action']}）" for i, s in enumerate((manifest["spec"] or {}).get("steps", [])))
    return f"""# {plan['name']} 执行交付包

我们提供策略与工具；执行者提供和管理测试环境；应用方提供构建；复核者确认结果。

## 先确认输入

{('这是已绑定任务的可执行包。' if concrete else '这是通用策略包，尚未绑定应用和场景。请让应用方在策略中心选定具体任务后导出可执行包。')}
{('应用构建位于 '+manifest['package']['file']+'。' if included else '此包未包含应用构建。已绑定任务时，请通过约定渠道取得同一 SHA-256 的原文件。')}
任务信息、目标架构和构建哈希见 scenario.json；不要修改验收期望来掩盖失败。

## 执行环境

{plan['environment']}
{plan['validation']}
在解压目录打开终端。应用安装和运行应使用执行者批准的专用测试环境。

## 独立执行（推荐）

{'包内包含运行工具；按下面的步骤准备依赖。' if concrete else '下列命令供收到可执行包后使用；通用策略包不包含运行工具。'}

```{'powershell' if kind == 'windows' else 'bash'}
{plan['install']}
```

{('macOS：在系统设置中给实际运行的终端 / Python 授予辅助功能与屏幕录制权限，然后重启终端并重新激活虚拟环境。' if kind == 'macos' else '')}
执行前预检（不会安装或启动应用）：

```text
{launch} --check
```

在目标系统运行一次：

```text
{launch}
```

{'Linux 无桌面服务器可以显式创建虚拟显示：' if kind == 'linux' else ''}
{('```bash'+chr(10)+'NO_AT_BRIDGE=0 GTK_MODULES=atk-bridge GDK_BACKEND=x11 xvfb-run -a -s "-screen 0 1280x900x24 +extension Composite -nolisten tcp" dbus-run-session -- '+launch+chr(10)+'```') if kind == 'linux' else ''}

## 本次验收步骤

{steps or '待应用方提供 3–5 个共同步骤，以及各平台的窗口名、控件定位和预期文本。'}

## 返回什么

执行器在 results/<执行编号>/ 下保存 receipt.json 和 evidence.zip；终端打印该目录。
失败和待复核也会保留证据。退出码 0 表示自动检查通过，2 表示待人工复核，1 表示执行失败或环境检查失败。
有结果目录时返回 receipt.json 与 evidence.zip，并填写 ISSUE_TEMPLATE.md；启动前被阻塞则返回实际错误文本与环境说明。
按 ACCEPTANCE.md 验收，执行者和复核者分别登记。复跑应使用相同构建与场景、重置后的测试环境；每次结果单独保存。
结果不会自动上传，也不会把控制台原来的等待任务改成通过。独立结果由复核者人工核验。

## 常见阻塞

{chr(10).join('- '+item for item in plan['pitfalls'])}

## 可选：长期在线节点

独立运行不需要节点凭据。长期接入由协调者单独提供服务地址和节点凭据，并安排私有连接；不要在本包内寻找共享密钥。
当前交付包面向单次独立执行；在线节点请由协调者提供完整项目并按原生节点接入说明配置。
"""


def build_kit(kind, run=None, package_path=None):
    if kind not in PLANS or (run and run["platform"] != kind):
        raise ValueError("任务平台与交付平台不一致")
    if package_path and not run:
        raise ValueError("请先选择具体任务，再包含应用构建")
    spec = dict(run["spec"]) if run else None
    if spec:
        spec.pop("package_id", None)
    package = {"name": run["package"]["name"], "sha256": run["package"]["sha256"],
               "file": "application/"+run["package"]["name"] if package_path else None} if run else None
    manifest = {"schema_version": 1, "platform": kind, "source_run_id": run["id"] if run else None,
                "spec": spec, "package": package, "result_policy": "independent_execution_requires_review"}
    if package_path:
        with Path(package_path).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != package["sha256"]:
                raise ValueError("应用构建哈希已变化，不能生成交付包")
    # Spool large builds to disk instead of allocating their full size in memory.
    output = tempfile.SpooledTemporaryFile(max_size=8*1024*1024)
    try:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("README.md", instructions(kind, manifest, bool(package_path)))
            archive.writestr("INVITATION.txt", invitation(kind, run))
            archive.writestr("scenario.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for source, target in zip(DOC_FILES, ("STRATEGY.md", "ACCEPTANCE.md", "ISSUE_TEMPLATE.md")):
                archive.write(ROOT / "docs" / source, target)
            if run:
                for name in RUNTIME_FILES:
                    archive.write(ROOT / "prooflane" / name, "prooflane/"+name)
                for name in ("requirements.txt", "requirements-macos.txt", "requirements-linux.txt"):
                    archive.write(ROOT / name, name)
            if package_path:
                archive.write(package_path, package["file"])
        output.seek(0)
        return output
    except BaseException:
        output.close()
        raise
