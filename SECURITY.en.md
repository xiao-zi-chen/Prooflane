# Security policy

[简体中文](SECURITY.md) · **English**

Prooflane installs and runs submitted desktop applications. It is designed for dedicated test environments managed by trusted operators, not a public service hosting untrusted tenants.

## Current boundaries

- The controller listens on localhost by default; use private connections for remote access.
- Host / Origin checks and the `X-Prooflane-Client` header are not account authentication.
- Worker registration and subsequent calls require credentials. Platform, architecture, ownership and leases constrain task claims and result uploads.
- Archive extraction checks path traversal and other inputs, but run directories, process cleanup and worker authentication do not sandbox an application.
- Hashes in standalone receipts verify file consistency, not the trustworthiness of a tester or evidence.

Tenant isolation, VM creation and snapshot restoration, a worker credential revocation UI and automatic data retention are not implemented. Deployers manage test machines, networks and evidence access.

## Report a vulnerability

Relevant issues include authentication bypass, unauthorized reads or result uploads, path traversal, credential exposure, and execution or data access that violates the documented boundaries.

GitHub private vulnerability reporting is enabled. Use [Report a vulnerability](https://github.com/xiao-zi-chen/new/security/advisories/new). Do not post exploit instructions, credentials or customer evidence in public Issues. There is no separate security email address at present.

Include:

- Affected code revision, platform and deployment configuration.
- Minimal reproduction, expected restriction and observed behavior.
- Potentially affected tasks or data.
- Sanitized logs, screenshots or sample inputs.

The project has no stable release series or guaranteed security response time. Fix announcements should identify affected scope, the fixed version and upgrade steps.

## Credentials and data

The controller's `agent-token` file holds the registration credential. Workers receive their own credentials after registration. Changing the registration credential does not invalidate existing worker credentials. If a credential is exposed, stop the service and affected workers to prevent further task claims, then have the maintainer inspect and address registration records.

Reports may contain application text, file paths and system information. Use minimal sanitized evidence in public Issues; exchange originals through an agreed private channel. Adding a secret to `.gitignore` does not remove it from Git history. Exposed credentials need revocation and history may need separate remediation.

See [Configuration](docs/configuration.en.md) for data locations and backups.
