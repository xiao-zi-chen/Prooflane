"""Run a bound handoff on the recipient's own machine, without a central server."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from .models import RunSpec
from .platforms import capability, current_platform, current_architecture, validate_package
from .runner import Worker
from .storage import Store, now


def prepare(manifest_path, package_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != 1 or not manifest.get("spec") or not manifest.get("package"):
        raise ValueError("这是通用策略或不支持的交付包；请先选择具体任务并重新导出")
    spec = RunSpec.model_validate({**manifest["spec"], "package_id": uuid.uuid4().hex})
    if manifest.get("platform") != spec.platform or current_platform() != spec.platform:
        raise ValueError("请在交付包指定的目标操作系统执行，不能用另一平台代替")
    if spec.architecture not in ("any", current_architecture()):
        raise ValueError("当前机器架构与任务不匹配")
    path = Path(package_path).resolve()
    if not path.is_file():
        raise ValueError("找不到应用构建文件")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != manifest["package"]["sha256"]:
        raise ValueError("应用构建 SHA-256 与交付任务不一致；请取得原构建")
    validate_package(spec, {"name": path.name})
    environment = capability()
    if not environment["ready"]:
        raise ValueError(environment["detail"])
    return manifest, spec, path, digest, environment


def execute(manifest_path, package_path, output="results", check=False):
    manifest, spec, package_path, digest, environment = prepare(manifest_path, package_path)
    if check:
        print(json.dumps({"preflight": "ready", "platform": spec.platform, "architecture": current_architecture(),
                          "package_sha256": digest, "detail": environment["detail"]}, ensure_ascii=False))
        return 0
    # Each invocation owns a new store, so interruption cannot overwrite earlier evidence.
    destination = Path(output).resolve() / uuid.uuid4().hex
    store = Store(destination / "execution")
    copied = store.root / "packages" / package_path.name
    copied.parent.mkdir(parents=True)
    shutil.copyfile(package_path, copied)
    package = {"id": spec.package_id, "name": package_path.name, "path": str(copied),
               "size": copied.stat().st_size, "sha256": digest}
    store.put_package(package)
    run = store.create(spec.model_dump(), package)
    worker = Worker(store)
    try:
        worker.dispatch(run["id"])
    except KeyboardInterrupt:
        worker.abort(run["id"], "cancelled", "执行者中止了独立验收，证据可能不完整")
    except Exception as exc:
        worker.abort(run["id"], "failed", f"独立执行器异常：{exc}")
    result = store.get(run["id"])
    evidence = destination / "evidence.zip"
    shutil.copyfile(store.directory(run["id"]) / "bundle.zip", evidence)
    with evidence.open("rb") as stream:
        evidence_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = {"schema_version": 1, "source_run_id": manifest.get("source_run_id"),
               "execution_run_id": run["id"], "platform": spec.platform, "architecture": current_architecture(),
               "package_sha256": digest, "execution_status": result["status"], "review_status": "pending",
               "evidence_file": "evidence.zip", "evidence_sha256": evidence_hash, "created_at": now(),
               "environment": result["environment"], "display_session": {
                   "x11_display": os.environ.get("DISPLAY", ""),
                   "wsl": bool(os.environ.get("WSL_DISTRO_NAME"))},
               "error": result["error"], "note": "执行者本机结果；需复核构建、环境与证据，不自动更新源任务。"}
    (destination / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Result: {result['status']}\nReturn directory: {destination}", flush=True)
    return 0 if result["status"] == "passed" else 2 if result["status"] == "review" else 1


def main():
    parser = argparse.ArgumentParser(description="Run a Prooflane handoff on this native desktop")
    parser.add_argument("--manifest", default="scenario.json")
    parser.add_argument("--package", required=True)
    parser.add_argument("--output", default="results")
    parser.add_argument("--check", action="store_true", help="Validate platform, package hash and desktop readiness without launching")
    args = parser.parse_args()
    try:
        return execute(args.manifest, args.package, args.output, args.check)
    except (ValueError, OSError, KeyError) as exc:
        print(f"Cannot execute: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
