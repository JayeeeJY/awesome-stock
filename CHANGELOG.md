# Changelog

## v1.0.1 — 2026-10-07

- Restored the Personal login starfield, connecting particles, brand lockup and glass card in Community. Local account creation/login is unchanged. Reduced motion shows a static background; particles are destroyed when leaving login.
- Rewrote Chinese and English project introductions around product value and the research → decision → plan → trade → review workflow; refreshed synthetic screenshots and distinguished released Community, internal Personal experiments and future Cloud directions.
- Pinned the same tsParticles 3.9.1 engine/slim graph used by the original visual design, bundled locally with refreshed dependency notices and SBOM. No external particle scripts or new runtime service are required.
- Distribution remains native source for macOS Apple Silicon; no provider, pricing, account model or business scope change. v1.0.0 remains available unchanged.

2026-10-07 发布准备补充：新增首次使用、模型/行情凭据获取与测试/保存/失败指引，连接页提供可展开步骤；携带所有者批准的两包MIT元数据与参考文本透明披露，不冒充恢复上游正文。实际发布日期以 GitHub Releases 为准。

## v1.0.0 — first-release scope; publication date in GitHub Releases

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

Project-owned code: Copyright (c) 2026 Evan, AGPL-3.0-only, approved 2026-10-06. No separate commercial license is offered. Owner functional acceptance of T01–T21 is complete. v1.0.0 was publicly released on 2026-10-07 after owner authorization and final engineering verification; exact commits and downloads are recorded in GitHub Releases. Two absent upstream notice bodies retain the owner-approved transparent disclosure rather than invented upstream text. The owner-approved standard for this first stable release is completed owner functional acceptance plus final engineering verification; the former 10-trading-day and 10–20 invited-user prerequisites no longer apply to this release. No migration of private user databases or publication of private Git history occurred.
