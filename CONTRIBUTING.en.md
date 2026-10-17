# Contributing

[简体中文](CONTRIBUTING.md) · **English**

Reproducible bug reports, documentation fixes and focused changes are welcome. For substantial design changes, describe the use case, current problem and expected behavior before implementing them.

The project is a preview and has no selected open-source license. Confirm contribution and future distribution terms with the maintainer before contributing. This document does not request a copyright assignment.

## Set up development

Use Python 3.11+ and Node.js 22+ for JavaScript syntax checks. Controller development does not require the macOS or Linux desktop dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Commands below use the virtual environment's `python`. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` directly; changing the global execution policy is unnecessary.

## Choose checks for your change

| Change | Minimum checks |
| --- | --- |
| Markdown, images or documentation links | Run `python scripts/check_docs.py` and inspect rendering; verify behavior when changing example commands |
| Python, APIs, package handling or scheduling | Run `python -m pytest -q`; add useful regression coverage for changed behavior |
| Frontend | Run the three syntax checks below and exercise affected pages at desktop and narrow widths |
| Desktop adapters, installation or capture | Run an actual application on the affected system and record the environment and evidence; mark unavailable platforms as unverified |
| Execution kits and their documentation | Export generic and task-bound kits and check contents and links; validate standalone execution when runtime behavior changes |

```bash
python -m pytest -q
python scripts/check_docs.py
node --check static/app.js
node --check static/workspace.js
node --check static/strategy.js
```

`pytest` uses temporary data directories and primarily checks models, APIs, archive boundaries, scheduling and exports. A Windows case also compiles the sample without running its GUI. Passing CI on several operating systems is not evidence of native GUI acceptance on those systems.

The [CI workflow](.github/workflows/checks.yml) runs code tests on Windows, macOS and Ubuntu with Python 3.11 / 3.12, plus documentation and JavaScript checks. Check the Actions result for the specific commit; the workflow file alone is not proof of success.

## GUI and browser checks

Start the local service and ensure the test desktop is free. Browser scripts use Playwright's Microsoft Edge channel and require Edge to be installed.

| Script | Prerequisites and effects |
| --- | --- |
| [e2e_windows.py](scripts/e2e_windows.py) | Windows desktop; creates tasks, runs and installs bundled samples |
| [browser_check.py](scripts/browser_check.py) | Running controller; submits and runs a Windows task when the Notes sample is available |
| [browser_workspace.py](scripts/browser_workspace.py) | Creates a three-platform sample by default; use `--existing-campaign` to reuse four-step results and `--keep-demo` to retain waiting tasks |
| [browser_multiplatform.py](scripts/browser_multiplatform.py) | Creates test tasks to check multi-platform forms and waiting states |
| [check_strategy_delivery.py](scripts/check_strategy_delivery.py) | Requires an existing four-step Windows demo and a waiting Linux task; exports and independently runs the Windows sample |
| [e2e_remote_agent.py](scripts/e2e_remote_agent.py) | Windows desktop and free port 8766; starts a temporary controller and HTTP worker and runs the sample |
| [msi_check.py](scripts/msi_check.py) | Windows and Python 3.11 / 3.12; builds, installs, checks and uninstalls an MSI sample |
| [capture_check.py](scripts/capture_check.py) | Idle Windows worker; checks capture with another window covering the application |

Refer to each script for its current prerequisites and outputs. Run GUI checks serially on a dedicated desktop. Copy or layout edits do not require rerunning installers.

## Code and documentation

- Keep the existing stack and directory structure. Explain why a new dependency is needed.
- Address a specific problem without unrelated formatting changes.
- Write user-facing text around actions, states and next steps. Avoid slogans and repeated assurances.
- Distinguish implemented, verified and planned work. Never invent test outcomes.
- Add new documents to the [documentation index](docs/README.en.md). Relative links must work from a source checkout.
- Maintain Chinese and English counterparts together. Explain any translation gap in the PR; CI checks for missing counterpart pages and language links.
- The three documents included in execution kits must remain usable without the rest of the repository.
- Do not commit `data/`, `agent-data/`, `artifacts/`, credentials or customer applications. Review public screenshots before placing them in `docs/assets/`.

## Submit a PR

Describe the original problem, resulting behavior, validation and remaining gaps. Include screenshots for UI changes, and update relevant documentation and the [Changelog](CHANGELOG.en.md) for behavior changes. State which checks were not run and why.

Use the [English bug form](.github/ISSUE_TEMPLATE/bug_report.en.yml) for ordinary defects. Feature suggestions should describe a real use case. For security problems, read [SECURITY](SECURITY.en.md) first. PRs and Issues may be written in either Chinese or English.
