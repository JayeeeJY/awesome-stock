#!/bin/bash
# macOS double-click entry — folder picker + install.
cd "$(dirname "$0")" || exit 1
chmod +x ./install.sh 2>/dev/null || true
echo
./install.sh
status=$?
echo
if [[ $status -eq 0 ]]; then
  echo "可以关闭本窗口了。回到 Obsidian 打开 7-Repo-Board.canvas"
else
  echo "安装未成功（退出码 $status）。把上面的错误发我即可。"
fi
echo
read -r -p "按回车关闭…" _
exit "$status"
