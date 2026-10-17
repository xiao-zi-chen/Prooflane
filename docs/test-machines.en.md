# Arrange test environments

[简体中文](test-machines.md) · **English**

Use this guide when contacting testers with macOS or Linux machines. Testers arrange equipment and maintenance; the project supplies tasks, tools and review criteria. There are no publishable Mac or Linux GUI pass records yet.

## Where to look

| Source | Confirm first |
| --- | --- |
| Colleagues or internal QA | System, architecture, available time and permission to run the build |
| Customer QA or partners | Acceptable build delivery, capture scope and return channel |
| Community testers | Try a public sample first, then agree on business builds and information handling |
| Testing services or cloud desktops | Graphical desktop, dependencies, permissions, total cost and minimum billing period |

Pricing and availability change. The person arranging equipment should confirm them before purchasing. This guide does not maintain unverified quotes or vendor recommendations.

## macOS

Use a Mac environment that complies with Apple's licensing terms, with Python 3.11+ and an actual user desktop. The tester must be able to grant Accessibility and Screen Recording permission to the terminal / Python process that runs the worker.

Record Apple Silicon and Intel separately. SSH-only or compile-only access is not sufficient to declare a GUI worker ready. Obtain a complete sample's screenshots, recording and logs before recording the environment's coverage.

## Linux

The current adapter needs X11, AT-SPI / PyGObject, D-Bus and XComposite. Wayland is unsupported. Ubuntu 24.04 is a reasonable starting environment; verify package names and libraries separately for other distributions.

| Environment | Record and limitations |
| --- | --- |
| Physical or virtual X11 desktop | Distribution, version, architecture and desktop session |
| Xvfb on a server without a desktop | Identify it as a virtual display; results do not establish physical GPU or Wayland behavior |
| WSL2 with Xvfb | Record both WSL2 and Xvfb; this does not establish compatibility with a physical Linux desktop |

See [Worker setup](multiplatform.en.md) for dependencies and the helper script. Having a script does not mean the environment has passed actual tests.

## Message before assigning a task

```text
Could you help test a desktop application?
Target system and architecture:
Application version and build delivery:
Acceptance steps:
Available time and cost:
Return channel and evidence retention period:

We provide the execution kit and instructions. Please confirm that you can
install dependencies, run the application and capture its window.
Return the receipt and evidence ZIP. If blocked, return the original error
and environment details instead.
```

Start with [standalone execution](execution-strategy.en.md). Testers do not need to share machine passwords or connect to the controller. For ongoing automation, arrange a [connected worker](multiplatform.en.md).

## Confirm readiness with evidence

Finding a machine, establishing a connection, having a ready worker and completing acceptance are different milestones. Once you receive build identity, environment details, executed steps and readable evidence, apply the [review checklist](handoff-acceptance.en.md).

Back to [Documentation](README.en.md).
