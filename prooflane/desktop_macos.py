"""macOS accessibility and window capture adapter; requires real Mac validation."""
import subprocess
import tempfile
from pathlib import Path


class MacDesktop:
    def __init__(self, pid, title):
        import ApplicationServices as AX
        import Quartz
        self.AX, self.Quartz = AX, Quartz
        self.pid, self.title = pid, title
        self.handle = None

    def attr(self, element, name):
        error, value = self.AX.AXUIElementCopyAttributeValue(element, name, None)
        return value if error == 0 else None

    def find(self):
        app = self.AX.AXUIElementCreateApplication(self.pid)
        candidates = [w for w in self.attr(app, "AXWindows") or [] if self.attr(w, "AXTitle") == self.title]
        if len(candidates) != 1:
            raise LookupError("未找到唯一的 macOS 主窗口")
        self.root = candidates[0]
        q = self.Quartz
        windows = q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionOnScreenOnly, q.kCGNullWindowID)
        matches = [w for w in windows if w.get(q.kCGWindowOwnerPID) == self.pid and w.get(q.kCGWindowName) == self.title]
        if len(matches) != 1:
            raise LookupError("未找到唯一的可采集窗口；检查屏幕录制权限")
        self.handle = int(matches[0][q.kCGWindowNumber])
        return self

    def set_focus(self):
        self.AX.AXUIElementPerformAction(self.root, "AXRaise")

    def walk(self):
        result, pending = [], [(self.root, 0)]
        while pending and len(result) < 500:
            item, depth = pending.pop(0)
            result.append(item)
            if depth < 15:
                pending.extend((child, depth+1) for child in self.attr(item, "AXChildren") or [])
        return result

    def info(self, item):
        return {"name": str(self.attr(item, "AXTitle") or self.attr(item, "AXDescription") or ""),
                "automation_id": str(self.attr(item, "AXIdentifier") or ""), "control_type": str(self.attr(item, "AXRole") or "")}

    def control(self, step):
        matches = []
        for item in self.walk():
            info = self.info(item)
            if all(not step[key] or step[key] == info[field] for key, field in (("target", "name"), ("automation_id", "automation_id"), ("control_type", "control_type"))):
                matches.append(item)
        if len(matches) != 1:
            raise LookupError(f"控件需要唯一匹配，当前匹配 {len(matches)} 个")
        return matches[0]

    def click(self, step):
        if self.AX.AXUIElementPerformAction(self.control(step), "AXPress") != 0:
            raise RuntimeError("控件不支持 AXPress")

    def type_text(self, step):
        if self.AX.AXUIElementSetAttributeValue(self.control(step), "AXValue", step["value"]) != 0:
            raise RuntimeError("控件不能设置文本")

    def texts(self, step):
        items = [self.control(step)] if step["target"] or step["automation_id"] else self.walk()
        return [str(self.attr(item, key) or "") for item in items for key in ("AXTitle", "AXDescription", "AXValue")]

    def capture(self):
        from PIL import Image
        if not self.handle:
            raise RuntimeError("没有应用窗口句柄")
        with tempfile.TemporaryDirectory(prefix="prooflane-window-") as temporary:
            path = Path(temporary) / "window.png"
            result = subprocess.run(["/usr/sbin/screencapture", "-x", "-o", "-l", str(self.handle), str(path)], capture_output=True, timeout=10)
            if result.returncode or not path.exists():
                raise RuntimeError("macOS 窗口采集失败；检查屏幕录制权限")
            with Image.open(path) as image:
                return image.convert("RGB").copy()
