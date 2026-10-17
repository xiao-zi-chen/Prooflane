# Changelog

[简体中文](CHANGELOG.md) · **English**

## Unreleased

These entries describe the current source and do not correspond to a formal release tag. The UI's `v0.2` label identifies a preview.

### Features

- Task configuration and step-by-step comparison for native Windows, macOS and Linux builds.
- Connected worker registration, platform and architecture matching, lease renewal and evidence upload.
- Generic instruction kits and task-bound kits with scenarios and standalone execution tools.
- Windows Notes GUI, capture and standalone execution records. macOS and Linux desktop adapters still await testing on their target systems.

### Interface

- The overview prioritizes results; the strategy page prioritizes task selection and downloads.
- Simpler copy and layouts for desktop, tablet and mobile.
- Polling preserves focus and expanded instructions after changing kit options.

### Documentation and maintenance

- Rewritten README and guides for setup, configuration, APIs, architecture and troubleshooting.
- Organized execution strategy, evidence review, validation records and test environment guidance.
- Contribution and security policies, Issue / PR templates and a release checklist.
- Documentation checks and GitHub Actions, with the first three-system code matrix and documentation / frontend checks passing.
- GitHub private vulnerability reporting enabled.
- Chinese and English documentation with language links, English Issue forms, a bilingual PR template and bilingual execution kits.
- Literal build-path quoting in generated PowerShell / Bash commands, preserving spaces and special characters in filenames.

See [Validation records](docs/validation.en.md) for verified scope and outstanding gaps. For a formal release, move the relevant entries under its actual version and release date.
