# First-release security and platform review / 首发安全与平台范围

2026-10-06 · Community · P226. This is engineering evidence, not publication approval or a security certification.

The owner accepted T01–T21 functional testing. The approved first stable-release standard is completed owner functional acceptance plus final engineering verification. No long-duration or invited-user trial is claimed.

## Current first-release scope / P227 approved

The owner selected plan A: native source only on macOS Apple Silicon (arm64). Native installation, restart and isolated backup/restore were tested with Python 3.10.20 in P226 and Python 3.14.3 in P227. Container entrypoints, deployment files, container-specific verification and prebuilt images are excluded from both first-release artifacts. Windows, Linux and Intel Macs are not supported release targets. Prior Linux arm64 container tests are historical engineering evidence only. Browser checks cover desktop and narrow widths including 1440, 390 and 320 pixels; provider scenarios use controlled fixtures and do not establish every provider/account entitlement.

## Current findings

The locked UI/build and checks dependency audits report zero npm advisories after updating source-map-js from 1.2.1 to 1.2.2 for [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q). The compiled UI assets are unchanged.

Historical P226 container findings (outside the P227 release scope): Trivy 0.72.0 scanned the exact Linux arm64 test image with a database updated at 2026-10-06T07:04:23Z: **0 CRITICAL, 44 HIGH, 58 MEDIUM, 61 LOW, 2 UNKNOWN** package/advisory matches. The 44 HIGH matches concern 17 binary packages and 8 CVEs: CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410, CVE-2026-54369, CVE-2025-69720, CVE-2026-16742 and CVE-2026-9538. No fixed version is listed in the scan; this does not mean harmless. Current descriptor/hash binding, SBOM and scan metadata are recorded in `historical_container_scans` in OWNER_SUPPLY_CHAIN.json; older top-level fields are historical.

The deferred historical Compose configuration uses a non-root user, read-only root filesystem, loopback host binding, all capabilities dropped and no-new-privileges. These controls were checked but do not patch the findings or prove per-CVE unreachability. Source-only distribution avoids shipping a prebuilt image; user-built containers still inherit base-image risk. No container image has been published.

## Owner decision / D4 已处置

2026-10-06，用户明确选择「A方案」。首发仅提供macOS Apple Silicon原生源码安装，容器安装暂缓。容器漏洞记录保留为历史，未标记修复、无害或风险接受；它们不属于本次交付的运行依赖。平台范围及排除项写入两个发行清单，并在隔离产物中核对。

This scope decision does not certify the native runtime as vulnerability-free. Users maintain their own supported Python interpreter. The npm audit and source secret scan have their stated coverage limits. Project license is AGPL-3.0-only, copyright Evan; third-party notices and public market-data terms remain separate review items. Historical exposed-key revocation, repository identity/target, remote CI and final publication approval remain separate.
