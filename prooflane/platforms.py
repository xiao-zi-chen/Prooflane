"""Platform capabilities and strict package routing; capability is not proof of validation."""
import importlib.util
import os
import platform
import sys
from pathlib import Path

LABELS = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}
FORMATS = {"windows": (".exe", ".msi", ".zip"), "macos": (".zip", ".dmg", ".pkg"), "linux": (".appimage", ".zip", ".tar.gz")}


def current_platform():
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux" if sys.platform.startswith("linux") else "unknown")


def current_architecture():
    return "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"


def package_suffix(name):
    return ".tar.gz" if name.lower().endswith(".tar.gz") else Path(name).suffix.lower()


def validate_package(spec, package):
    suffix = package_suffix(package["name"])
    if suffix not in FORMATS[spec.platform]:
        raise ValueError(f"{LABELS[spec.platform]} 不支持此包格式：{suffix}")
    if spec.platform == "windows":
        if spec.mode == "installer" and suffix == ".zip":
            raise ValueError("ZIP 请使用便携程序模式")
        if spec.mode == "portable" and suffix == ".msi":
            raise ValueError("MSI 请使用安装模式")
    elif spec.platform == "macos":
        if (suffix == ".pkg") != (spec.mode == "installer"):
            raise ValueError("macOS PKG 使用安装模式；APP ZIP 和 DMG 使用便携模式")
    elif spec.mode != "portable":
        raise ValueError("Linux 节点当前接收便携 AppImage、ZIP 或 tar.gz，不执行系统包管理器")


def capability():
    kind = current_platform()
    ready, detail = False, "当前系统没有桌面执行适配器"
    if kind == "windows":
        from .environment import desktop_available
        ready = importlib.util.find_spec("pywinauto") is not None and desktop_available()
        detail = "Windows UI Automation / PrintWindow" if ready else "需要依赖完整且未锁屏的 Windows 桌面"
    elif kind == "macos":
        try:
            import ApplicationServices as AX
            import Quartz
            ready = bool(AX.AXIsProcessTrusted() and Quartz.CGPreflightScreenCaptureAccess())
            detail = "macOS Accessibility / Window Capture（待实机验证）" if ready else "需要辅助功能与屏幕录制权限"
        except ImportError:
            detail = "请安装 requirements-macos.txt"
    elif kind == "linux":
        try:
            import gi
            gi.require_version("Atspi", "2.0")
            from gi.repository import Atspi
            from Xlib import display
            Atspi.init()
            connection = display.Display()
            ready = bool(connection.has_extension("Composite") and os.environ.get("DBUS_SESSION_BUS_ADDRESS"))
            connection.close()
            detail = "AT-SPI / X11 Composite（待实机验证）" if ready else "需要 X11 Composite 与桌面 D-Bus 会话"
        except Exception as exc:
            detail = f"需要 AT-SPI、python-xlib 和 X11 会话：{type(exc).__name__}"
    return {"id": "local", "name": "本机执行节点", "platform": kind, "architecture": current_architecture(),
            "ready": ready, "detail": detail, "online": True, "local": True}
