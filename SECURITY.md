# Security — Awesome Stock Community

Scope: Community v1.0.0; actual publication is recorded in GitHub Releases. Updated 2026-10-07. This document describes the persistent local Community entrypoint. The old synthetic demo is a separate historical entrypoint.

## Current boundary

- Source launcher: one local owner, HTTP on host loopback (default 4322). There is no default account or password; the owner creates the account.
- The first-release scope is native source installation on macOS Apple Silicon (arm64). Docker installation and container images are excluded; Windows, Linux and Intel Mac are outside the supported first-release scope.
- Accounts, trades, cash flows, research, plans, reviews and history persist in SQLite. Backups contain credential hashes and business data and are not encrypted. Exported JSON excludes account credentials but may contain personal text.
- Host/Origin and CSRF checks protect the local API; sessions are process-local. Restart requires login again. There is no remote or multi-user deployment support, password recovery service or automatic broker execution.
- OpenAI, DeepSeek, user-installed Ollama, Alpha Vantage and EODHD are optional and disabled by default. Yahoo public chart integration is deferred from this first release. Legacy query endpoints reject requests without network access or writes. Manual prices and trade CSV import remain available without a connection. Each user supplies their own service access and pays their provider. Keys stay in memory and are cleared on logout, password change or restart. Selected AI context is previewed before explicit transmission; provider-side handling remains outside this application's storage boundary.
- Local Ollama must be installed by the user and uses loopback. Do not expose the model endpoint publicly to make it reachable.
- Deleting current business data does not remove independent backups, downloads or operating-system snapshots. No physical secure-erasure claim is made.

Do not expose these ports through a public bind, tunnel or reverse proxy. The current validation stage uses synthetic records. See OWNER_INSTALL.md for backup and recovery boundaries.

## Reporting an issue

The owner selected GitHub private vulnerability reporting on 2026-10-07. This channel must be enabled and verified when the repository becomes public, before publishing v1.0.0. If the report link is unavailable, do not post security details in a public issue.

Use [Report a vulnerability](https://github.com/JayeeeJY/awesome-stock/security/advisories/new) for security issues. Include the affected version, reproduction steps using synthetic records, and potential impact. Do not submit API keys, real portfolios or database backups. Do not post exploitable demonstrations in public issues. No response-time SLA is promised.

Use [GitHub Issues](https://github.com/JayeeeJY/awesome-stock/issues) for ordinary bug reports and feature feedback once the repository is public. External code contributions are not accepted for this first release.

## Verification limits

Source archive hashing and selected secret-pattern checks are reproducible with tools/audit_owner_package.py in the development tree. They do not prove absence of all secrets or inspect private Git history. The npm inventory includes dependencies used to compile the shipped interface. Historical container scans describe excluded experimental artifacts, not the native first-release runtime; their findings are neither fixed nor accepted by excluding Docker. Review results and unresolved findings belong in the release evidence, not in an unconditional safety claim.

No production-security certification, support SLA, release signature or final publication approval is implied.
