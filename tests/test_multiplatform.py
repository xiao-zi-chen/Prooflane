import concurrent.futures
import io
import json
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from prooflane.app import create_app
from prooflane.coordination import Coordinator
from prooflane.models import RunSpec, DEMO_STEPS
from prooflane.storage import Store

HEADERS = {"X-Prooflane-Client": "web"}


@pytest.fixture
def hub(tmp_path):
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        yield client


def package(hub, name="notes.zip"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("app", "fixture for protocol tests, not an executable")
    response = hub.post("/api/packages", headers=HEADERS, files={"file": (name, stream.getvalue())})
    assert response.status_code == 201
    return response.json()


def spec(package_id, kind="linux", arch="any"):
    return RunSpec(name="protocol fixture", package_id=package_id, platform=kind, architecture=arch,
                   window_title="Notes", steps=DEMO_STEPS[:4]).model_dump()


def register(hub, kind="linux", arch="x86_64"):
    secret = (hub.app.state.store.root / "agent-token").read_text().strip()
    response = hub.post("/api/agents/register", headers={"Authorization": "Bearer "+secret},
        json={"name": kind+" fixture", "platform": kind, "architecture": arch, "ready": True})
    assert response.status_code == 200
    return response.json()


def claim(hub, node):
    return hub.post(f"/api/agents/{node['id']}/claim", headers={"Authorization": "Bearer "+node['token']}).json()["run"]


def test_multiplatform_waiting_is_not_success(hub):
    info = package(hub)
    response = hub.post("/api/campaigns", headers=HEADERS, json={"name": "all platforms", "targets": [spec(info["id"], p) for p in ("windows", "macos", "linux")]})
    assert response.status_code == 201
    report = hub.get("/api/campaigns/"+response.json()["id"]).json()
    assert {r["platform"] for r in report["runs"]} == {"windows", "macos", "linux"}
    assert all(r["status"] == "waiting_worker" for r in report["runs"])
    assert report["passed"] is False and report["complete"] is False
    assert all(r["campaign_id"] == report["id"] for r in report["runs"])


def test_campaign_rejects_misaligned_steps_and_bad_target_format(hub):
    info = package(hub)
    windows, linux = spec(info["id"], "windows"), spec(info["id"])
    linux["steps"][0]["title"] = "Different scenario"
    assert hub.post("/api/campaigns", headers=HEADERS, json={"name": "invalid", "targets": [windows, linux]}).status_code == 422
    exe = hub.post("/api/packages", headers=HEADERS, files={"file": ("notes.exe", b"MZfixture")}).json()
    assert hub.post("/api/runs", headers=HEADERS, json=spec(exe["id"], "macos")).status_code == 422


def test_nodes_authenticate_and_claim_only_matching_platform_arch(hub):
    info = package(hub)
    mac_run = hub.post("/api/runs", headers=HEADERS, json=spec(info["id"], "macos", "arm64")).json()
    assert hub.post("/api/agents/register", json={"name": "x", "platform": "linux", "architecture": "x86_64"}).status_code == 401
    linux = register(hub)
    assert claim(hub, linux) is None
    mac_intel = register(hub, "macos")
    assert claim(hub, mac_intel) is None
    mac_arm = register(hub, "macos", "arm64")
    claimed = claim(hub, mac_arm)
    assert claimed["id"] == mac_run["id"]
    assert claim(hub, mac_arm)["lease"] == claimed["lease"]
    response = hub.get(f"/api/agents/{linux['id']}/runs/{claimed['id']}/package", params={"lease": claimed["lease"]}, headers={"Authorization": "Bearer "+linux["token"]})
    assert response.status_code == 403
    assert "secret_hash" not in json.dumps(hub.get("/api/platforms").json())


def test_claim_is_transactional_across_coordinators(hub):
    info = package(hub)
    hub.post("/api/runs", headers=HEADERS, json=spec(info["id"]))
    nodes = [register(hub), register(hub)]
    def take(node):
        return Coordinator(Store(hub.app.state.store.root)).claim(node["id"], node["token"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(take, nodes))
    assert sum(r is not None for r in results) == 1


def test_lease_expiry_preserves_unknown_and_rejects_late_results(hub):
    info = package(hub)
    hub.post("/api/runs", headers=HEADERS, json=spec(info["id"]))
    node = register(hub)
    run = claim(hub, node)
    hub.app.state.store.update(run["id"], lease_until=time.time()-1)
    hub.app.state.coordinator.expire()
    assert hub.get("/api/runs/"+run["id"]).json()["status"] == "interrupted"
    assert claim(hub, register(hub)) is None
    response = hub.post(f"/api/agents/{node['id']}/runs/{run['id']}/progress", headers={"Authorization": "Bearer "+node['token']},
                        json={"lease": run["lease"], "status": "running", "steps": run["steps"], "environment": {}})
    assert response.status_code == 422


def test_heartbeat_renews_lease_during_transfer_and_cancel_waiting(hub):
    info = package(hub)
    queued = hub.post("/api/runs", headers=HEADERS, json=spec(info["id"])).json()
    node = register(hub)
    run = claim(hub, node)
    hub.app.state.store.update(run["id"], lease_until=time.time()+3)
    hub.post(f"/api/agents/{node['id']}/heartbeat", headers={"Authorization": "Bearer "+node['token']}, json={"ready": True})
    assert hub.app.state.store.get(run["id"])["lease_until"] > time.time()+35
    waiting = hub.post("/api/runs", headers=HEADERS, json=spec(info["id"], "macos")).json()
    cancelled = hub.post(f"/api/runs/{waiting['id']}/cancel", headers=HEADERS).json()
    assert cancelled["status"] == "cancelled"
    assert claim(hub, register(hub, "macos")) is None


def test_remote_report_rejects_missing_evidence_and_keeps_provenance(hub):
    info = package(hub)
    hub.post("/api/runs", headers=HEADERS, json=spec(info["id"]))
    node = register(hub)
    run = claim(hub, node)
    result = dict(run, status="passed", warnings=[])
    result["steps"] = [dict(s, status="passed", screenshot=None) for s in run["steps"]]
    def upload(value, extras=()):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("report.json", json.dumps(value))
            for name, content in extras:
                archive.writestr(name, content)
        return hub.post(f"/api/agents/{node['id']}/runs/{run['id']}/result", params={"lease": run["lease"]},
                        headers={"Authorization": "Bearer "+node['token']}, files={"file": ("report.zip", stream.getvalue())})
    assert upload(result).status_code == 422
    assert upload(result, [("../escape.log", "bad")]).status_code == 422
    result.update(status="failed", platform="windows", spec={"package_id": "attacker"}, error="fixture failure")
    result["steps"] = [dict(s, status="failed", detail="fixture", screenshot=None) for s in run["steps"]]
    response = upload(result)
    assert response.status_code == 200
    assert response.json()["platform"] == "linux"
    assert response.json()["spec"]["package_id"] == info["id"]
    report = hub.get(f"/api/runs/{run['id']}/artifacts/report.json").json()
    assert "lease" not in report


def test_native_archive_rejects_links_and_traversal(tmp_path):
    import tarfile
    from prooflane.native import extract_tar
    source = tmp_path / "app.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        archive.addfile(link)
    with pytest.raises(ValueError):
        extract_tar(source, tmp_path / "target")
