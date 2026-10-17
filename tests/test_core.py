import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from prooflane.app import create_app
from prooflane.models import DEMO_STEPS, RunSpec
from prooflane.runner import extract_package, write_reports
from prooflane.storage import Store


def spec(package_id="a" * 32):
    return RunSpec(name="真实测试", package_id=package_id, window_title="Notes", steps=DEMO_STEPS).model_dump()


def package(store):
    value = {"id": "a" * 32, "name": "notes.exe", "size": 10, "sha256": "b" * 64, "path": "not-exposed.exe"}
    store.put_package(value)
    return value


@pytest.mark.parametrize("entry", ["../escape.exe", "..\\escape.exe", "C:/escape.exe", "/escape.exe", "app.exe:secret", "CON", "folder./app.exe"])
def test_zip_rejects_windows_path_escapes_before_writing(tmp_path, entry):
    source = tmp_path / "package.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("valid.txt", "first")
        archive.writestr(entry, "malicious")
    destination = tmp_path / "unpacked"
    destination.mkdir()
    with pytest.raises(ValueError):
        extract_package(source, destination)
    assert not list(destination.iterdir())


def test_zip_preserves_valid_nested_application(tmp_path):
    source = tmp_path / "package.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("app/notes.exe", b"MZexample")
        archive.writestr("app/data/readme.txt", "resource")
    extract_package(source, tmp_path / "unpacked")
    assert (tmp_path / "unpacked/app/data/readme.txt").read_text() == "resource"


def test_schema_rejects_ambiguous_actions_and_missing_install_configuration():
    value = spec()
    value["steps"][1].update(automation_id="", target="")
    with pytest.raises(ValidationError):
        RunSpec.model_validate(value)
    value = spec()
    value["mode"] = "installer"
    with pytest.raises(ValidationError):
        RunSpec.model_validate(value)
    value = spec()
    value["steps"] = value["steps"][:2]
    with pytest.raises(ValidationError):
        RunSpec.model_validate(value)


def test_recovery_does_not_reexecute_packages(tmp_path):
    store = Store(tmp_path)
    run = store.create(spec(), package(store))
    store.update(run["id"], status="running")
    store.recover()
    result = store.get(run["id"])
    assert result["status"] == "interrupted"
    assert all(s["status"] == "skipped" for s in result["steps"])
    assert result["error"]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        yield client


def test_local_api_rejects_cross_origin_execution(client):
    assert client.post("/api/demo").status_code == 403
    assert client.post("/api/demo", headers={"X-Prooflane-Client": "web", "Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_upload_validation_and_checksum(client):
    headers = {"X-Prooflane-Client": "web"}
    for name, body in [("payload.ps1", b"command"), ("fake.exe", b"not-executable"), ("empty.zip", b""), ("CON.exe", b"MZexample")]:
        assert client.post("/api/packages", headers=headers, files={"file": (name, body)}).status_code == 422
    result = client.post("/api/packages", headers=headers, files={"file": ("notes.exe", b"MZexample")})
    assert result.status_code == 201
    assert len(result.json()["sha256"]) == 64
    assert "path" not in result.json()
    stored = client.app.state.store.package(result.json()["id"])
    assert Path(stored["path"]).name == "notes.exe"


def test_cancel_retry_and_manual_review_report(client):
    store = client.app.state.store
    run = store.create(spec(), package(store))
    identifier = run["id"]
    headers = {"X-Prooflane-Client": "web"}
    assert client.post(f"/api/runs/{identifier}/retry", headers=headers).status_code == 409
    assert client.post(f"/api/runs/{identifier}/cancel", headers=headers).json()["cancel_requested"] is True
    def complete(run):
        for step in run["steps"]:
            step["status"] = "review" if step["action"] == "screenshot" else "passed"
    store.update(identifier, complete, status="review", cancel_requested=False)
    write_reports(store, identifier)
    assert client.post(f"/api/runs/{identifier}/cancel", headers=headers).status_code == 409
    review = client.post(f"/api/runs/{identifier}/review", headers=headers,
                         json={"step_index": 4, "decision": "failed", "note": "窗口文字被截断"})
    assert review.status_code == 200
    assert review.json()["status"] == "failed"
    assert review.json()["steps"][4]["reviewed_at"]
    report = client.get(f"/api/runs/{identifier}/artifacts/report.json").json()
    assert report["status"] == "failed"
    feedback = client.get(f"/api/runs/{identifier}/artifacts/feedback.md").text
    assert "窗口文字被截断" in feedback
    bundle = client.get(f"/api/runs/{identifier}/bundle")
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        assert "report.json" in archive.namelist()
        assert json.loads(archive.read("report.json"))["status"] == "failed"
    assert client.get(f"/api/runs/{identifier}/artifacts/notes.exe").status_code == 404
    assert client.get(f"/api/runs/{identifier}/artifacts/..%5C..%5Cprooflane.db").status_code == 404


def test_storage_returns_detached_snapshots(tmp_path):
    store = Store(tmp_path)
    run = store.create(spec(), package(store))
    run["status"] = "passed"
    assert store.get(run["id"])["status"] == "queued"
