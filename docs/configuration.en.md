# Configuration

[简体中文](configuration.md) · **English**

Set configuration in the service process's environment. The default listener is `127.0.0.1:8765` for local or private access.

## Controller

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROOFLANE_DATA` | `data/` under the project root | SQLite, builds, execution evidence and registration credentials |
| `PROOFLANE_LOCAL_WORKER` | `1` | Only `1` enables the local worker; set `0` to schedule other workers only |
| `PROOFLANE_AGENT_TOKEN` | Contents of `agent-token` in the data directory | Overrides the registration credential used by this service process; does not update the file |
| `PROOFLANE_ALLOWED_HOSTS` | No additional hosts | Comma-separated extra Host values; `127.0.0.1`, `localhost` and `testserver` are already allowed |

The Host allowlist validates the requested host name; it is not access control or account authentication. Uvicorn's `--host` and `--port` set the listener.

Controller-only example on Windows:

```powershell
$env:PROOFLANE_LOCAL_WORKER = '0'
$env:PROOFLANE_DATA = 'D:\ProoflaneData'
.\.venv\Scripts\python.exe -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

These variables affect the current shell and its children. Use one Uvicorn process. With a local worker enabled, avoid `--workers` and automatic reload, which can compete for the desktop, start duplicate workers or interrupt tasks.

## Data locations

| Path | Contents |
| --- | --- |
| `data/prooflane.db` | Build metadata, tasks, workers and platform comparisons |
| `data/packages/` | Original uploaded builds |
| `data/runs/<id>/` | A run's working directory, logs, media and reports |
| `data/agent-token` | Registration credential generated on first startup |
| `agent-data/` | A connected worker's cache and execution data |
| `results/<id>/` | A standalone run's receipt, evidence ZIP and internal execution directory |

With `PROOFLANE_DATA`, controller paths move under that directory. Connected workers use `--data`; standalone execution uses `--output`. Neither should share the controller's data directory.

There is no automatic retention cleanup, database migration command or online backup API. For a complete backup, finish tasks, stop the service and copy the data directory while preserving path relationships. The database contains build paths, so moving to another location requires additional verification. Restore with matching code and dependencies; a database file alone is not a complete backup.

## Worker arguments

```bash
python -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name test-node
```

| Argument | Default or requirement |
| --- | --- |
| `--server` | `http://127.0.0.1:8765`; may point to an SSH tunnel |
| `--token-file` | Required UTF-8 file containing the registration credential |
| `--data` | `agent-data` in the current directory |
| `--name` | Current host name; prefer a test-machine name without personal information |
| `--once` | Exit after one claim attempt or one task; useful for debugging |

Registration exchanges the enrollment credential for a worker-specific credential. Changing the enrollment credential does not revoke existing worker credentials; there is no web revocation interface yet. If exposure is suspected, stop the service and affected workers, then inspect data and connection records. See [Security](../SECURITY.en.md).

The Linux Xvfb helper uses `PROOFLANE_LINUX_NODE_ROOT` for its virtual environment and worker data, defaulting to `~/.local/share/prooflane-linux`. It does not install system packages. See [Worker setup](multiplatform.en.md) for prerequisites.

## Standalone arguments

```bash
python -m prooflane.handoff --manifest scenario.json --package "path/to/application" --check
```

`--manifest` defaults to `scenario.json`, `--package` is required, and `--output` defaults to `results`. `--check` validates the task, build, system, architecture and desktop readiness without launching the application.

Remove `--check` to execute. Exit code `0` means automated checks passed, `2` means review is required, and `1` means execution did not complete successfully. The receipt's `review_status` always starts as `pending`. See [Evidence review](handoff-acceptance.en.md) for return requirements.

Back to [Documentation](README.en.md).
