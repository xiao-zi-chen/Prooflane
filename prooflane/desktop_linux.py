"""AT-SPI and XComposite adapter. Wayland and nonaccessible UIs are not claimed."""
import threading


class LinuxDesktop:
    def __init__(self, pid, title):
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
        self.Atspi = Atspi
        Atspi.init()
        self.pid, self.title = pid, title
        self.handle = None
        self.lock = threading.Lock()

    @staticmethod
    def children(item):
        return [item.get_child_at_index(i) for i in range(item.get_child_count())]

    def find(self):
        from Xlib import display
        root = self.Atspi.get_desktop(0)
        apps = [item for item in self.children(root) if item.get_process_id() == self.pid]
        windows = [w for app in apps for w in self.children(app) if w.get_name() == self.title]
        if len(windows) != 1:
            raise LookupError("未找到唯一的 AT-SPI 窗口；应用需提供可访问性接口")
        self.root = windows[0]
        connection = display.Display()
        try:
            root = connection.screen().root
            prop = root.get_full_property(connection.intern_atom("_NET_CLIENT_LIST"), 0)
            candidates = [connection.create_resource_object("window", int(i)) for i in prop.value] if prop else root.query_tree().children
            matches = []
            for window in candidates:
                process = window.get_full_property(connection.intern_atom("_NET_WM_PID"), 0)
                name = window.get_full_property(connection.intern_atom("_NET_WM_NAME"), 0)
                title = name.value.decode("utf-8", errors="replace") if name else window.get_wm_name()
                if process and int(process.value[0]) == self.pid and title == self.title:
                    matches.append(window.id)
            if len(matches) != 1:
                raise LookupError("未找到属于目标进程的唯一 X11 窗口")
            self.handle = matches[0]
        finally:
            connection.close()
        return self

    def set_focus(self):
        # Actions use accessibility methods and do not move the host mouse.
        pass

    def walk(self):
        result, pending = [], [(self.root, 0)]
        while pending and len(result) < 500:
            item, depth = pending.pop(0)
            result.append(item)
            if depth < 15:
                pending.extend((child, depth+1) for child in self.children(item))
        return result

    def info(self, item):
        identifier = ""
        try:
            identifier = item.get_accessible_id() or ""
        except AttributeError:
            pass
        return {"name": item.get_name() or "", "automation_id": identifier, "control_type": item.get_role_name() or ""}

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
        action = self.control(step).get_action_iface()
        count = action.get_n_actions() if action else 0
        indices = [i for i in range(count) if action.get_action_name(i).lower() in ("click", "press", "activate")]
        if len(indices) != 1 or not action.do_action(indices[0]):
            raise RuntimeError("控件没有唯一可执行的点击动作")

    def type_text(self, step):
        editable = self.control(step).get_editable_text_iface()
        if not editable or not editable.set_text_contents(step["value"]):
            raise RuntimeError("控件不支持可访问性文本输入")

    def texts(self, step):
        items = [self.control(step)] if step["target"] or step["automation_id"] else self.walk()
        values = []
        for item in items:
            values.append(item.get_name() or "")
            text = item.get_text_iface()
            if text:
                values.append(text.get_text(0, -1))
        return values

    def capture(self):
        from PIL import Image
        from Xlib import X, display
        from Xlib.ext import composite
        with self.lock:
            connection = display.Display()
            pixmap, redirected = None, False
            window = connection.create_resource_object("window", self.handle)
            try:
                # A named Composite pixmap contains this window even when obscured.
                # Never fall back to grabbing root/desktop pixels.
                try:
                    pixmap = window.composite_name_window_pixmap()
                    connection.sync()
                    geometry = pixmap.get_geometry()
                except Exception:
                    window.composite_redirect_window(composite.RedirectAutomatic)
                    connection.sync()
                    redirected = True
                    pixmap = window.composite_name_window_pixmap()
                    geometry = pixmap.get_geometry()
                raw = pixmap.get_image(0, 0, geometry.width, geometry.height, X.ZPixmap, 0xFFFFFFFF)
                if len(raw.data) != geometry.width * geometry.height * 4:
                    raise RuntimeError("当前 X11 像素格式暂不支持")
                return Image.frombytes("RGB", (geometry.width, geometry.height), raw.data, "raw", "BGRX", 0, 1)
            finally:
                if pixmap:
                    pixmap.free()
                if redirected:
                    window.composite_unredirect_window(composite.RedirectAutomatic)
                connection.close()
