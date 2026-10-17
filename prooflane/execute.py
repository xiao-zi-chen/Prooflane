"""Disposable execution process, supervised and job-contained by Worker."""
import sys
import importlib
import threading
from pathlib import Path

from .runner import Execution
from .storage import Store


def main():
    if sys.platform != "win32":
        from .native import NativeExecution
        NativeExecution(Store(Path(sys.argv[1])), sys.argv[2], threading.Event()).run()
        return
    # comtypes may create its generated-module package on the first import.
    # Invalidate Python's directory cache before retrying that cold-start import.
    try:
        import comtypes.client
    except ImportError:
        importlib.invalidate_caches()
        import comtypes.client
    import pythoncom
    pythoncom.CoInitialize()
    try:
        Execution(Store(Path(sys.argv[1])), sys.argv[2], threading.Event()).run()
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main()
