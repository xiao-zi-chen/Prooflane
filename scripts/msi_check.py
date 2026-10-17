"""Build, exercise, and uninstall an owned per-user MSI fixture (Python 3.11/3.12).

The fixture's payload directory is inside this workspace. It uses a fresh product
GUID and is removed by Windows Installer in the finally block.
"""
import json
import subprocess
import uuid
from pathlib import Path

import msilib
from msilib import schema, sequence

from e2e_windows import CLIENT, ROOT, check_evidence, post, wait


def main():
    fixture = ROOT / "data/msi-fixture" / uuid.uuid4().hex
    fixture.mkdir(parents=True)
    destination = fixture / "installed"
    path = fixture / "ProoflaneFixture.msi"
    product = msilib.gen_uuid()
    db = msilib.init_database(str(path), schema, "Prooflane Owned Test Fixture", product, "0.1.0", "Prooflane")
    msilib.add_tables(db, sequence)
    msilib.add_data(db, "Property", [("ARPSYSTEMCOMPONENT", "1"), ("REBOOT", "ReallySuppress")])
    cab = msilib.CAB("payload.cab")
    feature = msilib.Feature(db, "Main", "Notes fixture", "Owned verification fixture", 1)
    directory = msilib.Directory(db, cab, None, str(ROOT / "data/demo"), "TARGETDIR", "SourceDir")
    application = msilib.Directory(db, cab, directory, ".", "INSTALLDIR", "Notes")
    application.start_component("NotesComponent", feature, 0, keyfile="ProoflaneNotes.exe")
    application.add_file("ProoflaneNotes.exe")
    cab.commit(db)
    db.Commit()
    del db
    try:
        with path.open("rb") as source:
            package = post("/api/packages", files={"file": (path.name, source, "application/octet-stream")})
        spec = json.loads((ROOT / "examples/run-spec.json").read_text(encoding="utf-8"))
        spec.update(name="回归验证 · 真实 MSI 静默安装", package_id=package["id"], mode="installer",
                    install_args=["/qn", f"INSTALLDIR={destination}"], app_path=str(destination / "ProoflaneNotes.exe"),
                    steps=spec["steps"][:4])
        run = wait(post("/api/runs", json=spec)["id"], timeout=100)
        assert run["status"] == "passed", run
        assert "msi.log" in run["artifacts"]
        check_evidence(run, 4)
        output = {"run_id": run["id"], "status": run["status"], "product_code": product}
        (ROOT / "artifacts/msi-result.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output, indent=2))
    finally:
        result = subprocess.run(["msiexec.exe", "/x", product, "/qn", "/norestart"],
                                timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode in (0, 1605), f"Fixture uninstall failed: {result.returncode}"
        assert not (destination / "ProoflaneNotes.exe").exists(), "Fixture payload was not removed"
        print("Owned MSI fixture uninstalled.")


if __name__ == "__main__":
    main()
