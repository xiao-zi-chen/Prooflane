"""Real Windows agent -> independent controller -> returned evidence, over HTTP."""
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prooflane.models import DEMO_STEPS


def main():
    directory = ROOT / "data" / "remote-e2e" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    environment = dict(os.environ, PROOFLANE_DATA=str(directory / "hub"), PROOFLANE_LOCAL_WORKER="0")
    server = None
    agent = None
    with (directory / "hub.log").open("wb") as hub_log, (directory / "agent.log").open("wb") as agent_log:
        try:
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "prooflane.app:app", "--host", "127.0.0.1", "--port", "8766", "--no-access-log"], cwd=ROOT, env=environment,
                                      stdout=hub_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            with httpx.Client(base_url="http://127.0.0.1:8766", headers={"X-Prooflane-Client": "web"}, timeout=20) as client:
                deadline = time.monotonic()+15
                while time.monotonic()<deadline:
                    try:
                        response=client.get("/api/health")
                        if response.status_code==200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError("Integration controller did not start")
                assert response.json()["local_enabled"] is False
                with (ROOT / "data/demo/ProoflaneNotes.exe").open("rb") as executable:
                    package=client.post("/api/packages", files={"file": ("ProoflaneNotes.exe", executable)}).json()
                response=client.post("/api/runs", json={"name": "真实远程协议验证 · Windows 节点", "platform": "windows", "architecture": "x86_64",
                    "package_id": package["id"], "window_title": "Prooflane Notes", "steps": DEMO_STEPS[:4]})
                response.raise_for_status()
                run=response.json()
                assert run["status"]=="waiting_worker"
                agent=subprocess.Popen([sys.executable,"-m","prooflane.agent","--server","http://127.0.0.1:8766","--token-file",str(directory/"hub/agent-token"),
                    "--data",str(directory/"agent"),"--name","HTTP integration Windows","--once"],cwd=ROOT,stdout=agent_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                deadline=time.monotonic()+100
                while time.monotonic()<deadline:
                    run=client.get(f"/api/runs/{run['id']}").json()
                    if run["status"] in {"passed","failed","interrupted","cancelled","review"}:
                        break
                    if agent.poll() is not None:
                        raise AssertionError(f"Agent exited early: {agent.returncode}; see {directory/'agent.log'}")
                    time.sleep(.4)
                assert run["status"]=="passed", run
                assert run["worker_id"] not in (None,"local")
                assert run["platform"]=="windows" and run["package"]["sha256"]==package["sha256"]
                response=client.get(f"/api/runs/{run['id']}/bundle")
                response.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    assert "recording.mp4" in archive.namelist()
                    assert len([n for n in archive.namelist() if n.endswith('.png')])==4
                    report=json.loads(archive.read("report.json"))
                    assert "lease" not in report
                    assert report["status"]=="passed"
                agent.wait(timeout=20)
                assert agent.returncode==0
                (ROOT/"artifacts/remote-e2e.json").write_text(json.dumps({"status":"passed","run_id":run["id"],"platform":"windows","controller_local_worker":False,
                    "evidence_directory":str(directory/"hub/runs"/run["id"]),"note":"真实 Windows GUI 经独立节点协议执行；不代表 macOS/Linux 实机验证"},ensure_ascii=False,indent=2),encoding="utf-8")
                print("Real Windows HTTP agent E2E passed: claim, package download, GUI, progress, artifact upload, report download.")
        finally:
            if agent and agent.poll() is None:
                agent.terminate()
                agent.wait(timeout=10)
            if server and server.poll() is None:
                server.terminate()
                server.wait(timeout=10)


if __name__=="__main__":
    main()
