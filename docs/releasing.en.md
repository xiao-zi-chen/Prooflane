# Release checklist

[简体中文](releasing.md) · **English**

Maintainers use this checklist when preparing a release. A checked item records verification for that release; the checklist itself does not mean a release has happened.

## Define the release

- [ ] The rights holder has selected a license and added the actual `LICENSE` file.
- [ ] A traceable Git commit and version tag exist, and the changelog reflects the changes.
- [ ] README, UI version and release notes agree on version and support scope.
- [ ] Maintainer contact and security reporting channels are configured; unprovided services are not claimed as available.

## Validate

- [ ] Install dependencies and start the controller from a clean checkout, recording Python, OS and dependency versions.
- [ ] Code tests, documentation checks and frontend syntax checks pass for this commit.
- [ ] Affected platforms complete the necessary GUI validation; unexecuted platforms remain marked unverified.
- [ ] Generic kits, task-bound kits and their READMEs work and exclude unrelated tasks and local credentials.
- [ ] Screenshots match the interface, and links and example paths work from the checkout.
- [ ] Chinese and English documentation and kit instructions describe the same behavior and limitations.

## Distribution

- [ ] Exclude runtime data, customer builds, credentials, virtual environments and local investigations.
- [ ] If distributing builds, identify the platform, architecture, installation steps and SHA-256.
- [ ] Record limitations, upgrade and rollback steps. There is no data migration tool; stop the service, back up and verify restoration before upgrading.
- [ ] Release notes distinguish implemented features, actual acceptance results and plans.

The repository's CI does not replace desktop acceptance testing. Release records should include reproduction commands and sanitized evidence; local `artifacts/` files do not automatically become public evidence.

Back to [Documentation](README.en.md).
