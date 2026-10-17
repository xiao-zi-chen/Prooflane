# Cross-platform issue record

[简体中文](issue-template.md) · **English**

Use one record per reproducible problem. Write “unknown” for facts you have not observed; do not infer them from another platform.

## Identity and environment

- Application / version / build SHA-256:
- Prooflane version or commit (state if unknown):
- Source task ID / execution ID:
- Tester / date:
- Platform / OS version / architecture:
- Physical machine, VM or WSL2; display session such as X11 or Xvfb:
- Automated execution / manual supplement:

## Problem

- Initial category: invalid input / environment blocker / possible automation issue / possible application issue / insufficient evidence.
- Severity: blocks a critical flow / functional difference / layout or experience problem.
- Failed step and action:
- Preconditions and shortest reproduction:
- Expected behavior:
- Actual behavior and original error:
- Reproductions / total attempts with the same build:
- Can the same action be completed manually? Is comparable evidence available from other systems?

## Evidence

- `evidence.zip` / `receipt.json`:
- Screenshot file / recording timestamp:
- Log file and relevant content:
- Locator information / `controls.json`:
- Missing evidence and reason:

## Follow-up

- Owner:
- Changes already tried and observations:
- Root cause (use “unconfirmed” until established):
- Fixed build SHA-256 / retest scenario:
- Reviewer / conclusion / date:

Before returning the record, check that it contains only the agreed application evidence. Worker credentials, machine passwords and unrelated personal files do not belong in it.
