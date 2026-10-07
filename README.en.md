# Awesome Stock · Community

A self-hosted personal investing workspace connecting your ledger, research, decisions, plans and reviews. Run it on your own computer, with your own data and optional model services.

**Preparing the v1.0.0 stable release. Not publicly released.** The project license is AGPL-3.0-only; notice treatment and market-data scope follow the owner decisions; final engineering verification and publication approval are recorded separately. Screenshots use synthetic test data only.

[中文](README.md) · [Installation and recovery](OWNER_INSTALL.md) · [Security](SECURITY.md)

## Run locally

The first release supports native source installation on macOS Apple Silicon (arm64), with Python 3.10+. The application uses only the standard library; no Node runtime, database service or AI model is required.

```sh
python3 start_owner.py --open-browser
```

Visit `http://127.0.0.1:4322/ledger` and create your own local account. There are no default credentials or preloaded holdings.

Docker installation and prebuilt container images are deferred. Windows, Linux and Intel Macs are outside the supported first-release scope. See [installation and recovery](OWNER_INSTALL.md).

## Workspaces

- **Cockpit:** ledger facts, gaps, action feedback and recent trades.
- **Portfolio:** separate accounts and currencies, long-only trades, cash flows, per-account FIFO or weighted-average accounting, CSV preview/import and manual price snapshots.
- **Research:** candidates, evidence, explicit filters, comparisons and versioned notes.
- **Plan:** versioned decisions, supporting/counter evidence, invalidation conditions, manual plans and read-only allocation/trade scenarios.
- **Evolve:** reviews tied to historical evidence, manual rules and process trends.
- **Academy:** educational articles from the original application with diagrams, search and categories.

Settings include account and data controls, optional connections, import/export, light/dark/system appearance, desktop sidebar width, and a cockpit privacy toggle. Appearance and cockpit privacy preferences are saved only in the current browser.

![Settings with synthetic data](docs/screenshots/settings.png)

## Your services, your costs

OpenAI, DeepSeek, user-installed Ollama, Alpha Vantage and EODHD are optional, disabled by default and called only after explicit actions. Yahoo key-free data is deferred from this first release. Manual price snapshots and CSV import work without a market connection; automated queries require the user's own API. There is no startup query or automatic provider fallback. Each user supplies their own access and pays their provider for configured services. No shared project key or subsidy is provided. Cloud model IDs are supplied by each user. Alpha Vantage provides optional US/USD and Shanghai-Shenzhen A-share/CNY daily prices and history; the independent EODHD connection provides Hong Kong/HKD daily data. Company and news connections currently cover US securities only. See [provider boundaries](docs/OPTIONAL_PROVIDERS.md).

Keys stay in server process memory and clear on logout, password change or restart. Ask Awesome supports free questions and follow-ups; each message, attached material and session history is reviewed before sending. Conversation history stays in page memory and clears on refresh; responses cannot execute trades. No broker synchronization, real-time pricing or automatic migration from the private product is provided.

## Data and status

Local SQLite data lives in `.owner-state` unless `--data-dir` is set. Backups are unencrypted and include credential hashes and business history. Recovery creates a new directory without replacing the original. Cross-currency summaries use recorded, valid user-supplied FX rates to convert to USD; unavailable prices or FX rates remain explicitly missing. Converted P&L excludes historical FX gains and losses.

See [validation](docs/VALIDATION.md), [development checks](docs/DEVELOPMENT.md) and [contribution policy](CONTRIBUTING.md).

The first release accepts [issues and product feedback](https://github.com/JayeeeJY/awesome-stock/issues), not external code contributions. Security reports use GitHub private vulnerability reporting; see [SECURITY.md](SECURITY.md). The repository is currently private staging. Public feedback channels will be activated and verified when it becomes public.

## License and release

Copyright (c) 2026 Evan. Project-owned code is licensed under **AGPL-3.0-only**; see [LICENSE](LICENSE) and [licensing scope](LICENSING.md). No separate commercial license is offered for this release; commercial use complying with AGPL remains permitted. Third-party inputs retain their own licenses. Outstanding notice/provenance reviews, market-data terms and publication approval remain separate conditions. No prebuilt image, model weights or private repository history is distributed.

## First-use and connection checklist

1. Start the app as described in [installation](OWNER_INSTALL.md), create your own local login, and keep the same data directory when restarting. There is no default password.
2. Create a capital account, record opening cash **before the first trade**, then enter cash flows and trades. In Settings → Import/Export, download the CSV template, choose an account, preview and confirm. CSV imports trades, not quotes or price history.
3. In Portfolio → Manage holdings → Record price snapshot, enter verified prices with dates and sources. Missing prices or FX stay unknown. Core manual workflows need no provider account.
4. In Settings → Data & AI connections, select DeepSeek/OpenAI and provide your own API Key plus model ID; or install Ollama locally, download a local model and enter its exact name with no Key. Save, then explicitly confirm the connection test. Saving alone does not call the provider.
5. A successful test shows a success card and the model reply. Open Ask Awesome from the top bar to type a question, preview the actual outbound content and confirm sending. Load page material only when needed. Cloud charges go to your own provider account.
6. Optional quotes require your own Alpha Vantage Key for US/CN or EODHD Token for HK. Select the market, enter a code (AAPL / 600104 / 00700), query, inspect the preview and explicitly save. Daily prices are not realtime. Yahoo is deferred; there is no shared project Key or automatic fallback.
7. Create a full backup in account/data settings and copy the complete backup directory elsewhere. Keys stay only in process memory and are cleared on logout, password change, connection closure or restart. Backups are not encrypted.

The connection page includes expandable setup steps and official provider account links. Detailed Chinese guides: [first use](docs/QUICKSTART.md), [provider setup and troubleshooting](docs/OPTIONAL_PROVIDERS.md). Missing package-specific upstream notices are transparently described in the [owner-approved MIT metadata/reference disclosure](docs/OWNER_UI_NOTICE_DISCLOSURES.txt); the reference is not represented as recovered upstream text.
