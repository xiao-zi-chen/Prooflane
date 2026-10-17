# Execution and evidence review

[简体中文](handoff-acceptance.md) · **English**

The tester records the environment and observations; the reviewer confirms the conclusion. This checklist defines the handoff requirements, not checks already completed.

## Before execution

- [ ] Identify the application owner, coordinator, tester, reviewer and return channel.
- [ ] Record platform, version, architecture, physical machine / VM / WSL2, and display session such as X11 / Xvfb.
- [ ] Verify the build SHA-256 against `scenario.json`. Matching version names with different hashes are different builds.
- [ ] Confirm steps, window title, locators, installer arguments and expected text; use a native build for each platform.
- [ ] Confirm the test environment is available, the desktop is idle and required permissions are granted.

## After execution

- [ ] Return the complete `evidence.zip` and `receipt.json`; for preflight failures, return the original error and environment details.
- [ ] Match the receipt's `source_run_id` to the assigned task and `execution_run_id` to the enclosed `report.json`.
- [ ] Recompute the evidence ZIP's SHA-256 and compare it with the receipt. This checks consistency, not report authenticity.
- [ ] Match the report's build hash, platform, architecture, step count and locators against the original task.
- [ ] Confirm screenshots show the target application; images and recordings open and correspond to the actual steps.
- [ ] Check `report.json`, `feedback.md`, execution / application logs, `controls.json` and available crash information. Explain missing files.
- [ ] Do not treat screenshot review, blank captures, missing recordings or permission errors as automated passes.
- [ ] Preserve all failures and interruptions. Consider three runs of the same build, returning each result separately.
- [ ] When testing a fix, use its new build hash and keep the earlier results for comparison.

## Conclusions

| State | Meaning and next action |
| --- | --- |
| Not executed | Only instructions were delivered, or there is no execution evidence; arrange a tester |
| Environment blocked | This environment cannot execute the task; record the cause for the tester to address |
| Execution failed | Automation failed; inspect original evidence to distinguish application, input and adapter issues |
| Needs review | Steps or evidence exist, but manual layout checks, completeness or trust remain unresolved |
| Verified | A reviewer confirms this build, scenario and specified environment meet the acceptance criteria; the conclusion covers only that scope |

The standalone executor's `execution_status` is separate from the review conclusion. `receipt.json` starts with `review_status=pending`, even when automated checks report `passed`. Label manual evidence separately rather than counting it as automation success.

The controller currently has no automatic import or authenticity verification for standalone ZIPs. Do not edit its database to turn a waiting task into a pass. Track standalone outcomes in the register in `STRATEGY.en.md`, or arrange a connected worker to run the same scenario.

## Receipt supplement

```text
Application / version:
Source task ID / execution ID:
Build SHA-256:
Tester / execution date:
System version / architecture / display session:
Was the environment reset? How?
Execution status / repeat count:
Evidence ZIP location:
Problems found / steps not completed:
Reviewer / review date:
Review conclusion and coverage:
Next owner / agreed date:
```
