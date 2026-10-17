# Prooflane · Cross-platform desktop app testing

[简体中文](README.md) · **English**

[![Checks](https://github.com/xiao-zi-chen/new/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/xiao-zi-chen/new/actions/workflows/checks.yml)

Test native Windows, macOS and Linux builds with the same acceptance steps, then compare screenshots, recordings and logs.

Send an execution kit to someone with the required machine, or connect a persistent worker. Prooflane is a preview: **Windows samples have recorded GUI test results. The macOS and Linux adapters are implemented but still await testing on their target desktops.**

[Getting started](docs/getting-started.en.md) · [Delegate a test](docs/execution-strategy.en.md) · [Documentation](docs/README.en.md) · [Contributing](CONTRIBUTING.en.md)

![Test overview showing Windows results and macOS and Linux waiting for execution](docs/assets/overview.png)

This screenshot shows the current Chinese interface. Empty platforms have not run. Passing browser or protocol checks does not establish that a platform's GUI tests passed.

## Quick start

Requires Python 3.11+. Open PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/`. On Windows, click **创建示例任务** (Create sample tasks) to try the four-step Notes scenario. Building the Windows sample requires the local .NET Framework C# compiler. You can upload your own application without compiling the sample.

Keep the desktop signed in and unlocked during GUI tests. Installers modify the test environment; use a dedicated machine that can be restored.

For a controller on macOS or Linux, your first submission and startup help, see [Getting started](docs/getting-started.en.md).

## Execution options

| Option | Workflow | Results |
| --- | --- | --- |
| Standalone execution kit | Select a platform and task under **执行策略** (Execution strategy), then send the ZIP to a tester | The tester returns a receipt and evidence ZIP for review; the controller is not updated automatically |
| Connected worker | Start a worker in the target system's desktop session and connect it to the controller | The worker claims matching tasks and returns screenshots, recordings and reports |

A generic kit contains instructions and templates only. Selecting a specific task adds the execution tools; including the application build is optional. Testers provide or arrange their machines. Prooflane does not create or rent them.

Repository documentation and exported kits include Chinese and English instructions. The UI currently uses Chinese; English guides include the relevant button labels.

## Platform status

| Target | Build formats | Available evidence |
| --- | --- | --- |
| Windows | EXE, MSI, ZIP | Bundled samples have passed desktop interaction, installation, capture and reporting checks; this does not establish compatibility with every Windows app |
| macOS | ZIP containing an APP, DMG, PKG | Experimental adapter; no Mac GUI execution record yet |
| Linux | AppImage, ZIP, tar.gz | Experimental adapter requiring X11, AT-SPI and D-Bus; no Linux GUI execution record yet |

Wayland, Android and iOS are not supported. Control interactions depend on the application's accessibility interfaces. Custom rendering, special permissions and complex installers need separate validation. See [Worker setup](docs/multiplatform.en.md) and [Validation records](docs/validation.en.md).

## Documentation

- [Execution strategy](docs/execution-strategy.en.md): find testers, prepare inputs and collect results.
- [Evidence review](docs/handoff-acceptance.en.md): verify builds, environments, steps and conclusions.
- [Configuration](docs/configuration.en.md): data directories, environment variables, connections and backups.
- [API](docs/api.en.md): upload builds, create tasks and retrieve results.
- [Troubleshooting](docs/troubleshooting.en.md): waiting tasks, permissions, controls and capture problems.
- [Architecture](docs/architecture.en.md): modules, task lifecycle and trust boundaries.

## Development

The frontend uses plain HTML, CSS and JavaScript, with no build step. The backend uses FastAPI, Pydantic and SQLite.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_docs.py
```

See [Contributing](CONTRIBUTING.en.md) for submission guidelines and GUI checks. [CI](.github/workflows/checks.yml) runs code tests on three operating systems, documentation checks and frontend syntax checks. Results are available in [GitHub Actions](https://github.com/xiao-zi-chen/new/actions). Native desktop validation is recorded separately.

Report ordinary problems through repository Issues, with a minimal reproduction and environment details. For credential exposure, unauthorized access or data leaks, follow the [Security policy](SECURITY.en.md). Changes are recorded in the [Changelog](CHANGELOG.en.md).

## Scope and licensing

Prooflane currently targets local test environments managed by trusted operators. It does not provide public user authentication, tenant isolation, VM snapshot restoration or automatic data retention. Worker credentials and run directories are not a security sandbox.

No open-source license has been selected. Public source availability does not itself grant open-source rights to use, modify or redistribute it. The rights holder still needs to choose a license and add a `LICENSE` file before an open-source release.
