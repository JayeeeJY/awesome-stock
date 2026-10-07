# Third-party input record — Owner source candidate

Technical inventory only; not the project license or legal approval. Updated 2026-10-02; historical container evidence is separately dated.

The backend uses Python's standard library and the internal awesome_stock package. The default browser interface now includes compiled Vue, Vue Router, Pinia, Element Plus and Element Plus icons, with adapted original local UI source. Node and the locked build toolchain are needed to rebuild these assets, not to run the prebuilt application. Previous statements that this interface has no npm build or third-party icons no longer apply. No model weights or private database are bundled.

`OWNER_UI_SBOM.cdx.json` records the complete npm lock graph, including optional platform dependencies. `OWNER_UI_DEPENDENCIES.json` ties the inventory to the lock hash, distinguishes locally installed packages from other-platform optional packages, and records upstream root notice hashes. `OWNER_UI_THIRD_PARTY_LICENSES.txt` contains collected upstream notice texts. This conservative graph is not a claim that every listed package executes in the browser. Three missing root notices have version-linked upstream texts in `OWNER_UI_UPSTREAM_NOTICES.json`, also included in the aggregate notice file. Two installed packages (`de-indent@1.0.2`, `lodash-unified@1.0.3`) still lack upstream notice texts and remain pending review; platform packages not installed locally have no copied notice text. These gaps are not legal approval.

The current Owner container base is:

`python:3.10-slim-trixie@sha256:000d806b9dee7f9b12ed29ac3705ec5027bc696fdc8f3b2f60c64b3a1f09175a`

The historical 2026-09-20 inspected ARM64 runtime is Python 3.10.21, OpenSSL 3.5.7 and SQLite 3.46.1. Bundled site-packages/installers are removed from the final runtime, but layer deletion does not erase lower-layer bytes or distribution obligations. That historical SPDX inventory contains 123 component records; exact versions, scanner-declared licenses and vulnerability findings are in OWNER_SUPPLY_CHAIN.json. Such declarations are evidence, not a legal compatibility conclusion.

Current distribution is source only. Users pull the official pinned input and build locally. No prebuilt image is redistributed. Publishing an image later requires a separate review of notices, corresponding source and other applicable obligations for the exact distributed layers.

Development checks optionally install pytest 9.1.1 and Playwright 1.63.0; these are test tooling, not application runtime dependencies. Their files and browser binaries are not vendored in this tree. GitHub Actions references are pinned to inspected upstream commit IDs; remote CI has not run yet.

The owner approved AGPL-3.0-only for project-owned code with attribution to Evan on 2026-10-06; see ../LICENSING.md and ../LICENSE. Third-party notices, six historical provenance clues and remaining applicable obligations still require final review. Optional provider account/data terms remain separate from source-code permissions. This inventory grants no separate commercial license or blanket legal clearance.

## Historical container evidence (2026-09-27 local date)

The historical P38 ARM64 image and refreshed database scan are preserved under `OWNER_SUPPLY_CHAIN.json.historical_container_scans`, not its current-container field. Docker Scout emitted 124 SPDX package records (including its image record); the log reported 123 indexed packages. Trivy reported 156 package/advisory matches across 68 distinct advisories: 44 HIGH, 53 MEDIUM, 57 LOW and 2 UNKNOWN; none had a reported fixed version in that scan. Five matches were added since the historical P16 scan. This historical result cannot describe the current image. The scanner did not detect the npm graph inside compiled assets; the separate frontend inventory is required. No risk acceptance or release approval follows from these reports.

## Current container evidence (2026-10-02, P212)

The official pinned Python 3.10.22 slim-trixie multi-architecture base was verified against Docker's current registry manifest. For the supported linux/arm64 build, the Debian security package libpcre2-8-0 10.46-1~deb13u3 is fetched by BuildKit with its exact SHA256 before offline build commands install it. This removes the scanner-reported fixable high-severity PCRE match while keeping build commands under the compose network:none policy. The arm64 package path is intentional; other image architectures are not currently validated.

The current recorded P212 Linux ARM64 image was built from the provisional P212 source archive after the visual label/date alignment. All 167 application files match that archive byte for byte, including the Vue entry page and build manifest; the final P212 source archive is checked separately against the runtime payload. Its isolated container passed page asset loading, account and business setup, backup creation, restart, data retention and backup restoration to a separate directory. Trivy 0.72.0 with the 2026-10-02 database reported 163 package/advisory matches across 72 advisories: 44 HIGH, 57 MEDIUM, 60 LOW and 2 UNKNOWN, with no reported fixed version. Its SPDX report has 89 package records. Frontend production npm audit reported zero advisories on the unchanged dependency lock; neither scanner establishes legal approval or harmlessness of the remaining findings. The exact image ID and report hashes are in `OWNER_SUPPLY_CHAIN.json.current_container`; full local evidence is documented in the project review report `docs/RELEASE_VISUAL_LABELS_P212.md` outside the distributable source archive. Earlier containers and archives are historical evidence.
