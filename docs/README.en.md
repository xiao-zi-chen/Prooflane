# Documentation

[简体中文](README.md) · **English**

New to Prooflane? Start with [Getting started](getting-started.en.md). To prepare tests for someone else to run, start with [Execution strategy](execution-strategy.en.md).

## Using and running tests

| Guide | Purpose |
| --- | --- |
| [Getting started](getting-started.en.md) | Install the controller, submit tasks and understand results |
| [Execution strategy](execution-strategy.en.md) | Prepare kits for testers with the required machines |
| [Test environments](test-machines.en.md) | What to confirm with macOS / Linux testers |
| [Worker setup](multiplatform.en.md) | Connect native workers for ongoing testing |
| [Evidence review](handoff-acceptance.en.md) | Verify returned evidence and record conclusions |
| [Issue record](issue-template.en.md) | Document a specific application or execution problem |
| [Troubleshooting](troubleshooting.en.md) | Investigate configuration, environment and evidence problems |

## Development and maintenance

| Guide | Contents |
| --- | --- |
| [Configuration](configuration.en.md) | Environment variables, directories, credentials and backups |
| [API](api.en.md) | Common endpoints, examples and result semantics |
| [Architecture](architecture.en.md) | Modules, data flow and key constraints |
| [Contributing](../CONTRIBUTING.en.md) | Development setup, checks and submissions |
| [Security policy](../SECURITY.en.md) | Deployment boundaries and vulnerability reporting |
| [Validation records](validation.en.md) | Evidence, reproduction entry points and unverified scope |
| [Release checklist](releasing.en.md) | Checks before a release |
| [Changelog](../CHANGELOG.en.md) | Unreleased features and documentation changes |

The [pilot plan](pilot.en.md) is an unexecuted user study proposal, not evidence of product capability or paid demand.

## Documentation conventions

- “Verified” must identify the build, system, scenario and evidence. “Implemented” only means that code exists.
- Run repository commands from the project root, and kit commands from the extracted kit directory.
- `artifacts/` contains local validation outputs and is not distributed with the source. Public documentation must be understandable without those files.
- Update documentation with behavior changes and register new pages here. UI references use the current labels.
- Every public root or `docs/` guide has a Chinese page and an `.en.md` counterpart. Update both together and keep the language links working.

The interface currently uses Chinese. English guides show the relevant Chinese labels where needed to find an action; task names, window titles and assertion text remain the values supplied by the author.

Back to the [project README](../README.en.md).
