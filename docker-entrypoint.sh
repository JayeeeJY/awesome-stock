#!/bin/sh
# Prepare the ledger directory, then start the same entrypoint as a local install.
# The process binds 0.0.0.0 so `docker run -p 4322:4322` can reach it. The app
# still accepts only loopback Host headers, and the directory must be mode 700.
set -eu
umask 077
mkdir -p /data
chmod 700 /data
python3 - <<'PY'
import os
import stat
import sys
mode = os.stat("/data").st_mode
if mode & 0o077:
    print(
        f"数据目录 /data 其他用户仍可访问（权限 {stat.S_IMODE(mode):o}）。应用要求 700。",
        file=sys.stderr,
    )
    print(
        "请换一个空目录挂到 /data，或改用命名卷：docker run -p 4322:4322 -v awesome-stock-data:/data IMAGE",
        file=sys.stderr,
    )
    sys.exit(1)
PY
exec python3 /app/start_owner.py --host 0.0.0.0 --data-dir /data "$@"
