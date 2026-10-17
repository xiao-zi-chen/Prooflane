# Initial user pilot

[简体中文](pilot.md) · **English**

Status: planned. No participants have been recruited and no paid results recorded. This document organizes a possible pilot; it does not establish market validation.

## Questions to answer

Can developers without test devices use an execution kit and a third-party tester to obtain reproducible feedback? For repeat tests, does preparation and review take less human effort than their current process?

The first round proposes five developers who mainly use Macs but publish Windows applications. Existing Windows sample records make it a practical initial scope. Expand into macOS / Linux only after obtaining execution evidence on those desktops.

## Inputs and arrangements

Participants provide a recent real EXE, MSI or ZIP and 3–5 important steps. Prefer single-window tools with standard controls. Assess drivers, reboots, complicated elevation and login flows separately.

The application owner supplies the build and expectations; the tester supplies a dedicated, restorable Windows environment. Agree on schedule, fees, evidence scope and retention, following the [execution strategy](execution-strategy.en.md).

## Comparison method

From the same initial environment, measure preparation, execution and feedback assembly for both manual testing and Prooflane. Include first-time automation configuration rather than comparing only subsequent runtime.

Consider three runs per build, resetting the environment and alternating the order. Ask developers whether the report lets them reproduce problems, then record whether they actually request a retest after a fix.

| Record | Method |
| --- | --- |
| Build and environment | Anonymous task ID, SHA-256, system and architecture |
| Manual baseline | Time preparation, interaction and feedback separately |
| Automation cost | Separate initial setup, each execution and human intervention |
| Problem category | Distinguish application defects, automation false positives and environment failures |
| Feedback quality | Can the developer reproduce it? What information is missing? |
| Continued use | Did they submit another build or actually pay? |

Costs include machine time, human work, storage and transfer. Record intended prices and actual payments separately.

## Evaluate the pilot

The proposed internal thresholds are hypotheses, not current data: at least four participants finish a real flow; repeat results agree at least 90% of the time; human intervention after setup is half the manual baseline; and at least two participants purchase another test.

If a threshold is missed, inspect the causes. Locator failures suggest narrowing application scope and improving diagnostics. Excessive setup time may call for assisted testing. Without repeat demand, defer expanding equipment investment.

Back to [Documentation](README.en.md).
