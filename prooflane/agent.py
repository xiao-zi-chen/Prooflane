"""Pull agent: run on the actual target desktop, connect through a private tunnel."""
import argparse
import hashlib
import json
import os
import platform
import time
import threading
from pathlib import Path

import httpx

from .platforms import capability
from .runner import Worker
from .storage import Store, TERMINAL


def run_agent(server, token_file, data, name, once=False):
    root = Path(data).resolve()
    store = Store(root)
    worker = Worker(store)
    token = Path(token_file).read_text(encoding="utf-8-sig").strip()
    with httpx.Client(base_url=server.rstrip("/"), timeout=20) as client:
        node = capability()
        registration = client.post("/api/agents/register", headers={"Authorization": "Bearer "+token}, json={k: node[k] for k in ("platform", "architecture", "ready", "detail")} | {"name": name})
        registration.raise_for_status()
        auth = registration.json()
        client.headers["Authorization"] = "Bearer " + auth["token"]
        prefix = f"/api/agents/{auth['id']}"
        print(f"Node registered: {node['platform']} / {node['architecture']}; ready={node['ready']}", flush=True)
        worker.start()
        stop_ping = threading.Event()
        def heartbeat_loop():
            with httpx.Client(base_url=server.rstrip("/"), headers={"Authorization": "Bearer "+auth["token"]}, timeout=10) as ping:
                while not stop_ping.wait(5):
                    try:
                        ping.post(prefix+"/heartbeat", json={"ready": node["ready"], "detail": node["detail"]}).raise_for_status()
                    except httpx.HTTPError:
                        pass
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        try:
            while True:
                node = capability()
                client.post(prefix+"/heartbeat", json={"ready": node["ready"], "detail": node["detail"]}).raise_for_status()
                response = client.post(prefix+"/claim")
                response.raise_for_status()
                remote = response.json()["run"]
                if not remote:
                    if once:
                        return
                    time.sleep(3)
                    continue
                execute_claim(client, prefix, remote, store, worker)
                if once:
                    return
        finally:
            stop_ping.set()
            heartbeat_thread.join(timeout=11)
            worker.stop()
            try:
                client.post(prefix+"/heartbeat", json={"ready": False, "detail": "节点进程已退出"})
            except httpx.HTTPError:
                pass


def execute_claim(client, prefix, remote, store, worker):
    identifier, lease = remote["id"], remote["lease"]
    package = remote["package"].copy()
    folder = store.root / "packages" / package["id"]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / package["name"]
    if target.parent != folder or "\\" in package["name"]:
        raise ValueError("服务端返回非法文件名")
    digest, size = hashlib.sha256(), 0
    with client.stream("GET", prefix+f"/runs/{identifier}/package", params={"lease": lease}) as response:
        response.raise_for_status()
        with target.open("wb") as output:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 300*1024*1024:
                    raise ValueError("安装包超过限制")
                digest.update(chunk)
                output.write(chunk)
    if digest.hexdigest() != package["sha256"]:
        raise ValueError("下载包哈希不一致")
    package["path"] = str(target)
    if not store.package(package["id"]):
        store.put_package(package)
    local = json.loads(json.dumps(remote))
    local.update(status="queued", worker_id="local", artifacts=[])
    store.directory(identifier).mkdir(parents=True, exist_ok=True)
    with store.connect() as db:
        db.execute("INSERT OR REPLACE INTO runs VALUES (?,?)", (identifier, json.dumps(local)))
    worker.submit(identifier)
    last_success = time.monotonic()
    while True:
        run = store.get(identifier)
        try:
            response = client.post(prefix+f"/runs/{identifier}/progress", json={"lease": lease,
                "status": run["status"] if run["status"] in {"preparing", "installing", "running"} else "running",
                "steps": run["steps"], "environment": run["environment"]})
            response.raise_for_status()
            last_success = time.monotonic()
            if response.json()["cancel_requested"]:
                store.update(identifier, cancel_requested=True)
            client.post(prefix+"/heartbeat", json={"ready": True, "detail": f"正在处理 {identifier[:8]}"}).raise_for_status()
            if run["status"] in TERMINAL and (store.directory(identifier) / "bundle.zip").exists():
                with (store.directory(identifier) / "bundle.zip").open("rb") as result:
                    response = client.post(prefix+f"/runs/{identifier}/result", params={"lease": lease}, files={"file": ("result.zip", result, "application/zip")}, timeout=120)
                    response.raise_for_status()
                print(f"Uploaded {identifier}: {run['status']}", flush=True)
                return
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                store.update(identifier, cancel_requested=True)
                raise RuntimeError(f"控制台拒绝当前租约或结果：HTTP {exc.response.status_code}") from exc
            if time.monotonic()-last_success > 20:
                store.update(identifier, cancel_requested=True)
                raise
        except httpx.HTTPError:
            if time.monotonic()-last_success > 20:
                store.update(identifier, cancel_requested=True)
                raise RuntimeError("控制台连接中断；取消本机任务并保留本地证据")
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description="Prooflane native desktop agent")
    parser.add_argument("--server", default="http://127.0.0.1:8765")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--data", default="agent-data")
    parser.add_argument("--name", default=platform.node())
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    run_agent(args.server, args.token_file, args.data, args.name, args.once)


if __name__ == "__main__":
    main()
