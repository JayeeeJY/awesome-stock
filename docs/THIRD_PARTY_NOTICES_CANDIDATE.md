# Third-party input record — Awesome Stock Community

Technical inventory for v1.0.0 preparation, updated 2026-10-07. This is neither a blanket rights approval nor a replacement for upstream notices.

## Native first-release scope

The supported installation is native source on macOS Apple Silicon (arm64). The backend uses Python's standard library and project-owned modules. The shipped browser interface includes compiled Vue, Vue Router, Pinia, Element Plus and icons, with adapted original local UI source. Node and the locked npm toolchain rebuild the interface; they are not required to run the included assets. Python is installed separately by each user. No Python interpreter, model weights, private database or private Git history is bundled.

Docker installation files, the container launcher and prebuilt images are excluded from the first-release archive and GitHub source tree. GitHub CI's secret scanner uses a container as development tooling; this does not add a product container installation option.

## Frontend licenses and provenance

[OWNER_UI_SBOM.cdx.json](OWNER_UI_SBOM.cdx.json) records the complete npm lock graph, including optional platform dependencies. [OWNER_UI_DEPENDENCIES.json](OWNER_UI_DEPENDENCIES.json) binds the inventory to the lock hash, distinguishes installed packages from other-platform optional packages, and records upstream root notice hashes. [OWNER_UI_THIRD_PARTY_LICENSES.txt](OWNER_UI_THIRD_PARTY_LICENSES.txt) contains collected upstream notice texts. Not every package in the lock graph executes in the browser.

Three supplemental notices are bound to exact upstream versions in [OWNER_UI_UPSTREAM_NOTICES.json](OWNER_UI_UPSTREAM_NOTICES.json) and included in the collected text. Two packages still have unresolved notice gaps:

| Package | Use | Publisher metadata | Remaining gap |
| --- | --- | --- | --- |
| de-indent 1.0.2 | Build-only, via Vue's compatibility compiler | MIT; author Evan You; npm gitHead 5861bd7a39c09f0056fd361d82e570e56bd2c275 | The npm archive and the matching upstream commit have no LICENSE/NOTICE body |
| lodash-unified 1.0.3 | Element Plus dependency in the production graph | MIT; author Jack Works | The npm archive has no LICENSE/NOTICE body and version metadata provides no source repository |

Official metadata: [de-indent 1.0.2](https://registry.npmjs.org/de-indent/1.0.2), [matching de-indent commit](https://github.com/yyx990803/de-indent/tree/5861bd7a39c09f0056fd361d82e570e56bd2c275), [lodash-unified 1.0.3](https://registry.npmjs.org/lodash-unified/1.0.3). Author metadata is not an independently established copyright notice. We do not invent copyright years, copy a different project's notice, or describe the generic MIT template as recovered upstream text. Notice treatment remains under review.

## Development tooling

pytest 9.1.1 and Playwright 1.63.0 are development dependencies. Their installed packages and browser binaries are not vendored. GitHub Actions references are pinned to upstream commit IDs. Actual remote execution is tracked separately; a workflow file alone is not evidence of a successful CI run.

## Historical containers

[OWNER_SUPPLY_CHAIN.json](../OWNER_SUPPLY_CHAIN.json) retains historical experimental container records. Its current_container field is null. The latest excluded P226 Linux arm64 image scan with the 2026-10-06 Trivy database reported 0 CRITICAL, 44 HIGH, 58 MEDIUM, 61 LOW and 2 UNKNOWN findings. Those findings have not been fixed or accepted; the image and Docker installation are outside the first release. Older P16/P38/P212 records describe their respective historical bytes and must not be presented as current native-runtime findings.

## Project and data permissions

Project-owned code uses AGPL-3.0-only, with attribution to Evan, as approved on 2026-10-06; see [LICENSING.md](../LICENSING.md) and [LICENSE](../LICENSE). Third-party inputs retain their own licenses. No separate commercial license is offered for this release.

The owner has declared that the original work was formed by the owner with ChatGPT and Codex, without other participants, external project/tutorial/company-code references, or employer/client/partner assets. Formation records and historical technical clues remain privately preserved, not copied into this public candidate.

Optional provider accounts and market-data permissions remain separate from source-code licenses. The owner deferred Yahoo public chart integration from the first release on 2026-10-07; its adapter is excluded and legacy query endpoints reject without network access or writes. Previously saved source records remain unchanged. Reintroducing it requires a separately reviewed source disposition. No live provider data is bundled in the release.
