import ctypes
import os
import sys
from ctypes import wintypes


def system_description():
    if os.name == "nt":
        version = sys.getwindowsversion()
        return f"Windows {'11' if version.build >= 22000 else '10'} ({version.major}.{version.minor}.{version.build})"
    import platform
    return platform.platform()


def desktop_available():
    """Probe the input desktop without switching it or unlocking the session."""
    if os.name != "nt":
        return False
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    handle = user32.OpenInputDesktop(0, False, 1)  # DESKTOP_READOBJECTS
    if not handle:
        return False
    try:
        name = ctypes.create_unicode_buffer(256)
        needed = wintypes.DWORD()
        valid = user32.GetUserObjectInformationW(handle, 2, name, ctypes.sizeof(name), ctypes.byref(needed))
        return bool(valid and name.value.casefold() == "default")
    finally:
        user32.CloseDesktop(handle)
