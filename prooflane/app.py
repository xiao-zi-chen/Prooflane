import asyncio
import contextlib
import secrets
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .models import DEMO_STEPS, Review, RunSpec, CampaignSpec, NodeRegistration, LeaseProgress
from .platforms import FORMATS, LABELS, capability, current_platform, current_architecture, package_suffix, validate_package
from .coordination import Coordinator
from .environment import desktop_available
from .runner import Worker, write_reports
from .storage import Store, TERMINAL, now
from .demo import native_demo_package
from .strategies import PLANS, build_kit, invitation

ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD = 300 * 1024 * 1024


def create_app(data_root=None, start_worker=True):
    store = Store(Path(data_root or os.environ.get("PROOFLANE_DATA", ROOT / "data")).resolve())
    worker = Worker(store)
    demo_lock = threading.Lock()
    coordinator = Coordinator(store)
    token_path = store.root / "agent-token"
    if not token_path.exists():
        token_path.write_text(secrets.token_urlsafe(40), encoding="utf-8")
        if os.name != "nt":
            token_path.chmod(0o600)
    enrollment_token = os.environ.get("PROOFLANE_AGENT_TOKEN") or token_path.read_text(encoding="utf-8").strip()
    local_enabled = start_worker and os.environ.get("PROOFLANE_LOCAL_WORKER", "1") == "1"

    async def maintain_leases():
        while True:
            await run_in_threadpool(coordinator.expire)
            await asyncio.sleep(3)

    @asynccontextmanager
    async def lifespan(app):
        lock_file = None
        if local_enabled:
            lock_file = (store.root / "worker.lock").open("a+b")
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    lock_file.close()
                    raise RuntimeError("这个数据目录已有执行器运行；请勿启用多个 Uvicorn workers")
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            worker.start()
        maintenance = asyncio.create_task(maintain_leases())
        try:
            yield
        finally:
            maintenance.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await maintenance
            if local_enabled:
                worker.stop()
            if lock_file:
                lock_file.close()

    app = FastAPI(title="Prooflane", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.worker = store, worker
    app.state.coordinator = coordinator
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"] + [h.strip() for h in os.environ.get("PROOFLANE_ALLOWED_HOSTS", "").split(",") if h.strip()])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.url.path.startswith("/api/agents/"):
            origin = request.headers.get("origin")
            if request.headers.get("x-prooflane-client") != "web" or (origin and urlparse(origin).netloc != request.headers.get("host")):
                return JSONResponse({"detail": "请从本地 Prooflane 页面或授权的本地 API 客户端提交"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        return response

    def get_run(identifier):
        run = store.get(identifier)
        if not run:
            raise HTTPException(404, "没有找到这次测试")
        return run

    @app.exception_handler(PermissionError)
    async def forbidden(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    def bearer(request):
        value = request.headers.get("authorization", "")
        if not value.startswith("Bearer "):
            raise HTTPException(401, "执行节点需要 Bearer 凭据")
        return value[7:]

    @app.get("/api/platforms")
    def platforms():
        local = capability()
        local["ready"] = local["ready"] and local_enabled
        nodes = [local] + coordinator.nodes()
        return [{"id": kind, "name": LABELS[kind], "formats": FORMATS[kind],
                 "validation": "Windows 样本已完成实机验证" if kind == "windows" else "适配器实验阶段，待对应实机验证",
                 "nodes": [n for n in nodes if n["platform"] == kind],
                 "available": any(n["ready"] and n["online"] for n in nodes if n["platform"] == kind)}
                for kind in FORMATS]

    @app.post("/api/agents/register")
    def register_node(registration: NodeRegistration, request: Request):
        if not secrets.compare_digest(bearer(request), enrollment_token):
            raise HTTPException(403, "节点注册凭据无效")
        return coordinator.register(registration.model_dump())

    @app.get("/api/strategies")
    def strategies():
        return [{"id": kind, **plan} for kind, plan in PLANS.items()]

    def handoff_run(kind, run_id):
        run = get_run(run_id) if run_id else None
        if run and run["platform"] != kind:
            raise HTTPException(422, "所选任务不属于此平台")
        return run

    @app.get("/api/strategies/{kind}/invitation")
    def strategy_invitation(kind: Literal["windows", "macos", "linux"], run_id: str | None = None):
        return {"text": invitation(kind, handoff_run(kind, run_id))}

    @app.get("/api/strategies/{kind}/kit")
    def strategy_kit(kind: Literal["windows", "macos", "linux"], run_id: str | None = None, include_package: bool = False):
        run = handoff_run(kind, run_id)
        package_path = None
        if include_package:
            if not run:
                raise HTTPException(422, "包含应用构建前请先选择具体任务")
            package = store.package(run["spec"]["package_id"])
            if not package:
                raise HTTPException(404, "原始应用构建已不可用")
            package_path = Path(package["path"]).resolve()
            if not package_path.is_relative_to((store.root / "packages").resolve()) or not package_path.is_file():
                raise HTTPException(404, "原始应用构建已不可用")
        archive = build_kit(kind, run, package_path)
        def chunks():
            try:
                while chunk := archive.read(128*1024):
                    yield chunk
            finally:
                archive.close()
        return StreamingResponse(chunks(), media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="prooflane-{kind}-handoff.zip"', "Cache-Control": "no-store"},
            background=BackgroundTask(archive.close))

    @app.post("/api/agents/{node_id}/heartbeat")
    async def node_heartbeat(node_id: str, request: Request):
        body = await request.json()
        return coordinator.heartbeat(node_id, bearer(request), bool(body.get("ready")), str(body.get("detail", "")))

    @app.post("/api/agents/{node_id}/claim")
    def claim_node(node_id: str, request: Request):
        return {"run": coordinator.claim(node_id, bearer(request))}

    @app.get("/api/agents/{node_id}/runs/{run_id}/package")
    def agent_package(node_id: str, run_id: str, lease: str, request: Request):
        run = coordinator.owned(node_id, bearer(request), run_id, lease)
        package = store.package(run["spec"]["package_id"])
        return FileResponse(package["path"], filename=package["name"], media_type="application/octet-stream")

    @app.post("/api/agents/{node_id}/runs/{run_id}/progress")
    def agent_progress(node_id: str, run_id: str, progress: LeaseProgress, request: Request):
        run = coordinator.progress(node_id, bearer(request), run_id, progress.model_dump())
        return {"cancel_requested": run["cancel_requested"]}

    @app.post("/api/agents/{node_id}/runs/{run_id}/result")
    async def agent_result(node_id: str, run_id: str, lease: str, request: Request, file: UploadFile = File(...)):
        coordinator.owned(node_id, bearer(request), run_id, lease)
        # Stream to a temporary file; package size is bounded before extraction.
        target = store.directory(run_id) / (uuid.uuid4().hex + ".upload")
        try:
            size = 0
            with target.open("wb") as output:
                while chunk := await file.read(1024*1024):
                    size += len(chunk)
                    if size > 500*1024*1024:
                        raise HTTPException(413, "结果包不能超过 500 MB")
                    output.write(chunk)
            return await run_in_threadpool(coordinator.receive, node_id, bearer(request), run_id, lease, target)
        finally:
            target.unlink(missing_ok=True)
            await file.close()

    @app.get("/api/campaigns")
    def campaigns():
        return coordinator.campaigns()

    @app.get("/api/campaigns/{identifier}")
    def campaign(identifier: str):
        value = coordinator.get_campaign(identifier)
        if not value:
            raise HTTPException(404, "没有找到此平台对照任务")
        return value

    @app.post("/api/campaigns", status_code=201)
    def create_campaign(spec: CampaignSpec):
        for target in spec.targets:
            package = store.package(target.package_id)
            if not package:
                raise HTTPException(404, "平台安装包不存在")
            validate_package(target, package)
        runs = [submit(target) for target in spec.targets]
        return coordinator.campaign(spec.name, runs)

    @app.get("/api/health")
    def health():
        native = capability()
        kind = native["platform"]
        display = f"Windows {'11' if sys.getwindowsversion().build >= 22000 else '10'}" if kind == "windows" else LABELS.get(kind, platform.system())
        return {"name": "本机执行节点", "os": platform.platform(), "architecture": platform.machine(),
                "display_os": display, "ready": native["ready"] and local_enabled,
                "desktop_available": native["ready"], "active_run": worker.active,
                "queue_size": worker.queue.qsize(), "max_upload_mb": 300, "platform": kind, "local_enabled": local_enabled,
                "isolation": "host", "concurrency": 1, "detail": native["detail"]}

    @app.post("/api/packages", status_code=201)
    async def upload(file: UploadFile = File(...)):
        name = (file.filename or "").replace("\\", "/").split("/")[-1]
        extension = package_suffix(name)
        if extension not in {ext for formats in FORMATS.values() for ext in formats}:
            raise HTTPException(422, "支持 EXE、MSI、ZIP、DMG、PKG、AppImage 和 tar.gz")
        if len(name) > 180:
            raise HTTPException(422, "文件名不能超过 180 个字符")
        if PureWindowsPath(name).is_reserved() or any(ord(c) < 32 or c in '<>:"|?*' for c in name) or name.endswith((" ", ".")):
            raise HTTPException(422, "文件名包含 Windows 保留名称或非法字符")
        identifier = uuid.uuid4().hex
        directory = store.root / "packages" / identifier
        directory.mkdir(parents=True)
        path = directory / name
        size, digest = 0, hashlib.sha256()
        try:
            with path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, "文件不能超过 300 MB")
                    digest.update(chunk)
                    output.write(chunk)
            if not size:
                raise HTTPException(422, "安装包为空")
            with path.open("rb") as stream:
                signature = stream.read(8)
            if extension == ".exe" and signature[:2] != b"MZ":
                raise HTTPException(422, "文件不是有效的 Windows EXE")
            if extension == ".msi" and signature != bytes.fromhex("d0cf11e0a1b11ae1"):
                raise HTTPException(422, "文件不是有效的 MSI 安装包")
            if extension == ".zip" and signature[:2] != b"PK":
                raise HTTPException(422, "文件不是有效的 ZIP 压缩包")
            if extension == ".appimage" and signature[:4] != b"\x7fELF":
                raise HTTPException(422, "AppImage 必须是有效 ELF 文件")
            if extension == ".tar.gz" and signature[:2] != b"\x1f\x8b":
                raise HTTPException(422, "tar.gz 文件头无效")
            package = {"id": identifier, "name": name, "size": size, "sha256": digest.hexdigest(), "path": str(path)}
            store.put_package(package)
            return {k: v for k, v in package.items() if k != "path"}
        except Exception:
            path.unlink(missing_ok=True)
            directory.rmdir()
            raise
        finally:
            await file.close()

    def submit(spec):
        package = store.package(spec.package_id)
        if not package:
            raise HTTPException(404, "找不到安装包，请重新上传")
        validate_package(spec, package)
        local = capability()
        matches = local_enabled and local["ready"] and spec.platform == local["platform"] and spec.architecture in ("any", local["architecture"])
        run = store.create(spec.model_dump(), package)
        if matches:
            run = store.update(run["id"], worker_id="local", worker_name="本机执行节点")
            worker.submit(run["id"])
        else:
            run = store.update(run["id"], status="waiting_worker")
        return run

    @app.post("/api/runs", status_code=201)
    def create_run(spec: RunSpec):
        return submit(spec)

    @app.get("/api/runs")
    def list_runs():
        return store.list()

    @app.get("/api/runs/{identifier}")
    def read_run(identifier: str):
        return get_run(identifier)

    @app.post("/api/runs/{identifier}/cancel")
    def cancel(identifier: str):
        if get_run(identifier)["status"] in TERMINAL:
            raise HTTPException(409, "测试已经结束")
        run = store.update(identifier, cancel_requested=True)
        if run["status"] in {"queued", "waiting_worker"}:
            def skip(value):
                for step in value["steps"]:
                    step.update(status="skipped", detail="开始执行前已取消")
            run = store.update(identifier, skip, status="cancelled", finished_at=now(), error="任务在开始前已取消")
            write_reports(store, identifier)
        return run

    @app.post("/api/runs/{identifier}/retry", status_code=201)
    def retry(identifier: str):
        run = get_run(identifier)
        if run["status"] not in TERMINAL:
            raise HTTPException(409, "请等待当前测试结束后重跑")
        return submit(RunSpec.model_validate(run["spec"]))

    @app.post("/api/runs/{identifier}/review")
    def review(identifier: str, review: Review):
        run = get_run(identifier)
        if run["status"] not in TERMINAL or not (store.directory(identifier) / "bundle.zip").exists():
            raise HTTPException(409, "请等待报告生成后复核")
        def apply(run):
            if review.step_index >= len(run["steps"]) or run["steps"][review.step_index]["status"] != "review":
                raise HTTPException(409, "这一步不在待复核状态")
            step = run["steps"][review.step_index]
            step.update(status=review.decision, detail=f"人工复核：{review.note}", reviewed_at=now())
            if run["status"] == "review":
                if any(s["status"] == "failed" for s in run["steps"]):
                    run["status"] = "failed"
                    run["error"] = f"人工复核发现问题：{review.note}"
                elif all(s["status"] == "passed" for s in run["steps"]) and not run["warnings"]:
                    run["status"] = "passed"
        with store.lock:
            store.update(identifier, apply)
            write_reports(store, identifier)
        return store.get(identifier)

    @app.get("/api/runs/{identifier}/artifacts/{filename}")
    def artifact(identifier: str, filename: str):
        run = get_run(identifier)
        # During execution, only expose captured screenshots explicitly referenced by a step.
        allowed = set(run["artifacts"]) | {s["screenshot"] for s in run["steps"] if s.get("screenshot")}
        if filename not in allowed or Path(filename).name != filename or "\\" in filename:
            raise HTTPException(404, "证据不存在")
        path = store.directory(identifier) / filename
        if not path.is_file():
            raise HTTPException(404, "证据尚未生成")
        media = {".png": "image/png", ".mp4": "video/mp4", ".json": "application/json", ".md": "text/plain; charset=utf-8", ".log": "text/plain; charset=utf-8"}
        return FileResponse(path, media_type=media.get(path.suffix, "application/octet-stream"))

    @app.get("/api/runs/{identifier}/bundle")
    def bundle(identifier: str):
        get_run(identifier)
        path = store.directory(identifier) / "bundle.zip"
        if not path.is_file():
            raise HTTPException(409, "报告正在生成，请稍后重试")
        return FileResponse(path, media_type="application/zip", filename=f"prooflane-{identifier[:8]}.zip")

    async def windows_demo_package():
        if os.name != "nt":
            raise HTTPException(503, "真实演示需要 Windows 主机")
        directory = store.root / "demo"
        directory.mkdir(exist_ok=True)
        source = ROOT / "demo" / "NotesDemo.cs"
        executable = directory / "ProoflaneNotes.exe"
        if not executable.exists() or executable.stat().st_mtime < source.stat().st_mtime:
            compiler = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
            if not compiler.exists():
                raise HTTPException(503, "演示程序需要 Windows .NET Framework C# 编译器")
            def build():
                with demo_lock:
                    return subprocess.run([str(compiler), "/nologo", "/target:winexe", "/reference:System.Windows.Forms.dll",
                                       "/reference:System.Drawing.dll", f"/out:{executable}", str(source)],
                                      capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
            result = await run_in_threadpool(build)
            if result.returncode:
                raise HTTPException(500, "演示程序编译失败：" + result.stdout.decode(errors="replace"))
        identifier = uuid.uuid4().hex
        package_path = store.root / "packages" / f"{identifier}.exe"
        package_path.parent.mkdir(exist_ok=True)
        shutil.copy2(executable, package_path)
        package = {"id": identifier, "name": "ProoflaneNotes.exe", "size": executable.stat().st_size,
                   "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(), "path": str(package_path), "demo": True}
        store.put_package(package)
        return package

    @app.post("/api/demo", status_code=201)
    async def demo():
        package = await windows_demo_package()
        return submit(RunSpec(name="Notes · Windows 实机演示", package_id=package["id"],
                              window_title="Prooflane Notes", steps=DEMO_STEPS))

    @app.post("/api/demo/campaign", status_code=201)
    async def demo_campaign():
        packages = {"windows": await windows_demo_package()}
        for kind in ("macos", "linux"):
            packages[kind] = native_demo_package(store, kind)
        targets = []
        for kind, package in packages.items():
            steps = [dict(step) for step in DEMO_STEPS[:4]]
            if kind == "linux":
                steps[1].update(automation_id="", target="Note")
                steps[2].update(automation_id="", target="Save note")
            targets.append(RunSpec(name="Notes · 三平台共同验收", platform=kind,
                package_id=package["id"], window_title="Prooflane Notes", steps=steps,
                app_path={"windows": "", "macos": "ProoflaneNotes.app", "linux": "ProoflaneNotes"}[kind]))
        return create_campaign(CampaignSpec(name="Notes · Windows / macOS / Linux", targets=targets))

    app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="web")
    return app


app = create_app()
