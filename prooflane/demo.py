"""Package actual native samples; packaging is not an execution result."""
import hashlib
import plistlib
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def native_demo_package(store, kind):
    if kind not in {"macos", "linux"}:
        raise ValueError("Unsupported native sample")
    identifier = uuid.uuid4().hex
    name = f"ProoflaneNotes-{kind}.zip"
    path = store.root / "packages" / f"{identifier}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "demo" / f"notes_{kind}.py").read_bytes()
    executable = "ProoflaneNotes.app/Contents/MacOS/ProoflaneNotes" if kind == "macos" else "ProoflaneNotes"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        entry = zipfile.ZipInfo(executable)
        entry.create_system = 3
        entry.external_attr = 0o100755 << 16
        archive.writestr(entry, source)
        if kind == "macos":
            archive.writestr("ProoflaneNotes.app/Contents/Info.plist", plistlib.dumps({
                "CFBundleExecutable": "ProoflaneNotes", "CFBundleName": "Prooflane Notes",
                "CFBundleIdentifier": "local.prooflane.notes", "CFBundlePackageType": "APPL",
                "CFBundleVersion": "1.0", "NSHighResolutionCapable": True,
            }))
        archive.writestr("README.txt", "Native source sample. Activate the node Python environment before starting the agent. "
                          + ("Requires PyObjC AppKit." if kind == "macos" else "Requires PyGObject and GTK 3.")
                          + " This package has not yet been validated on its target OS.")
    package = {"id": identifier, "name": name, "size": path.stat().st_size,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "path": str(path), "demo": True}
    store.put_package(package)
    return package
