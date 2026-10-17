# Validation records

[简体中文](validation.md) · **English**

Record date: 2026-10-17. Existing desktop evidence comes from Windows 11 (10.0.26200), AMD64, Python 3.11.5 and Microsoft Edge. All tested applications were bundled samples, not customer software.

This page distinguishes code tests, browser checks and native GUI acceptance. Raw outputs are stored in the developer's local `artifacts/` directory, not distributed with the source. Paths below identify records and reproduction entry points; readers are not expected to possess those files.

## Current conclusions

| Scope | Evidence available | What it does not establish |
| --- | --- | --- |
| Windows desktop | Bundled sample interaction, installation, screenshots, recordings and reports | Compatibility with every app, system version, DPI or GUI framework |
| Windows connected worker | A temporary controller and real HTTP worker on one machine completed claims, execution, renewal and uploads | A deployment across physical machines |
| Windows standalone execution | An exported kit completed four steps outside the project directory and produced a receipt pending review | Dependency installation on a third party's clean machine |
| macOS / Linux | Adapter code, sample packages, routing and waiting-state checks | Native GUI interaction or capture on those systems |
| Frontend | Image enlargement, video playback, feedback copy, kit download and responsive layouts | That the browser's OS is the OS where the application ran |

## Code and API checks

Run `python -m pytest -q`. The local run after the initial documentation cleanup had **31 passing tests**. Use current command output for later changes rather than treating a historical count as today's result.

Coverage includes input constraints, archive boundaries, platform / architecture matching, atomic claims, expired leases, authentication, cancellation, result provenance, aligned scenarios, export allowlists, build hashes and preflight without application launch.

The first [GitHub Actions run](https://github.com/xiao-zi-chen/Prooflane/actions/runs/39039156800), for commit `ec1256f`, passed all seven jobs: six combinations of Windows, macOS, Ubuntu and Python 3.11 / 3.12, plus documentation / JavaScript checks. Hosted runner code tests are not native GUI acceptance.

| Runner | Python 3.11 | Python 3.12 |
| --- | --- | --- |
| Windows | 31 passed | 31 passed |
| macOS | 30 passed, 1 skipped | 30 passed, 1 skipped |
| Ubuntu | 30 passed, 1 skipped | 30 passed, 1 skipped |

Non-Windows runners skipped the sample-build case requiring the Windows C# compiler. A skipped test is not GUI validation success.

A clean copy exported from committed source also passed documentation checks, controller startup, health and OpenAPI requests, and all three generic kit exports. It reused local Python dependencies and does not count as installation on a fresh machine.

## Existing desktop checks

| Scenario | Observation | Reproduction / local record |
| --- | --- | --- |
| EXE, ZIP and silent EXE installation | Samples completed steps and produced reports | `scripts/e2e_windows.py`; `artifacts/e2e-results.json` |
| Wrong text, abnormal exit and cancellation | Failures and cancellation retained; later steps skipped; exit codes recorded | Same as above |
| MSI | Sample installed, tested and uninstalled | `scripts/msi_check.py`; `artifacts/msi-result.json` |
| Capture under an overlapping window | The covering window did not appear in the application capture | `scripts/capture_check.py` |
| HTTP worker | A worker completed the task with the temporary controller's local executor disabled | `scripts/e2e_remote_agent.py`; `artifacts/remote-e2e.json` |
| Standalone kit | Exported modules ran four Windows steps without changing the source task | `scripts/check_strategy_delivery.py`; `artifacts/strategy-validation.json` |

An early region-capture implementation included foreground windows. It was replaced with capture by target window handle and the affected samples rerun. Those early unreliable images must not be used as current evidence.

## Browser checks

The recent UI revision reused Windows results without creating native runs. It checked image provenance, step selection, enlargement, playback during polling, feedback copy, generic and task-bound kits, invitation copy and form editing.

Eight pages were checked for horizontal overflow at widths of 320, 390, 768, 1024 and 1440 pixels, plus the tablet sidebar. No JavaScript or HTTP errors were reported. Records are in `artifacts/ui-refinement/result.json`; the workspace regression entry point is `scripts/browser_workspace.py`.

The public UI screenshot is `docs/assets/overview.png`. Its macOS / Linux targets are waiting. It illustrates the product rather than adding platform execution evidence.

## Outstanding coverage

- Actual macOS / Linux desktop interaction, window capture and installation.
- Third-party applications, Electron / Qt / custom rendering, and a full OS version, DPI and architecture matrix.
- Connections across physical machines, real customer pilots and actual paid demand.
- All COM, GPU or system installer deadlocks; current cancellation and timeout handling does not cover every failure mode.
- Deliberately triggered native crash dumps; a sample exiting with code 42 does not validate system crash collection.
- Tenant isolation, public accounts, VM lifecycle and automatic retention, which are not implemented.

## Add a validation record

Record the commit, Python and dependency versions, system / architecture / session, build hash, reproduction commands, expected and observed behavior, evidence location and untested scope. Preserve failures alongside passes.

See [Contributing](../CONTRIBUTING.en.md) for prerequisites and effects, and apply [Evidence review](handoff-acceptance.en.md) to third-party results.

Back to [Documentation](README.en.md).
