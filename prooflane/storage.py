import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


TERMINAL = {"passed", "failed", "review", "cancelled", "interrupted"}


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS packages (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, body TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.root / "prooflane.db", timeout=15)

    def package(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT body FROM packages WHERE id=?", (identifier,)).fetchone()
            return json.loads(row[0]) if row else None

    def put_package(self, package):
        with self.connect() as db:
            db.execute("INSERT INTO packages VALUES (?, ?)", (package["id"], json.dumps(package)))

    def create(self, spec, package):
        identifier = uuid.uuid4().hex
        run = {
            "id": identifier, "name": spec["name"], "status": "queued",
            "platform": spec.get("platform", "windows"), "architecture": spec.get("architecture", "any"),
            "worker_id": None, "campaign_id": None,
            "created_at": now(), "started_at": None, "finished_at": None,
            "spec": spec, "package": {k: v for k, v in package.items() if k != "path"},
            "steps": [{**step, "status": "pending", "detail": "", "screenshot": None,
                       "duration_ms": None} for step in spec["steps"]],
            "artifacts": [], "warnings": [], "error": None, "environment": {},
            "cancel_requested": False, "duration_seconds": None,
        }
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?)", (identifier, json.dumps(run)))
        self.directory(identifier).mkdir(parents=True)
        return run

    def directory(self, identifier):
        if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
            raise ValueError("无效的任务 ID")
        return self.root / "runs" / identifier

    def get(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (identifier,)).fetchone()
            return json.loads(row[0]) if row else None

    def update(self, identifier, mutate=None, **fields):
        with self.lock, self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = json.loads(db.execute("SELECT body FROM runs WHERE id=?", (identifier,)).fetchone()[0])
            run.update(fields)
            if mutate:
                mutate(run)
            db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run), identifier))
            return run

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT body FROM runs ORDER BY rowid DESC LIMIT 200")]

    def recover(self):
        with self.lock, self.connect() as db:
            rows = db.execute("SELECT id, body FROM runs").fetchall()
            for identifier, body in rows:
                run = json.loads(body)
                if run["status"] in TERMINAL or run["status"] in {"queued", "waiting_worker"} or run.get("worker_id") not in (None, "local"):
                    continue
                run.update(status="interrupted", finished_at=now(), error="执行器已重启，本次结果不完整，请重新运行。")
                for step in run["steps"]:
                    if step["status"] in ("pending", "running"):
                        step["status"] = "skipped"
                db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run), identifier))
