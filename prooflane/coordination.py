"""Transactional native-node leases. Remote results never overwrite job provenance."""
import hashlib
import io
import json
import secrets
import time
import uuid
import zipfile
from pathlib import Path

from .storage import TERMINAL, now

LEASE_SECONDS = 45
STEP_STATES = {"pending", "running", "passed", "failed", "review", "cancelled", "skipped"}


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Coordinator:
    def __init__(self, store):
        self.store = store

    def nodes(self):
        with self.store.connect() as db:
            nodes = [json.loads(r[0]) for r in db.execute("SELECT body FROM nodes")]
        for node in nodes:
            node.pop("secret_hash", None)
            node["online"] = time.time() - node["last_seen"] < LEASE_SECONDS
        return nodes

    def register(self, registration):
        token = secrets.token_urlsafe(32)
        node = {**registration, "id": uuid.uuid4().hex, "secret_hash": digest(token), "last_seen": time.time(), "local": False}
        with self.store.connect() as db:
            db.execute("INSERT INTO nodes VALUES (?,?)", (node["id"], json.dumps(node)))
        return {"id": node["id"], "token": token, "lease_seconds": LEASE_SECONDS}

    def authenticate(self, identifier, token):
        with self.store.connect() as db:
            row = db.execute("SELECT body FROM nodes WHERE id=?", (identifier,)).fetchone()
        if not row or not secrets.compare_digest(json.loads(row[0])["secret_hash"], digest(token)):
            raise PermissionError("节点认证失败")
        return json.loads(row[0])

    def heartbeat(self, identifier, token, ready, detail):
        self.authenticate(identifier, token)
        with self.store.lock, self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            node = json.loads(db.execute("SELECT body FROM nodes WHERE id=?", (identifier,)).fetchone()[0])
            node.update(last_seen=time.time(), ready=ready, detail=detail[:1000])
            db.execute("UPDATE nodes SET body=? WHERE id=?", (json.dumps(node), identifier))
            for (body,) in db.execute("SELECT body FROM runs").fetchall():
                run = json.loads(body)
                if run.get("worker_id") == identifier and run["status"] not in TERMINAL and run.get("lease_until", 0) >= time.time():
                    run["lease_until"] = time.time()+LEASE_SECONDS
                    db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run), run["id"]))
        return {"ok": True}

    def claim(self, identifier, token):
        self.authenticate(identifier, token)
        with self.store.lock, self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            node = json.loads(db.execute("SELECT body FROM nodes WHERE id=?", (identifier,)).fetchone()[0])
            if not node["ready"] or time.time() - node["last_seen"] >= LEASE_SECONDS:
                return None
            runs = [json.loads(r[0]) for r in db.execute("SELECT body FROM runs ORDER BY rowid")]
            active = next((r for r in runs if r.get("worker_id") == identifier and r["status"] not in TERMINAL), None)
            if active:
                return active
            for run in runs:
                if run["status"] not in {"queued", "waiting_worker"} or run.get("worker_id"):
                    continue
                if run.get("platform", "windows") != node["platform"] or run.get("architecture", "any") not in ("any", node["architecture"]):
                    continue
                if run["cancel_requested"]:
                    continue
                run.update(status="preparing", worker_id=identifier, lease=secrets.token_urlsafe(32), lease_until=time.time()+LEASE_SECONDS,
                           started_at=now(), worker_name=node["name"])
                db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run), run["id"]))
                return run
        return None

    def owned(self, identifier, token, run_id, lease):
        self.authenticate(identifier, token)
        run = self.store.get(run_id)
        if not run or run.get("worker_id") != identifier or run.get("lease") != lease:
            raise PermissionError("任务不属于该节点或租约无效")
        if run["status"] in TERMINAL or run.get("lease_until", 0) < time.time():
            raise ValueError("任务租约已结束；不能提交过期结果")
        return run

    @staticmethod
    def copy_steps(run, incoming, final=False, media=()):
        if len(incoming) != len(run["steps"]):
            raise ValueError("步骤数量与验收配置不一致")
        for original, result in zip(run["steps"], incoming):
            status = result.get("status")
            if status not in STEP_STATES or (final and status in {"pending", "running"}):
                raise ValueError("无效的步骤状态")
            original.update(status=status, detail=str(result.get("detail", ""))[:8000], duration_ms=result.get("duration_ms"))
            image = result.get("screenshot")
            original["screenshot"] = image if image in media and str(image).endswith(".png") else None

    def progress(self, identifier, token, run_id, data):
        with self.store.lock:
            self.owned(identifier, token, run_id, data["lease"])
            def apply(run):
                self.copy_steps(run, data["steps"])
                run.update(status=data["status"], environment=data["environment"], lease_until=time.time()+LEASE_SECONDS)
            return self.store.update(run_id, apply)

    def receive(self, identifier, token, run_id, lease, source):
        with self.store.lock:
            self.owned(identifier, token, run_id, lease)
            directory = self.store.directory(run_id)
            with zipfile.ZipFile(source) as archive:
                infos = archive.infolist()
                if len(infos) > 100 or sum(i.file_size for i in infos) > 1024**3:
                    raise ValueError("结果包超过限制")
                names = set()
                for info in infos:
                    name = info.filename
                    if name in names or Path(name).name != name or "/" in name or "\\" in name or ":" in name or len(name) > 100:
                        raise ValueError("结果包包含非法或重复路径")
                    if Path(name).suffix not in {".png", ".mp4", ".log", ".json", ".md"} or info.is_dir():
                        raise ValueError("结果文件类型无效")
                    names.add(name)
                if "report.json" not in names or archive.getinfo("report.json").file_size > 2*1024*1024:
                    raise ValueError("结果包缺少有效 report.json")
                result = json.loads(archive.read("report.json"))
                if result.get("status") not in TERMINAL:
                    raise ValueError("结果必须是已结束状态")
                run = self.store.get(run_id)
                self.copy_steps(run, result.get("steps", []), final=True, media=names)
                statuses = [s["status"] for s in run["steps"]]
                if result["status"] == "passed" and (any(s != "passed" for s in statuses) or result.get("warnings") or "recording.mp4" not in names or any(not s["screenshot"] for s in run["steps"])):
                    raise ValueError("结果不能将未通过步骤或采集异常标为通过")
                for info in infos:
                    if info.filename not in {"report.json", "feedback.md"}:
                        with archive.open(info) as src, (directory / info.filename).open("wb") as out:
                            import shutil
                            shutil.copyfileobj(src, out)
                def finish(current):
                    self.copy_steps(current, result["steps"], final=True, media=names)
                    current.update(status="cancelled" if current["cancel_requested"] else result["status"], finished_at=now(),
                                   environment=result.get("environment", {}), warnings=result.get("warnings", []),
                                   error=result.get("error"), duration_seconds=result.get("duration_seconds"))
                self.store.update(run_id, finish)
            from .runner import write_reports
            write_reports(self.store, run_id)
        return self.store.get(run_id)

    def expire(self):
        expired = []
        with self.store.lock, self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for (body,) in db.execute("SELECT body FROM runs").fetchall():
                run = json.loads(body)
                if run["status"] in TERMINAL or not run.get("lease_until") or run["lease_until"] >= time.time():
                    continue
                run.update(status="interrupted", finished_at=now(), error="执行节点失联，租约已过期；结果未知，未自动重复安装。")
                for step in run["steps"]:
                    if step["status"] in {"pending", "running"}:
                        step.update(status="skipped", detail="节点失联，未获得有效结果")
                db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run), run["id"]))
                expired.append(run["id"])
        from .runner import write_reports
        for identifier in expired:
            write_reports(self.store, identifier)

    def campaign(self, name, runs):
        value = {"id": uuid.uuid4().hex, "name": name, "created_at": now(), "run_ids": [r["id"] for r in runs]}
        with self.store.lock, self.store.connect() as db:
            db.execute("INSERT INTO campaigns VALUES (?,?)", (value["id"], json.dumps(value)))
        for run in runs:
            self.store.update(run["id"], campaign_id=value["id"])
        return value

    def campaigns(self):
        with self.store.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM campaigns ORDER BY rowid DESC LIMIT 100")]

    def get_campaign(self, identifier):
        with self.store.connect() as db:
            row = db.execute("SELECT body FROM campaigns WHERE id=?", (identifier,)).fetchone()
        if not row:
            return None
        value = json.loads(row[0])
        value["runs"] = [self.store.get(i) for i in value["run_ids"]]
        value["complete"] = all(r["status"] in TERMINAL for r in value["runs"])
        value["passed"] = value["complete"] and all(r["status"] == "passed" for r in value["runs"])
        return value
