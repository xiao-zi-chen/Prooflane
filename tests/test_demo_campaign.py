import ast
import hashlib
import os
import plistlib
import zipfile

import pytest
from fastapi.testclient import TestClient

from prooflane.app import create_app
from prooflane.demo import native_demo_package
from prooflane.runner import extract_package
from prooflane.storage import Store


@pytest.mark.parametrize("kind", ["macos", "linux"])
def test_native_samples_extract_to_real_source_entrypoints(tmp_path, kind):
    store = Store(tmp_path / "data")
    package = native_demo_package(store, kind)
    with zipfile.ZipFile(package["path"]) as archive:
        if kind == "macos":
            info = plistlib.loads(archive.read("ProoflaneNotes.app/Contents/Info.plist"))
            executable = "ProoflaneNotes.app/Contents/MacOS/" + info["CFBundleExecutable"]
        else:
            executable = "ProoflaneNotes"
        source = archive.read(executable)
        assert source.startswith(b"#!/usr/bin/env python3\n")
        ast.parse(source)
        assert b"Saved: " in source
        assert archive.getinfo(executable).external_attr >> 16 & 0o100
    extract_package(package["path"], tmp_path / "extracted")
    assert (tmp_path / "extracted" / executable).read_bytes() == source


@pytest.mark.skipif(os.name != "nt", reason="The built-in Windows sample needs the Windows C# compiler")
def test_demo_campaign_routes_three_distinct_packages_without_fabricated_results(tmp_path):
    with TestClient(create_app(tmp_path, start_worker=False)) as client:
        headers = {"X-Prooflane-Client": "web"}
        assert client.post("/api/demo/campaign").status_code == 403
        created = client.post("/api/demo/campaign", headers=headers)
        assert created.status_code == 201, created.text
        campaign = client.get("/api/campaigns/" + created.json()["id"]).json()
        runs = campaign["runs"]
        assert [r["platform"] for r in runs] == ["windows", "macos", "linux"]
        assert len({r["package"]["sha256"] for r in runs}) == 3
        assert not campaign["passed"] and not campaign["complete"]
        for run in runs:
            assert run["status"] == "waiting_worker"
            assert not run["artifacts"] and not run["environment"]
            assert all(s["status"] == "pending" and not s.get("screenshot") for s in run["steps"])
            assert [(s["title"], s["action"]) for s in run["steps"]] == [(s["title"], s["action"]) for s in runs[0]["steps"]]
            package = client.app.state.store.package(run["spec"]["package_id"])
            with open(package["path"], "rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == package["sha256"]
