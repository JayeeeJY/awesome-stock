#!/usr/bin/env bash
# Install 7-Repo Board into an existing Obsidian vault.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/vault-files"
STATE="$ROOT/.vault-path"

die() { echo "错误: $*" >&2; exit 1; }
info() { echo "→ $*"; }

pick_vault() {
  if [[ $# -ge 1 && -n "${1:-}" ]]; then
    printf '%s' "$1"
    return
  fi
  if [[ -f "$STATE" ]]; then
    local saved
    saved="$(tr -d '\r\n' < "$STATE")"
    if [[ -d "$saved/.obsidian" ]]; then
      printf '%s' "$saved"
      return
    fi
  fi
  echo "请输入你的 Obsidian vault 绝对路径（目录内应有 .obsidian）："
  local path
  read -r -p "> " path
  # Expand ~
  path="${path/#\~/$HOME}"
  printf '%s' "$path"
}

merge_snippet() {
  local appearance="$1"
  python3 - "$appearance" <<'PY'
import json, sys, os
path = sys.argv[1]
data = {}
if os.path.isfile(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if raw:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise SystemExit(f"appearance.json 不是对象: {path}")
enabled = data.get("enabledCssSnippets")
if not isinstance(enabled, list):
    enabled = []
if "7-repo-board" not in enabled:
    enabled.append("7-repo-board")
data["enabledCssSnippets"] = enabled
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("enabled")
PY
}

main() {
  local vault
  vault="$(pick_vault "${1:-}")"
  [[ -n "$vault" ]] || die "未提供 vault 路径"
  [[ -d "$vault" ]] || die "目录不存在: $vault"
  [[ -d "$vault/.obsidian" ]] || die "看起来不像 vault（缺少 .obsidian）: $vault"
  [[ -d "$SRC/7-Repo-Board" ]] || die "安装包不完整，缺少 vault-files/7-Repo-Board"

  info "目标 vault: $vault"
  mkdir -p "$vault/.obsidian/snippets"

  info "复制 7-Repo-Board/ …"
  rm -rf "$vault/7-Repo-Board"
  cp -R "$SRC/7-Repo-Board" "$vault/7-Repo-Board"

  info "安装 CSS snippet …"
  cp "$SRC/.obsidian/snippets/7-repo-board.css" "$vault/.obsidian/snippets/7-repo-board.css"

  info "启用 snippet（合并 appearance.json）…"
  merge_snippet "$vault/.obsidian/appearance.json"

  printf '%s\n' "$vault" > "$STATE"

  echo
  echo "完成。"
  echo "下一步："
  echo "  1. 打开 Obsidian → 打开文件  7-Repo-Board/7-Repo-Board.canvas"
  echo "  2. 若 snippet 未生效：设置 → 外观 → CSS 代码片段 → 勾选 7-repo-board"
  echo "  3. （可选）安装 Minimal 主题 + Flexoki 配色，更接近原图"
  echo
  echo "说明见: $vault/7-Repo-Board/START-HERE.md"
}

main "$@"
