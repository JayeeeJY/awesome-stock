# Obsidian 7-Repo Board Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `obsidian-7-repo-board/` — a double-click installer that copies a 7-tile Canvas dashboard into an existing Obsidian vault.

**Architecture:** Static vault files (`7-Repo-Board.canvas` + tile notes + CSS snippet) live under `vault-files/`. Platform install scripts copy them into the user’s vault and merge-enable the CSS snippet in `appearance.json` without touching other settings.

**Tech Stack:** JSON Canvas 1.0, Markdown, CSS snippets, bash (`install.sh` / `install.command`), PowerShell (`install.ps1`), Python3 optional for JSON merge (prefer pure bash/python3 available on macOS/Linux).

## Global Constraints

- Never overwrite unrelated `.obsidian` keys; only merge `enabledCssSnippets` for `7-repo-board`.
- Require an existing `.obsidian` directory in the target vault (refuse wrong folders).
- Overwrite only package-owned paths: `7-Repo-Board/**` and `.obsidian/snippets/7-repo-board.css`.
- No network during install; charts/stats are static.
- Board must open without Dataview / Minimal / Flexoki.

---

### Task 1: Tile notes + header/footer

**Files:**
- Create: `obsidian-7-repo-board/vault-files/7-Repo-Board/tiles/01-kepano-obsidian.md` … `07-flexoki.md`
- Create: `obsidian-7-repo-board/vault-files/7-Repo-Board/_header.md`
- Create: `obsidian-7-repo-board/vault-files/7-Repo-Board/_footer.md`
- Create: `obsidian-7-repo-board/vault-files/7-Repo-Board/START-HERE.md`

- [ ] Write seven visually dense tile notes (Chinese + English labels matching the reference board).
- [ ] Write header/footer notes and vault-local START-HERE.
- [ ] Commit.

### Task 2: Canvas + CSS snippet

**Files:**
- Create: `obsidian-7-repo-board/vault-files/7-Repo-Board/7-Repo-Board.canvas`
- Create: `obsidian-7-repo-board/vault-files/.obsidian/snippets/7-repo-board.css`

- [ ] Layout groups in 2 / 2 / 3 grid with Flexoki-ish color ids + file nodes.
- [ ] CSS for board note polish and canvas group accents.
- [ ] Validate canvas JSON with `python3 -m json.tool`.
- [ ] Commit.

### Task 3: Install scripts + package README

**Files:**
- Create: `obsidian-7-repo-board/install.sh`
- Create: `obsidian-7-repo-board/install.command`
- Create: `obsidian-7-repo-board/install.ps1`
- Create: `obsidian-7-repo-board/START-HERE.md`

- [ ] Implement copy + appearance.json merge.
- [ ] Smoke-test against a temp fake vault.
- [ ] Commit and update PR.
