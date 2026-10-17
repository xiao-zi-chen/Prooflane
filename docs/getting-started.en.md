# Getting started

[简体中文](getting-started.md) · **English**

The controller organizes tasks; a worker runs the application on its target system. You can also export a task for a tester to run independently.

## Install the controller

Requires Python 3.11+. Download or check out the complete project and run commands in the directory containing `requirements.txt`.

### Windows

In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

The local worker is enabled by default. It can claim Windows tasks when the desktop is signed in and unlocked.

Alternatively, run `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1`. The script creates the virtual environment, installs dependencies and starts the service.

### macOS / Linux: controller only

These commands disable the local GUI worker. Use this mode to organize tasks or export kits for other testers:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PROOFLANE_LOCAL_WORKER=0 python -m uvicorn prooflane.app:app --host 127.0.0.1 --port 8765
```

Running applications also requires platform dependencies and permissions; see [Worker setup](multiplatform.en.md). The macOS / Linux desktop adapters still await native GUI testing. Starting the controller does not validate GUI execution.

### Confirm startup

Open `http://127.0.0.1:8765/`. You should see **测试概览** (Test overview). `GET /api/health` returns service and worker status. The first startup creates a data directory and registration credential; see [Configuration](configuration.en.md). For startup failures, see [Troubleshooting](troubleshooting.en.md).

## Run the sample

On a Windows controller, click **创建示例任务** (Create sample tasks). This prepares three Notes builds and submits four shared steps: wait for the window, enter a note, save it and check the result text.

The Windows sample needs the .NET Framework C# compiler. The macOS sample uses PyObjC / AppKit and the Linux sample uses GTK 3. Those two require their target machines and dependencies; they do not execute on Windows.

- Platforms with a matching worker begin running and return screenshots, recordings and reports.
- Platforms without a worker remain in **等待节点** (Waiting for worker), with no execution screenshots.
- Select steps, enlarge images or switch to recordings. **平台对照** (Platform comparison) shows results for each step and platform.

## Submit your application

1. Open **发起测试** (New test) and select the platform and architecture.
2. Upload a build for that system, up to 300 MiB per file. Preserve the application directory structure inside archives.
3. Set the main window title and application path. Installer mode needs the full installed program path; Windows installers also require silent arguments.
4. Define 3–5 acceptance steps with control names or IDs and expected text. Screenshot acceptance steps require human review.
5. For comparison, click **添加另一个平台** (Add another platform). Step titles and actions stay aligned; locators and expected text may differ by platform.
6. Click **开始测试** (Start test) and inspect the task status.

See the [API](api.en.md) and [JSON example](../examples/run-spec.json) for step fields. Replace the example's all-zero `package_id` with the ID returned by the upload endpoint.

## Have another tester run it

Click **导出执行包** (Export execution kit) on a waiting platform, or open **执行策略** (Execution strategy). Select a specific task before downloading. To bundle the build, select **将应用文件一起放入 ZIP** (Include the application file in the ZIP).

The tester follows the kit's README for preflight and execution, then returns `receipt.json` and `evidence.zip`. No controller connection is needed. Kits include Chinese and English instructions, review forms and invitation drafts. See [Execution strategy](execution-strategy.en.md) and [Evidence review](handoff-acceptance.en.md).

Standalone results do not import automatically. For ongoing task claims and uploads, [connect a worker](multiplatform.en.md).

## Understand results

| UI status | Meaning |
| --- | --- |
| 等待节点 / Waiting for worker | The target system has not executed the task |
| 通过 / Passed | Configured checks passed for this build and scenario |
| 待复核 / Needs review | Manual checks or evidence issues require reviewing the screenshots and report |
| 失败 / Failed | Installation, interaction, an assertion or capture failed; inspect the logs |
| 已取消 / 已中断 / Cancelled or interrupted | Execution did not finish; existing evidence is retained, and application state should be checked before retrying |

Stop the service with `Ctrl+C`, after handling active tasks. Restarting does not automatically repeat interrupted installations. Builds and evidence remain on disk; arrange retention and cleanup yourself.

Back to [Documentation](README.en.md).
