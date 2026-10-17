# Native worker setup

[简体中文](multiplatform.md) · **English**

## Controller and workers

This guide connects persistent workers. For one-off collaboration, prefer a [standalone kit](execution-strategy.en.md): the tester runs it locally and returns evidence without requiring the controller to stay online or sharing worker credentials.

The controller stores native builds, shared scenarios, workers, leases and evidence. A worker runs its system's build in an interactive desktop session. Windows execution does not count as macOS testing, and results are not copied between platforms.

The trusted-operator mode listens on localhost by default. Use the controller's browser locally or access it through private SSH forwarding. Multiple operating systems can connect to one controller. Run only one worker per interactive desktop; do not let a local worker and a remote agent compete for the same desktop.

## 1. Prepare the controller

Install `requirements.txt`, then start:

```bash
python -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

Set `PROOFLANE_LOCAL_WORKER=0` for controller-only mode. By default, first startup creates `data/agent-token`. Transfer its contents through a trusted channel into `node.token` on the test machine. If `PROOFLANE_AGENT_TOKEN` is set, use that value instead; the file is not updated automatically. Registered workers receive separate credentials. See [Configuration](configuration.en.md).

## 2. Prepare the target machine

### Windows: tested with samples

Use Python 3.11+, install `requirements.txt`, and start from a signed-in, unlocked desktop. UI Automation locates controls by name or Automation ID; PrintWindow captures the application's contents for screenshots and recordings. EXE, MSI and ZIP samples have execution records.

### macOS: experimental, awaiting native GUI testing

Install Python 3.11+ on a Mac or properly licensed macOS test environment, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-macos.txt
```

Grant Accessibility and Screen Recording permission in System Settings to the terminal / Python process that actually launches the worker, then restart it. A worker without required permissions is not ready.

- A ZIP should contain one `.app`, or specify its internal path. Links inside ZIPs are rejected; prefer DMG for applications with Framework symlinks.
- A DMG is mounted read-only. Its single APP is copied into the run directory, launched using the executable in Info.plist, and the disk image is detached afterward.
- PKG uses the system installer and requires the full installed APP / executable path. The worker does not elevate privileges, enter passwords or disable Gatekeeper. Installers requiring additional authorization fail with an installation log.
- Names come from AXTitle / AXDescription, IDs from AXIdentifier, and types include AXButton and AXTextField. Clicking uses AXPress; input uses AXValue.
- Capture uses the target process's window ID and requires Screen Recording permission. Process output and matching DiagnosticReports are returned with the report.

These integrations have not been tested on a real Mac yet. Sandboxing, signing, dialogs, LaunchServices and specific GUI frameworks may require further work.

### Linux: experimental, awaiting native GUI testing

Requires Python 3.11+, X11, AT-SPI / PyGObject, D-Bus and XComposite. A Debian / Ubuntu example, to be run by the test machine's operator:

```bash
sudo apt update
sudo apt install python3-venv python3-gi gir1.2-atspi-2.0 gir1.2-gtk-3.0 at-spi2-core libatk-adaptor dbus-x11 xvfb xauth
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-linux.txt
```

Start the worker from a signed-in X11 desktop, preserving DISPLAY and DBUS_SESSION_BUS_ADDRESS. Wayland is unsupported. An operator can provide a dedicated Xvfb / D-Bus session, but it does not isolate the operating system or files.

- Accepted formats are AppImage, ZIP and tar.gz. Specify the main Linux program's relative path for archives.
- ZIP and tar.gz extraction rejects escaping paths and links, preserves ordinary executable permissions and does not restore setuid privileges.
- The worker does not install customer system packages using apt, dpkg or rpm. AppImage depends on host FUSE and runtime libraries; missing dependencies appear in process logs.
- Control names come from AT-SPI name, IDs from the application's accessible ID when available, and types from role names.
- Capture uses XComposite window pixmaps without falling back to the entire user desktop. Compatibility with Wayland, custom rendering or inaccessible controls is not promised.
- Reports include stdout / stderr, exit codes and coredumpctl information when available. Missing crash capture capability is recorded as an evidence limitation.

Without an existing desktop, install the dependencies above and use the Xvfb helper:

```bash
bash scripts/start-linux-x11.sh --server http://127.0.0.1:8765 --token-file node.token --name linux-xvfb
```

The helper creates an X11 / D-Bus session and uses a virtual environment and worker data under the user's directory. It does not install system packages. It currently has Bash syntax validation, not a Linux GUI execution record. Label WSL2 / Xvfb results with their actual environment.

## 3. Connect to the controller

For private forwarding, open another terminal on the target machine:

```bash
ssh -N -L 8765:127.0.0.1:8765 user@controller-host
```

Then start the worker from the target machine's interactive desktop:

```bash
python -m prooflane.agent --server http://127.0.0.1:8765 --token-file node.token --name my-native-node
```

Do not launch GUI workers from an SSH background session; SSH provides the connection only. Worker data defaults to `agent-data/`, configurable with `--data`. Do not share one data directory across machines or controllers. `--once` performs one claim attempt or one task for debugging.

Registration, matching, download, execution and upload require valid credentials. Each renewal grants a 45-second lease; heartbeats cover download and upload too. Disconnection beyond the lease interrupts the task without automatically reinstalling. Local evidence remains on the worker; stale uploads cannot overwrite controller state. Restarting the agent registers a new worker ID, leaving the old one offline.

## 4. Share a scenario and adjust platform differences

On a Windows controller, choose **创建示例任务** from **测试概览** to submit the three-platform Notes sample. Windows uses a compiled WinForms EXE. The macOS APP ZIP contains a PyObjC / AppKit Python entry point, and Linux contains a GTK 3 Python entry point. Both use `#!/usr/bin/env python3`, so activate the platform virtual environment before starting the agent. Linux GTK 3 is provided by `gir1.2-gtk-3.0`. Neither sample has native execution evidence on its target system yet.

The four default steps open the window, enter a note, save and check the result text. Linux uses AT-SPI control names; Windows and macOS use control IDs. Targets without ready workers remain waiting. A new worker automatically claims matching tasks. Images, recordings and reports show only returned evidence; selecting a comparison step shows that step across targets.

Enter each additional platform's window title and application path in the submission form. For example, if step 2 uses `automation_id=saveButton` on Windows but the title `Save` on macOS, use this override:

```json
{"2": {"automation_id": "", "target": "Save", "control_type": "AXButton"}}
```

Allowed overrides are `target`, `automation_id`, `control_type`, `value` and `timeout`. Indexes start at 1; titles and actions remain shared. Waiting, skipped and review states are not counted as passes.

## Evidence boundaries

- A controller and separate Windows HTTP worker have completed actual GUI execution on one physical Windows machine. This does not establish cross-machine or cross-OS desktop testing.
- Automated tests cover platform / architecture selection, authentication, competing claims, lease expiry and comparisons.
- macOS / Linux have implementation and code / protocol checks, but no native desktop execution results.
- Android / iOS, VM orchestration, snapshot restoration, tenant isolation and public user accounts are not implemented.
- Do not run unknown customer builds on a daily-use machine containing personal data. Use dedicated, restorable native test environments.

Back to [Documentation](README.en.md).
