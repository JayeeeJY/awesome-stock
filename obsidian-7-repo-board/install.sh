#!/usr/bin/env bash
# Install 7-Repo Board into an existing Obsidian vault.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/vault-files"
STATE="$ROOT/.vault-path"

die() { echo "错误: $*" >&2; exit 1; }
info() { echo "→ $*" >&2; }
prompt() { echo "$*" >&2; }

# Print ONLY the vault path on stdout (so command-substitution is safe).
# All human-facing text goes to stderr.
pick_vault() {
  if [[ $# -ge 1 && -n "${1:-}" ]]; then
    local arg="${1/#\~/$HOME}"
    printf '%s' "$arg"
    return
  fi
  if [[ -f "$STATE" ]]; then
    local saved
    saved="$(tr -d '\r\n' < "$STATE")"
    if [[ -d "$saved/.obsidian" ]]; then
      prompt "使用已保存的 vault: $saved"
      printf '%s' "$saved"
      return
    fi
  fi

  # macOS: native folder picker (best for double-click .command)
  if [[ "$(uname -s)" == "Darwin" ]] && command -v osascript >/dev/null 2>&1; then
    prompt "请在弹窗里选择你的 Obsidian vault 文件夹（里面应有 .obsidian）…"
    local chosen
    chosen="$(osascript <<'APPLESCRIPT'
try
  set theFolder to choose folder with prompt "选择你的 Obsidian vault 文件夹（目录内应有隐藏的 .obsidian）"
  return POSIX path of theFolder
on error
  return ""
end try
APPLESCRIPT
)" || true
    chosen="${chosen%$'\n'}"
    chosen="${chosen%/}"
    if [[ -n "$chosen" ]]; then
      printf '%s' "$chosen"
      return
    fi
    prompt "未选择文件夹，改为手动输入路径。"
  fi

  prompt ""
  prompt "请输入你的 Obsidian vault 绝对路径"
  prompt "（Finder 里对该文件夹按住 Option 右键 → 拷贝 … 作为路径名）"
  prompt "示例: /Users/你/Documents/MyVault"
  local path=""
  while [[ -z "$path" ]]; do
    read -r -p "vault 路径: " path >&2 || true
    path="${path/#\~/$HOME}"
    path="${path%\"}"
    path="${path#\"}"
    path="${path%/}"
  done
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
print("enabled", file=sys.stderr)
PY
}

main() {
  prompt "========================================"
  prompt "  Obsidian 7-Repo Board 安装程序"
  prompt "========================================"
  prompt ""

  local vault
  vault="$(pick_vault "${1:-}")"
  [[ -n "$vault" ]] || die "未提供 vault 路径"
  [[ -d "$vault" ]] || die "目录不存在: $vault"
  [[ -d "$vault/.obsidian" ]] || die "看起来不像 vault（缺少 .obsidian）: $vault
提示: vault = Obsidian 里 Open folder as vault 的那个文件夹"
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

  prompt ""
  prompt "======= 安装完成 ======="
  prompt ""
  prompt "现在去 Obsidian 里看："
  prompt "  1. 切回 Obsidian（如已打开，点一下窗口刷新文件列表）"
  prompt "  2. 左侧文件列表打开:  7-Repo-Board / 7-Repo-Board.canvas"
  prompt "  3. 若没有 CSS: 设置 → 外观 → CSS 代码片段 → 勾选 7-repo-board"
  prompt ""
  prompt "文件已写入:"
  prompt "  $vault/7-Repo-Board/"
  prompt ""
}

main "$@"
