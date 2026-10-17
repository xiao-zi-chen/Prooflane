# API

[简体中文](api.md) · **English**

The default base URL is `http://127.0.0.1:8765`. `GET /openapi.json` describes request and response schemas. Swagger UI and ReDoc pages are disabled.

## Request conventions

Mutating operator API requests require `X-Prooflane-Client: web`. A browser's `Origin`, when present, must match the request Host. This is protection against cross-site calls, not user authentication.

Worker endpoints use Bearer credentials: the registration credential for enrollment, then the worker-specific credential returned by registration. See [Worker setup](multiplatform.en.md).

| Status | Common meaning |
| --- | --- |
| `400` | Request problems such as a Host outside the allowlist |
| `401` / `403` | Missing credentials or client marker, or a worker does not own the task |
| `404` | Task, build or evidence not found |
| `409` | Current task state does not permit the operation |
| `413` | Upload limit exceeded |
| `422` | Invalid input, build format, platform or scenario |

Read `detail` in the JSON error response. The endpoint's actual response is authoritative.

## Upload a build and create a task

This example uses the runtime dependency `httpx`. Replace `path/to/Notes.exe` with an actual Windows build. A connected worker may execute the application as soon as submission succeeds.

```python
import json
from pathlib import Path

import httpx

package_path = Path("path/to/Notes.exe")
spec = json.loads(Path("examples/run-spec.json").read_text(encoding="utf-8"))

with httpx.Client(
    base_url="http://127.0.0.1:8765",
    headers={"X-Prooflane-Client": "web"},
    timeout=120,
) as client:
    with package_path.open("rb") as stream:
        response = client.post(
            "/api/packages", files={"file": (package_path.name, stream)}
        )
    response.raise_for_status()
    spec["package_id"] = response.json()["id"]
    response = client.post("/api/runs", json=spec)
    response.raise_for_status()
    print(response.json()["id"])
```

The scenario targets the Notes sample's controls and window title. Adjust those fields when using another application, not just the file path. Task titles in the example are Chinese; they are author-supplied labels. Locators and assertion values must match the actual application regardless of documentation language.

## Task fields

| Field | Requirement |
| --- | --- |
| `platform` | `windows`, `macos` or `linux`; defaults to `windows` |
| `architecture` | `any`, `x86_64` or `arm64`; defaults to `any` |
| `package_id` | The 32-character hexadecimal ID returned by upload |
| `mode` | `portable` or `installer` |
| `app_path` | Main executable's relative path inside an archive, or its full installed path |
| `install_args` / `app_args` | Arrays of strings, not a shell command |
| `window_title` | Required main window title |
| `steps` | 3–5 steps; constraints are defined in [models.py](../prooflane/models.py) |

Actions are `wait_window`, `click`, `type_text`, `assert_text` and `screenshot`. Clicking and typing require `target` or `automation_id`; text assertions require a nonempty `value`. Step `timeout` ranges from 2 to 60 seconds, defaulting to 15.

A campaign contains a `name` and 2–3 `targets`, each a complete task specification. Step titles and actions must align; a platform / architecture combination cannot appear twice.

## Common endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Service and local worker status |
| `GET /api/platforms` | Platform capabilities and workers |
| `POST /api/packages` | Multipart upload; returns ID and SHA-256 |
| `POST /api/runs` | Create a run |
| `GET /api/runs` | Recent runs |
| `GET /api/runs/{identifier}` | Task, steps and evidence index |
| `POST /api/runs/{identifier}/cancel` | Request cancellation |
| `POST /api/runs/{identifier}/retry` | Create a new run using the original build and scenario |
| `POST /api/runs/{identifier}/review` | Submit `step_index`, `decision` and `note`; indexes start at 0 |
| `GET /api/runs/{identifier}/bundle` | Download the evidence ZIP |
| `GET /api/runs/{identifier}/artifacts/{filename}` | Read an evidence file |
| `POST /api/campaigns` | Create a platform comparison |
| `GET /api/campaigns` | List comparisons |
| `GET /api/campaigns/{identifier}` | Comparison details |
| `POST /api/demo` | Create a Windows sample task |
| `POST /api/demo/campaign` | Build native samples and create a comparison; requires the Windows sample compiler |
| `GET /api/strategies` | Platform execution plans |
| `GET /api/strategies/{kind}/kit` | Download a generic or task-bound kit |
| `GET /api/strategies/{kind}/invitation` | Get invitation text; no message is sent |

Kit and invitation endpoints accept `run_id`. Kits also accept `include_package=true` to include the original build, but only with a specific task. `kind` is one of the three platform identifiers. ZIP exports contain both Chinese and English documents; the existing invitation endpoint returns Chinese, with an English draft available inside the kit.

## Results and compatibility

A run's `status` describes execution, not worker availability. For campaigns, inspect `complete`, `passed` and each target's results. Completion does not necessarily mean success.

The API evolves with the preview and has no stable-version compatibility guarantee. Preserve errors and consult the current OpenAPI schema. Standalone receipt `schema_version` is currently `1`; it is a separate execution record and must not be written directly into the controller database.

Back to [Documentation](README.en.md).
