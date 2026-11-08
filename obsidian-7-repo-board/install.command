#!/bin/bash
# macOS double-click entry — runs install.sh in Terminal.
cd "$(dirname "$0")" || exit 1
chmod +x ./install.sh 2>/dev/null || true
./install.sh
echo
read -r -p "按回车关闭…" _
