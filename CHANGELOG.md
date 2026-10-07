# Changelog

## Unreleased — v1.0.0 stable release preparation, 2026-10-07

- Deferred Yahoo public chart integration from this first release. Manual prices, CSV import and user-owned APIs remain available; legacy public-query endpoints reject without network access or writes. Existing source history is preserved.
- First-release distribution is native source only for macOS Apple Silicon (arm64); container installation and deployment files are excluded.
- Patched the locked source-map-js build dependency to 1.2.2; compiled UI assets are unchanged. Current engineering and unresolved container findings are disclosed in docs/RELEASE_SECURITY_REVIEW.md.
- Persistent single-owner ledger: accounts, long-only trades, cash flows, FIFO and average-cost accounting, validation and history.
- Research, decisions, plans and reviews linked to fixed historical versions; candidate/evidence tools, read-only scenarios and manual rules.
- Owner-written investment journal with editable trade, position and after-close drafts, versioned revisions and archive history; separate from fixed-evidence decision reviews.
- User-owned optional OpenAI, DeepSeek, Ollama, Alpha Vantage and EODHD connections; disabled by default, explicit requests and in-memory keys. US company/news sources and market-specific data boundaries are documented.
- CSV preview/import, business JSON export, backup/restore, schema migration and explicit privacy reset.
- Self-use-style desktop navigation, compact workspace layout, grouped settings and mobile navigation; independent Owner implementation.
- Fixed research report history keeps the selected saved report visible after a failed new preview and when the dialog is reopened; failed history-list reads clear stale cached reports, and long raw source details scroll within the dialog.
- Portfolio rows show only explicitly saved, source-marked company names; market-day, same-snapshot price change and open-cost floating return percentages appear only when their evidence is valid. The desktop table keeps all columns visible and narrow screens scroll within the table.
- Position details reflect the same source and valuation boundaries: a saved company label, valid market-day change, four factual cards and a complete-portfolio position weight only when every held valuation is available. Stale valuation amounts disappear across a date change; four functional tabs fit the drawer at mobile widths.
- Expanded portfolio structure includes a third fixed-history chart of saved held-market values, linked to the underlying daily snapshots. Missing valuations break the line and failed history reads clear old points; the chart is explicitly distinguished from investment returns.
- Reproducible source archive and isolated GitHub review tree, installation instructions, test workflow and supply-chain evidence. Historical container evidence is retained separately; container installation is excluded from this first release.

Project-owned code: Copyright (c) 2026 Evan, AGPL-3.0-only, approved 2026-10-06. No separate commercial license is offered. Owner functional acceptance of T01–T21 is complete. This is not a published version; third-party rights, final residual risk and repository/publication approval remain pending. The owner-approved standard for this first stable release is completed owner functional acceptance plus final engineering verification; the former 10-trading-day and 10–20 invited-user prerequisites no longer apply to this release. No migration of private user databases or publication of private Git history occurred.
