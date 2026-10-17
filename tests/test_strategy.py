import hashlib
import io
import json
import re
import shlex
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


def create_task(hub, kind="linux", filename="app.zip"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("app", "protocol fixture; not an application")
    package = hub.post("/api/packages", headers=HEADERS, files={"file": (filename, stream.getvalue())}).json()
    response = hub.post("/api/runs", headers=HEADERS, json={"name": "delegated task", "platform": kind,
        "package_id": package["id"], "window_title": "Notes", "steps": DEMO_STEPS[:4], "app_path": "app"})
    assert response.status_code == 201
    return response.json()


def assert_kit_language_links(archive):
    for name in archive.namelist():
        if not name.endswith(".md"):
            continue
        content = archive.read(name).decode("utf-8")
        counterpart = name[:-6] + ".md" if name.endswith(".en.md") else name[:-3] + ".en.md"
        assert f"]({counterpart})" in content, name
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            assert target in archive.namelist(), (name, target)


@pytest.mark.parametrize("kind", ["windows", "macos", "linux"])
def test_generic_strategy_is_shareable_without_local_machine_data(hub, kind):
    response = hub.get(f"/api/strategies/{kind}/kit")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "README.md", "README.en.md", "INVITATION.txt", "INVITATION.en.txt", "scenario.json",
            "STRATEGY.md", "STRATEGY.en.md", "ACCEPTANCE.md", "ACCEPTANCE.en.md",
            "ISSUE_TEMPLATE.md", "ISSUE_TEMPLATE.en.md",
        }
        assert_kit_language_links(archive)
        assert b"generic kit" in archive.read("README.en.md")
        manifest = json.loads(archive.read("scenario.json"))
        assert manifest["platform"] == kind and manifest["spec"] is None
        data = b"\n".join(archive.read(name) for name in archive.namelist())
        secret = (hub.app.state.store.root / "agent-token").read_bytes()
        assert secret not in data
        assert b"test-machines.md" not in data
    assert hub.get("/api/runs").json() == []


@pytest.mark.parametrize("kind", ["windows", "macos", "linux"])
def test_bound_kit_uses_original_scenario_and_only_includes_build_when_selected(hub, kind):
    run = create_task(hub, kind)
    original = hub.get("/api/runs/"+run["id"]).json()
    for include in (False, True):
        response = hub.get(f"/api/strategies/{kind}/kit", params={"run_id": run["id"], "include_package": include})
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert_kit_language_links(archive)
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


@pytest.mark.parametrize("kind", ["windows", "macos", "linux"])
def test_bilingual_instructions_preserve_scenario_and_literal_package_argument(hub, kind):
    filename = "note's $(probe).zip"
    run = create_task(hub, kind, filename)
    response = hub.get(f"/api/strategies/{kind}/kit", params={"run_id": run["id"], "include_package": True})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("scenario.json"))
        commands = []
        for suffix in ("", ".en"):
            content = archive.read(f"README{suffix}.md").decode("utf-8")
            for step in run["spec"]["steps"]:
                assert step["title"] in content
            assert run["package"]["sha256"] in archive.read(f"INVITATION{suffix}.txt").decode("utf-8")
            command = next(line for line in content.splitlines() if " -m prooflane.handoff " in line and line.endswith(" --check"))
            commands.append(command)
            if kind == "windows":
                assert command.endswith("--package 'application/note''s $(probe).zip' --check")
            else:
                assert shlex.split(command)[-2:] == [manifest["package"]["file"], "--check"]
        assert commands[0] == commands[1]
        assert manifest["spec"]["steps"] == run["spec"]["steps"]


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
