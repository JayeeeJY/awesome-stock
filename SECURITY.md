# Security — Owner local candidate

Status: development candidate; no supported public release yet. This document describes the persistent Owner entrypoints. The old synthetic demo is a separate historical entrypoint.

## Current boundary

- Source launcher: one local owner, HTTP on host loopback (default 4322). There is no default account or password; the owner creates the account.
- Owner Compose: host loopback only (default 4323), non-root process, read-only application filesystem, dedicated persistent data volume. The container listens internally on 0.0.0.0; this is not authorization for public exposure.
- Accounts, trades, cash flows, research, plans, reviews and history persist in SQLite. Backups contain credential hashes and business data and are not encrypted. Exported JSON excludes account credentials but may contain personal text.
- Host/Origin and CSRF checks protect the local API; sessions are process-local. Restart requires login again. There is no remote or multi-user deployment support, password recovery service or automatic broker execution.
- OpenAI, DeepSeek, user-installed Ollama, Alpha Vantage and EODHD are optional and disabled by default. The Yahoo public daily-data candidate requires no key and is queried only after an explicit action; its data terms remain under release review. Each user supplies their own service access and pays their provider. Keys stay in memory and are cleared on logout, password change or restart. Selected AI context is previewed before explicit transmission; provider-side handling remains outside this application's storage boundary.
- Local Ollama must be installed by the user. Source mode uses loopback; container mode uses the fixed host.docker.internal destination. Do not expose the model endpoint publicly to make it reachable.
- Deleting current business data does not remove independent backups, downloads or operating-system snapshots. No physical secure-erasure claim is made.

Do not expose these ports through a public bind, tunnel or reverse proxy. The current validation stage uses synthetic records. See OWNER_INSTALL.md for backup and recovery boundaries.

## Reporting an issue

Do not post secrets, personal records or exploitable demonstrations in public issues. No public private-reporting address has been designated. The repository owner must select a private reporting channel before public release; do not invent an address or promise a response time.

## Verification limits

Source archive hashing and selected secret-pattern checks are reproducible with tools/audit_owner_package.py in the development tree. They do not prove absence of all secrets or inspect private Git history. Container SBOM and vulnerability results are tied to the exact image and scan time; zero direct application dependencies does not mean zero third-party components. Review results and unresolved findings belong in the release evidence, not in an unconditional safety claim.

No production-security certification, support SLA, release signature or final publication approval is implied.
