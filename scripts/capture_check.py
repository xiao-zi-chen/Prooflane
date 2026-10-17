"""Regression: unrelated foreground windows must never enter app evidence."""
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import win32gui
from PIL import ImageChops
from pywinauto import Application

from prooflane.runner import capture_window


def main():
    root_path = Path(__file__).resolve().parent.parent
    process = subprocess.Popen([str(root_path / "data/demo/ProoflaneNotes.exe")])
    overlay = None
    try:
        app = Application(backend="uia").connect(process=process.pid, timeout=10)
        window = app.window(title="Prooflane Notes")
        window.wait("visible", timeout=10)
        handle = window.wrapper_object().handle
        baseline = capture_window(handle)
        x, y = win32gui.ClientToScreen(handle, (0, 0))
        overlay = tk.Tk()
        overlay.overrideredirect(True)
        overlay.configure(background="#ff00ff")
        overlay.geometry(f"{baseline.width}x{baseline.height}+{x}+{y}")
        overlay.attributes("-topmost", True)
        overlay.update()
        time.sleep(.2)
        obscured = capture_window(handle)
        magenta = sum(1 for r, g, b in obscured.getdata() if r > 240 and g < 15 and b > 240)
        assert magenta == 0, f"Foreground overlay leaked into screenshot: {magenta} pixels"
        difference = ImageChops.difference(baseline, obscured)
        changed = sum(1 for p in difference.getdata() if max(p) > 16) / (baseline.width * baseline.height)
        assert changed < .03, f"Application evidence changed by {changed:.1%} under occlusion"
        (root_path / "artifacts").mkdir(exist_ok=True)
        obscured.save(root_path / "artifacts/capture-occlusion.png")
        print(f"Occlusion regression passed: zero overlay pixels; changed application pixels {changed:.3%}.")
    finally:
        if overlay:
            overlay.destroy()
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
