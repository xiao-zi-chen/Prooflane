"""Runs owned Windows fixtures through the real HTTP/upload/desktop/report chain.

Requires the local server on :8765 and an unlocked desktop. Only launches the
included demo app. Writes evidence IDs to artifacts/e2e-results.json.
"""
import copy
import io
import json
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

import httpx
import imageio_ffmpeg

BASE = "http://127.0.0.1:8765"
ROOT = Path(__file__).resolve().parent.parent
CLIENT = httpx.Client(base_url=BASE, headers={"X-Prooflane-Client": "web"}, timeout=60)


def post(path, **kwargs):
    response = CLIENT.post(path, **kwargs)
    response.raise_for_status()
    return response.json()


def wait(identifier, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = CLIENT.get(f"/api/runs/{identifier}").json()
        if run["status"] in ("passed", "failed", "review", "cancelled", "interrupted"):
            if CLIENT.get(f"/api/runs/{identifier}/bundle").status_code == 200:
                return run
        time.sleep(0.4)
    raise TimeoutError(f"Run {identifier} did not complete")


def check_evidence(run, screenshots):
    assert sum(name.endswith(".png") for name in run["artifacts"]) == screenshots
    bundle = CLIENT.get(f"/api/runs/{run['id']}/bundle")
    bundle.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        assert {"report.json", "feedback.md", "execution.log", "crash-events.json"}.issubset(archive.namelist())
        assert json.loads(archive.read("report.json"))["status"] == run["status"]
    video = ROOT / "data/runs" / run["id"] / "recording.mp4"
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video), "-f", "null", "-"],
                            capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stderr


def main():
    results = {}
    demo = wait(post("/api/demo")["id"])
    assert demo["status"] == "review", demo
    assert [s["status"] for s in demo["steps"]] == ["passed"] * 4 + ["review"]
    check_evidence(demo, 5)
    results["real_gui_success_and_capture"] = demo["id"]
    # This is an explicitly labelled API review fixture, not a claim of human visual QA.
    reviewed = post(f"/api/runs/{demo['id']}/review", json={"step_index": 4, "decision": "passed", "note": "自动化回归用例：验证人工复核接口及报告更新，不代表人工视觉验收"})
    assert reviewed["status"] == "passed"
    assert CLIENT.get(f"/api/runs/{demo['id']}/artifacts/report.json").json()["status"] == "passed"
    results["review_round_trip"] = demo["id"]
    base = demo["spec"]

    failing = copy.deepcopy(base)
    failing["name"] = "回归验证 · 故意设置错误的预期文本"
    failing["steps"][3].update(value="THIS TEXT MUST NOT EXIST", timeout=2)
    run = wait(post("/api/runs", json=failing)["id"])
    assert run["status"] == "failed", run
    assert run["steps"][3]["status"] == "failed" and run["steps"][4]["status"] == "skipped"
    check_evidence(run, 4)
    results["assertion_failure_and_skip"] = run["id"]

    cancel_spec = copy.deepcopy(failing)
    cancel_spec["name"] = "回归验证 · 取消运行中任务"
    cancel_spec["steps"][3]["timeout"] = 60
    active = post("/api/runs", json=cancel_spec)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        current = CLIENT.get(f"/api/runs/{active['id']}").json()
        if current["steps"][3]["status"] == "running":
            break
        time.sleep(.2)
    else:
        raise AssertionError("Cancellation fixture did not reach the waiting assertion")
    queued = post("/api/runs", json=base)
    assert queued["status"] == "queued"
    post(f"/api/runs/{queued['id']}/cancel")
    post(f"/api/runs/{active['id']}/cancel")
    assert wait(active["id"])["status"] == "cancelled"
    assert wait(queued["id"])["status"] == "cancelled"
    results["running_cancel"] = active["id"]
    results["queued_cancel"] = queued["id"]

    exe = ROOT / "data/demo/ProoflaneNotes.exe"
    with exe.open("rb") as source:
        package = post("/api/packages", files={"file": ("ProoflaneNotes.exe", source, "application/octet-stream")})
    uploaded = copy.deepcopy(base)
    uploaded.update(package_id=package["id"], name="回归验证 · 上传便携 EXE", steps=base["steps"][:4])
    run = wait(post("/api/runs", json=uploaded)["id"])
    assert run["status"] == "passed", run
    check_evidence(run, 4)
    results["uploaded_exe"] = run["id"]

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.write(exe, "Notes/ProoflaneNotes.exe")
        archive.writestr("Notes/data.txt", "bundled resource")
    package = post("/api/packages", files={"file": ("Notes.zip", stream.getvalue(), "application/zip")})
    zipped = copy.deepcopy(uploaded)
    zipped.update(package_id=package["id"], app_path="Notes/ProoflaneNotes.exe", name="回归验证 · 上传 ZIP 程序")
    run = wait(post("/api/runs", json=zipped)["id"])
    assert run["status"] == "passed", run
    check_evidence(run, 4)
    results["uploaded_zip"] = run["id"]

    installation_dir = ROOT / "data/e2e-installations" / uuid.uuid4().hex
    installed = copy.deepcopy(uploaded)
    installed.update(name="回归验证 · 静默 EXE 安装后启动", mode="installer", app_path=str(installation_dir / "ProoflaneNotes.exe"),
                     install_args=["--install-to", str(installation_dir)])
    run = wait(post("/api/runs", json=installed)["id"])
    assert run["status"] == "passed", run
    assert (installation_dir / "ProoflaneNotes.exe").is_file()
    assert "installer.log" in run["artifacts"]
    check_evidence(run, 4)
    results["silent_exe_install"] = run["id"]

    crashed = copy.deepcopy(uploaded)
    crashed.update(name="回归验证 · 程序启动即异常退出", app_args=["--exit-error"])
    run = wait(post("/api/runs", json=crashed)["id"])
    assert run["status"] == "failed" and "42" in run["error"], run
    results["nonzero_exit"] = run["id"]

    final = wait(post("/api/demo")["id"])
    assert final["status"] == "review", final
    results["final_demo_for_manual_review"] = final["id"]
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    (output / "e2e-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print("All real Windows E2E checks passed.")


if __name__ == "__main__":
    main()
