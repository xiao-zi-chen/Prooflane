# Execution strategy

[简体中文](execution-strategy.md) · **English**

Give the same acceptance steps to testers with the required machines. Prooflane provides execution tools and return formats; the application owner supplies builds, testers arrange environments, and reviewers confirm results.

This document is also included as `STRATEGY.en.md` in execution kits and can be read without the repository.

## Define the scope

Start with an environment your users actually use, specifying system version, architecture and display session: for example, Windows x86_64, an Apple Silicon Mac or Ubuntu X11. Add Intel Macs, other distributions, architectures or DPI settings when needed, without promising blanket coverage.

Each task needs a native build, version, SHA-256, window title, launch or installation details and 3–5 acceptance steps. Platforms share step titles and actions; locators and expected text may differ.

## Find a tester

Start with colleagues, customer QA or partners who already have devices. Before arranging a paid provider, confirm desktop access, dependency installation and capture permissions. A machine that can compile an application may not support desktop acceptance testing.

Confirm:

1. The system version, CPU architecture and desktop session match the task.
2. The tester can install dependencies, run the build and capture its window.
3. The schedule, cost and channel for returning results are agreed.
4. The tester can return original errors and existing evidence if execution fails.

Testers provide or arrange equipment. The party preparing the strategy does not need to buy machines for every platform.

## Choose execution mode

| Mode | Suitable for | Result handling |
| --- | --- | --- |
| Standalone kit | One-off collaboration without controller access | Return receipt and evidence ZIP for human review |
| Connected worker | Ongoing testing with a desktop and private connection available | Automatically claim matching tasks and upload evidence; human checks still need review |
| Manual supplement | Custom rendering, permissions or adapter limitations prevent automation | Preserve the same steps and build identity; mark the result as manual testing |

Downloading a kit does not notify anyone. Invitation text is a draft; the coordinator fills in actual arrangements and sends it.

## Export and execute

1. In **执行策略** (Execution strategy), select a platform and a specific task. The default generic strategy contains instructions and templates only.
2. Download the kit. Select **将应用文件一起放入 ZIP** to include the build; otherwise send the file with the same hash separately.
3. The tester extracts it on the target system and follows `README.en.md` to install dependencies and grant permissions.
4. Run the preflight command with `--check`, then the command without `--check` to execute.
5. Return `receipt.json`, `evidence.zip` and an issue record. If preflight fails, return the original error and environment details.

Both documentation languages are included in the same kit. The scenario is preserved as supplied: task titles, locators and expected text are not translated automatically.

Each standalone execution creates a new result directory. The tool does not restore snapshots. The application owner should specify how to reset external files, installation state or account data. Run only one GUI task per desktop at a time.

For an initial stability check, consider three runs with environment resets. This is a suggested method, not a success rate already achieved by the project.

## Assign problems

| Problem | Initial owner | Needed information |
| --- | --- | --- |
| Wrong hash, architecture, path or steps | Application owner | File name, actual hash, task ID and error |
| Missing dependencies, permissions, unlocked session or X11 | Tester | System and session details, preflight output |
| Manual interaction works but controls cannot be located | Tool maintainer and application owner | Control inventory, locator fields and screenshot |
| Unexpected output or application exit | Application owner | Reproduction, logs, exit code and media |
| Blank screenshots or missing recordings | Tester and tool maintainer | Capture logs, available files and missing scope |

Initial categories route work; they are not confirmed root causes. Retest fixes with a new build hash and retain the earlier failures.

## Review and record

Use `ACCEPTANCE.en.md` in the kit to verify the build, environment, steps and evidence, and `ISSUE_TEMPLATE.en.md` to record problems. Their repository sources are `docs/handoff-acceptance.en.md` and `docs/issue-template.en.md`.

| Platform / version / architecture / session | Tester | Build hash and source task | Execution ID / attempts | Evidence location | Execution state | Review / reviewer | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| To fill in | Unassigned | To fill in | Not executed | Not returned | Not executed | Not reviewed | Confirm tester |

Automated success and human review are separate. Standalone receipts start with `review_status=pending` and do not automatically import or update the source task. Record manual supplements separately; they do not establish adapter success.

Record preparation time, execution time, human intervention and blockers for each round. Resolve execution failures and incomplete evidence first, then reduce configuration effort and expand coverage.
