# Obsidian 7-Repo Board — Drop-in Package Design

**Date:** 2026-11-08 (Asia/Shanghai)  
**Status:** Approved in chat; awaiting written-spec review  
**Goal:** Ship a copy-into-existing-vault package that recreates the “OBSIDIAN TEAM · 7 REPO BOARD” Canvas desktop with one double-click install script.

## Problem

The reference image is a hand-composed Obsidian Canvas dashboard showcasing seven public projects. Those repos supply themes, formats, and content ideas — not the board itself. The user wants that board inside their **existing** vault with **minimal** setup (prefer double-click script).

## Constraints

- Must not overwrite the user’s theme, community plugins, or unrelated `.obsidian` settings.
- Must work as a folder of files the user can also inspect without running a script.
- Charts and GitHub stats are **static** visual stand-ins (no live API).
- Dataview is optional; board must open without it.
- Cloud agent cannot write to the user’s local Obsidian; deliverable is an installable package in this repo.

## Chosen install approach

**Double-click / one-run install scripts** (user choice #1):

| Platform | Entry |
|---|---|
| macOS | `install.command` |
| Windows | `install.ps1` |
| Linux | `install.sh` |

Shared behavior:

1. Ask for the vault root path once (or accept it as the first CLI argument).
2. Optionally persist the path in a local `.vault-path` next to the scripts (gitignored if committed from a clone; for the shipped package, document that this file is machine-local).
3. Copy package content into `<vault>/7-Repo-Board/`.
4. Copy CSS snippet into `<vault>/.obsidian/snippets/7-repo-board.css`.
5. Merge-enable the snippet in `<vault>/.obsidian/appearance.json` when that file exists; create a minimal `appearance.json` with only `enabledCssSnippets` if missing.
6. Print next steps: open `7-Repo-Board/7-Repo-Board.canvas`; optionally install Minimal + Flexoki for closer look.

## Package layout

```
obsidian-7-repo-board/
  START-HERE.md
  install.sh
  install.command
  install.ps1
  vault-files/
    7-Repo-Board/
      7-Repo-Board.canvas
      START-HERE.md
      tiles/
        01-kepano-obsidian.md
        02-jsoncanvas.md
        03-obsidian-releases.md
        04-obsidian-sample-plugin.md
        05-40-questions.md
        06-obsidian-minimal.md
        07-flexoki.md
      _header.md
      _footer.md
    .obsidian/
      snippets/
        7-repo-board.css
```

Install copies `vault-files/7-Repo-Board/` → `<vault>/7-Repo-Board/` and the snippet → `<vault>/.obsidian/snippets/`.

## Canvas design

Single file `7-Repo-Board.canvas` using JSON Canvas 1.0:

- Header group + file/text node for title and static counters (7 / stars-style stats as static numbers matching the reference feel).
- Seven colored **group** frames in a 2 / 2 / 3 grid.
- Each group contains a **file** node pointing at the corresponding `tiles/*.md` note (and small text labels where needed).
- Footer text strip listing the seven project names.
- No edges required (dashboard, not flowchart).

Tile notes use Markdown only: headings, tables, fenced code, ASCII/Unicode progress, mermaid where helpful, and Flexoki-colored callouts. They explain the real GitHub project and visually approximate the reference panel.

## Appearance

- CSS snippet provides: canvas group accent borders, header/footer typography tweaks, soft Flexoki-like dark accents for board notes.
- Does **not** force Minimal theme. START-HERE recommends installing [Minimal](https://github.com/kepano/obsidian-minimal) and Flexoki style settings for the closest match.
- Snippet ID / filename: `7-repo-board` / `7-repo-board.css`.

## Safety rules for installers

- Refuse to run if target path does not look like a vault (must contain `.obsidian` **or** user confirms create-`.obsidian`).
- Prefer requiring an existing `.obsidian` directory to avoid dumping into the wrong folder.
- Never delete user files; overwrite only package-owned paths under `7-Repo-Board/` and the single snippet file.
- `appearance.json` edit: read JSON → ensure `enabledCssSnippets` array includes `"7-repo-board"` → write back with stable formatting; leave all other keys untouched.
- No network calls during install.

## Out of scope

- Live GitHub star/download sync.
- Shipping Minimal/Flexoki binaries inside the package.
- Converting this into a community plugin.
- Auto-opening Obsidian after install (print the path instead).

## Success criteria

1. User runs one platform script, points at vault once, and can open the Canvas immediately.
2. Existing vault notes and settings remain intact aside from the snippet enable merge.
3. Without Minimal/Flexoki, board is still readable and recognizably the 7-tile layout.
4. With Minimal + Flexoki, look is close to the reference image’s mood (not pixel-perfect screenshots).

## Implementation notes (for plan)

- Repo destination: `obsidian-7-repo-board/` at repository root (alongside existing `docs/`), plus this spec under `docs/superpowers/specs/`.
- Validate `.canvas` JSON manually against JSON Canvas node schema (ids, types, positions).
- Smoke-test install script against a temporary fake vault directory in CI or local shell.
