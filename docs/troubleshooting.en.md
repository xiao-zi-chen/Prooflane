# Troubleshooting

[简体中文](troubleshooting.md) · **English**

Start with the failed step's original error, execution logs and control inventory. Use the [issue record](issue-template.en.md) and keep the first failure's evidence. Do not change expected values merely to hide a failure.

## Controller startup

| Symptom | Check and action |
| --- | --- |
| Missing module | Use the project's virtual environment and install the appropriate requirements file |
| Port 8765 is occupied | Check for an existing service; a second controller needs a separate port and data directory |
| Data directory already has a worker | Stop duplicate processes; avoid multiple Uvicorn workers or agents sharing one desktop |
| Windows sample compilation fails | Check the .NET Framework C# compiler; uploading your own application does not require sample compilation |
| `Invalid host header` | Use localhost or an explicitly allowed Host; see [Configuration](configuration.en.md) |

## A task keeps waiting for a worker

Open **执行节点** (Workers) and check the platform, architecture and readiness.

1. No worker for the platform: export a kit for a tester or have them connect a worker.
2. Online but not ready: read the reported desktop, dependency or permission error.
3. Architecture mismatch: an `arm64` task will not go to an `x86_64` worker. Do not switch to `any` just to bypass matching.
4. Worker occupied: wait for its current task and confirm no other process is using the desktop.

Recheck readiness after changing the environment. Being online does not mean the task has executed.

## macOS permissions or launch failures

Grant Accessibility and Screen Recording permission to the actual terminal / Python process, then restart it. Start from a signed-in graphical desktop; an SSH shell does not replace desktop authorization.

APP ZIPs with symbolic links are rejected during extraction. Use DMG for applications with Framework symlinks. Preserve original PKG installation path, permission, signing or Gatekeeper errors; the executor does not elevate privileges or disable system protections automatically.

The macOS adapter still awaits native testing. Include architecture, OS version, application framework and permission state in reports.

## Linux is not ready

Requires X11, AT-SPI / PyGObject, D-Bus and XComposite. Wayland is unsupported. See [Worker setup](multiplatform.en.md) for dependencies and Xvfb.

- Cannot import `gi`: check distribution packages and the `--system-site-packages` virtual environment.
- Cannot find controls: check AT-SPI, the D-Bus session and the application's accessibility support.
- AppImage fails: retain FUSE or library errors and initially classify them as environment issues.
- WSL2 / Xvfb: identify both in the receipt; they do not establish Wayland or physical GPU coverage.

## Window or control not found

Check the window title, `target`, `automation_id`, control type and step order. Inspect `controls.json` and confirm it belongs to the application in this run. Control IDs and types can differ by system and need platform-specific configuration.

If manual interaction works but automation fails, initially classify it as a possible automation issue. Custom-rendered or inaccessible controls may require a manual supplement.

## Blank screenshots or missing recordings

Inspect capture errors and file completeness, permissions, window state and interruptions. Windows captures a specific window, Linux requires XComposite, and macOS needs Screen Recording permission.

Blank screenshots or missing recordings are not passing evidence. Keep logs and available files, then record the gap under the [review requirements](handoff-acceptance.en.md).

## Standalone kit problems

| Symptom | Action |
| --- | --- |
| Generic-strategy error or missing runtime | Select a specific task under **执行策略** and download again |
| SHA-256 mismatch | Obtain the original build, or create a new task and re-export; do not simply edit the manifest hash |
| Wrong system or architecture | Use an environment matching the task |
| Preflight fails with no result directory | Return the terminal error and environment; preflight does not install or launch the app |
| Run finishes but controller still waits | The result is standalone and needs review; there is no automatic import API |

## Worker connection or upload failures

For `401`, check enrollment or worker-specific credentials. `403` may also indicate wrong task ownership. Confirm the tunnel address, port and credentials belong to the same controller.

A disconnect beyond the lease interrupts the task. Old results cannot overwrite new state. Evidence may remain locally; inspect it before deciding to rerun. Confirm application state before repeating an installation.

Back to [Documentation](README.en.md).
