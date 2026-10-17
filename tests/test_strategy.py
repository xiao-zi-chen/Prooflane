import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from prooflane.app import create_app
from prooflane.handoff import execute
from prooflane.models import DEMO_STEPS

HEADERS = {"X-Prooflane-Client": "web"}


@pytest.fixture
def hub(tmp_path):
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        yield client


def create_task(hub, kind="linux"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("app", "protocol fixture; not an application")
    package = hub.post("/api/packages", headers=HEADERS, files={"file": ("app.zip", stream.getvalue())}).json()
    response = hub.post("/api/runs", headers=HEADERS, json={"name": "delegated task", "platform": kind,
        "package_id": package["id"], "window_title": "Notes", "steps": DEMO_STEPS[:4], "app_path": "app"})
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("kind", ["windows", "macos", "linux"])
def test_generic_strategy_is_shareable_without_local_machine_data(hub, kind):
    response = hub.get(f"/api/strategies/{kind}/kit")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"README.md", "INVITATION.txt", "scenario.json", "STRATEGY.md", "ACCEPTANCE.md", "ISSUE_TEMPLATE.md"}
        manifest = json.loads(archive.read("scenario.json"))
        assert manifest["platform"] == kind and manifest["spec"] is None
        data = b"\n".join(archive.read(name) for name in archive.namelist())
        secret = (hub.app.state.store.root / "agent-token").read_bytes()
        assert secret not in data
        assert b"test-machines.md" not in data
    assert hub.get("/api/runs").json() == []


def test_bound_kit_uses_original_scenario_and_only_includes_build_when_selected(hub):
    run = create_task(hub)
    original = hub.get("/api/runs/"+run["id"]).json()
    for include in (False, True):
        response = hub.get("/api/strategies/linux/kit", params={"run_id": run["id"], "include_package": include})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            manifest = json.loads(archive.read("scenario.json"))
            assert manifest["source_run_id"] == run["id"]
            assert manifest["spec"]["steps"] == run["spec"]["steps"]
            assert "package_id" not in manifest["spec"]
            assert "prooflane/handoff.py" in archive.namelist()
            assert not any(name.startswith(("data/", "agent-data/", "artifacts/")) for name in archive.namelist())
            assert ("application/app.zip" in archive.namelist()) is include
            if include:
                assert hashlib.sha256(archive.read(manifest["package"]["file"])).hexdigest() == run["package"]["sha256"]
    assert hub.get("/api/runs/"+run["id"]).json() == original
    assert len(hub.get("/api/runs").json()) == 1


def test_handoff_rejects_wrong_platform_missing_task_and_mutated_package(hub):
    run = create_task(hub)
    assert hub.get("/api/strategies/android/kit").status_code == 422
    assert hub.get("/api/strategies/macos/kit", params={"run_id": run["id"]}).status_code == 422
    assert hub.get("/api/strategies/linux/kit", params={"run_id": "f"*32}).status_code == 404
    assert hub.get("/api/strategies/linux/kit?include_package=true").status_code == 422
    package = hub.app.state.store.package(run["spec"]["package_id"])
    Path(package["path"]).write_bytes(b"changed")
    assert hub.get("/api/strategies/linux/kit", params={"run_id": run["id"], "include_package": True}).status_code == 422


def test_preflight_never_launches_mismatched_platform_or_hash(hub, tmp_path, monkeypatch):
    run = create_task(hub)
    response = hub.get("/api/strategies/linux/kit", params={"run_id": run["id"], "include_package": True})
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(tmp_path / "kit")
    manifest, package = tmp_path / "kit/scenario.json", tmp_path / "kit/application/app.zip"
    output = tmp_path / "results"
    monkeypatch.setattr("prooflane.handoff.current_platform", lambda: "macos")
    with pytest.raises(ValueError, match="目标操作系统"):
        execute(manifest, package, output, check=True)
    monkeypatch.setattr("prooflane.handoff.current_platform", lambda: "linux")
    package.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        execute(manifest, package, output, check=True)
    assert not output.exists()
