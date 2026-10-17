"""Native macOS/Linux execution using the same lifecycle and evidence schema."""
import hashlib
import json
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import tarfile
import time
from pathlib import Path

from .platforms import capability, current_platform, current_architecture, package_suffix
from .runner import Execution, Recorder, Cancelled, extract_package


def extract_tar(source, destination):
    with tarfile.open(source, "r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 1024**3:
            raise ValueError("解压后超过文件数量或大小限制")
        names = set()
        for member in members:
            target = (destination / member.name).resolve()
            if not (member.isfile() or member.isdir()) or not target.is_relative_to(destination.resolve()):
                raise ValueError("压缩包包含越界路径、链接或特殊设备")
            if str(target) in names:
                raise ValueError("压缩包包含重复路径")
            names.add(str(target))
        for member in members:
            target = destination / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as src, target.open("wb") as output:
                    shutil.copyfileobj(src, output)
                target.chmod(member.mode & 0o777)


class NativeExecution(Execution):
    def preflight(self):
        if self.spec["platform"] != current_platform() or self.spec["architecture"] not in ("any", current_architecture()):
            raise RuntimeError("任务平台或架构与实际节点不匹配")
        capabilities = capability()
        if not capabilities["ready"]:
            raise RuntimeError(capabilities["detail"])
        self.mount = None

    def environment(self):
        return {**super().environment(), "adapter": "macOS Accessibility" if current_platform() == "macos" else "Linux AT-SPI / X11",
                "adapter_validation": "实验阶段，需在目标系统验证兼容性"}

    def prepare(self):
        package = self.store.package(self.spec["package_id"])
        source = Path(package["path"])
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != package["sha256"]:
                raise ValueError("安装包 SHA-256 校验失败")
        self.log(f"Package verified: {package['name']} sha256={package['sha256']}")
        suffix = package_suffix(package["name"])
        target = self.directory / "app"
        target.mkdir()
        if suffix == ".pkg":
            self.store.update(self.id, status="installing")
            process = self.spawn(["/usr/sbin/installer", "-pkg", str(source), "-target", "/", *self.spec["install_args"]], "installer")
            code = self.wait_process(process, 300)
            if code:
                raise RuntimeError(f"PKG 安装失败（{code}），不会自动提权；详见 installer.log")
            executable = Path(os.path.expandvars(self.spec["app_path"])).expanduser()
            if not executable.is_absolute():
                raise ValueError("安装后的应用路径必须是绝对路径")
        else:
            if suffix == ".zip":
                extract_package(source, target)
            elif suffix == ".tar.gz":
                extract_tar(source, target)
            elif suffix == ".dmg":
                self.mount = self.directory / "mount"
                self.mount.mkdir()
                attach = self.spawn(["/usr/bin/hdiutil", "attach", str(source), "-readonly", "-nobrowse", "-mountpoint", str(self.mount)], "mount")
                if self.wait_process(attach, 60):
                    raise RuntimeError("DMG 挂载失败")
                apps = list(self.mount.glob("*.app"))
                if len(apps) != 1:
                    raise ValueError("DMG 根目录需要包含一个 APP")
                shutil.copytree(apps[0], target / apps[0].name, symlinks=True)
            elif suffix == ".appimage":
                shutil.copy2(source, target / package["name"])
            else:
                raise ValueError("目标平台不支持此安装包")
            if self.spec["app_path"]:
                executable = (target / self.spec["app_path"]).resolve()
                if not executable.is_relative_to(target.resolve()):
                    raise ValueError("应用路径必须位于解压目录")
            else:
                candidates = list(target.rglob("*.app")) if current_platform() == "macos" else list(target.glob("*.AppImage")) + list(target.glob("*.appimage"))
                if len(candidates) != 1:
                    raise ValueError("请填写包内主程序相对路径")
                executable = candidates[0]
        if current_platform() == "macos" and executable.suffix == ".app":
            bundle = executable.resolve()
            with (bundle / "Contents/Info.plist").open("rb") as stream:
                name = plistlib.load(stream)["CFBundleExecutable"]
            executable = (bundle / "Contents/MacOS" / name).resolve()
            if not executable.is_relative_to(bundle):
                raise ValueError("APP 主程序路径越界")
        if not executable.is_file():
            raise ValueError(f"找不到主程序：{executable}")
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
        self.executable = executable
        self.process = self.spawn([str(executable), *self.spec["app_args"]], "application", str(executable.parent))
        if current_platform() == "macos":
            from .desktop_macos import MacDesktop
            self.driver = MacDesktop(self.process.pid, self.spec["window_title"])
        else:
            from .desktop_linux import LinuxDesktop
            self.driver = LinuxDesktop(self.process.pid, self.spec["window_title"])
        self.log(f"Launched native process pid={self.process.pid}")

    def find_window(self, timeout):
        deadline, last = time.monotonic()+timeout, ""
        while time.monotonic() < deadline:
            self.check()
            if self.process.poll() is not None:
                raise RuntimeError(f"应用在窗口出现前退出：{self.process.returncode}")
            try:
                return self.driver.find()
            except Exception as exc:
                last = str(exc)
            time.sleep(.3)
        raise TimeoutError(f"未找到应用窗口：{last}")

    def perform(self, step):
        deadline, last = time.monotonic()+step["timeout"], ""
        while time.monotonic() < deadline:
            self.check()
            try:
                action = step["action"]
                if action == "wait_window":
                    self.driver.find()
                elif action == "click":
                    self.driver.click(step)
                elif action == "type_text":
                    self.driver.type_text(step)
                elif action == "assert_text":
                    if not any(step["value"] in text for text in self.driver.texts(step)):
                        raise LookupError(f"未找到预期文本：{step['value']}")
                elif action == "screenshot":
                    return "界面已留证，等待人工复核"
                return "目标系统原生操作已完成" if action != "assert_text" else f"界面包含：{step['value']}"
            except Exception as exc:
                last = str(exc)
            time.sleep(.25)
        raise TimeoutError(f"步骤超时：{last}")

    def capture(self):
        image = self.driver.capture().convert("RGB")
        if image.width < 20 or image.height < 20 or all(high == 0 for low, high in image.getextrema()):
            raise RuntimeError("未获得有效的应用窗口画面")
        return image

    def screenshot(self, index):
        name = f"step-{index+1:02d}.png"
        self.capture().save(self.directory / name)
        return name

    def make_recorder(self):
        return Recorder(self.window.handle, self.directory, self.capture)

    def control_tree(self):
        try:
            controls = [self.driver.info(item) for item in self.driver.walk()]
            (self.directory / "controls.json").write_text(json.dumps(controls, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            self.log(f"Control tree unavailable: {exc}")

    def crash_logs(self):
        report = {"source": "process stderr / exit code", "exit_code": self.process.poll() if self.process else None,
                  "native_crash_reports": [], "note": "无日志不表示没有崩溃；未启用自动转储。"}
        try:
            if current_platform() == "macos" and self.executable:
                root = Path.home() / "Library/Logs/DiagnosticReports"
                reports = sorted(root.glob(self.executable.name+"*"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
                for i, path in enumerate(reports):
                    if path.is_file() and path.stat().st_mtime >= self.wall_start and path.stat().st_size < 2*1024*1024:
                        filename = f"crash-{i:02d}.log"
                        shutil.copyfile(path, self.directory / filename)
                        report["native_crash_reports"].append(filename)
            elif current_platform() == "linux" and self.process:
                if shutil.which("coredumpctl"):
                    result = subprocess.run(["coredumpctl", "--no-pager", f"--since=@{int(self.wall_start)}", "info", str(self.process.pid)], capture_output=True, timeout=10)
                    (self.directory / "coredump.log").write_bytes(result.stdout + result.stderr)
                else:
                    self.warning("节点没有 coredumpctl，仅采集应用输出和退出码，崩溃转储不可用")
        except Exception as exc:
            report["collection_error"] = str(exc)
            self.warning(f"系统崩溃日志采集不完整：{exc}")
        (self.directory / "crash-events.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def cleanup(self):
        super().cleanup()
        if getattr(self, "mount", None):
            result = subprocess.run(["/usr/bin/hdiutil", "detach", str(self.mount)], capture_output=True, timeout=20)
            if result.returncode:
                self.warning("DMG 卸载失败，需要操作员检查挂载状态")
