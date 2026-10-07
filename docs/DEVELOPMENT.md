# 开发与复现检查

首发正式支持范围为macOS Apple Silicon（arm64）原生源码安装。CI使用的检查工具或Linux runner不构成Linux应用发行支持；首发包和审阅树均不包含容器部署入口。

归档包含预编译Vue界面，运行只需Python标准库和浏览器；重建界面需要Node 22.12+及锁定npm依赖。前端依赖许可和漏洞检查须单独完成。

打包和安装测试前先构建：

```sh
npm ci --ignore-scripts --prefix frontend/owner-ui
npm run build --prefix frontend/owner-ui
```

打包时核对源码及产物哈希；修改源码后必须重新构建。以下依赖仅用于开发测试。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend/src .venv/bin/python -m pytest -q -p no:cacheprovider tests/owner tests/install/test_owner_package.py tests/install/test_owner_archive_audit.py tests/install/test_owner_release_tree.py
.venv/bin/python tests/install/verify_owner_delivery.py
```

浏览器检查需要 Node 22+ 和 Playwright Chromium：

```sh
npm ci --ignore-scripts
npx playwright install chromium
OWNER_PYTHON="$PWD/.venv/bin/python" npm run test:vue
OWNER_PYTHON="$PWD/.venv/bin/python" npm run test:planning
OWNER_PYTHON="$PWD/.venv/bin/python" npm run test:diagnosis
OWNER_PYTHON="$PWD/.venv/bin/python" npm run test:ui
OWNER_PYTHON="$PWD/.venv/bin/python" npm run test:business
```

`OWNER_PYTHON` 可指定已有 Python 解释器；`OWNER_PLAYWRIGHT_PACKAGE` 可指定已有安装的 package.json 绝对路径。测试在系统临时目录创建合成账号/数据，退出清理，不使用默认账本。截图输出到 qa，不能把测试截图当真实服务验收。

`verify_owner_delivery.py`只执行独立原生源码安装、重启和恢复，使用临时合成数据目录；不提供容器参数。

```sh
python3 tools/package_owner.py --output .packages/owner-source.tar.gz
python3 tools/audit_owner_package.py .packages/owner-source.tar.gz
```

打包为确定性白名单，不含运行状态。GitHub 候选树由 `tools/prepare_owner_release.py` 在不存在的新目录生成，保留逐文件清单；不初始化 Git、不创建仓库、不发布。

默认启动使用随包提供、启动时核验的新版 Vue 界面：

```sh
python3 start_owner.py --data-dir /absolute/path/to/new-test-data
```

归档自带源码及已编译资源，解包运行无需安装 Node。缺少或损坏构建会在创建账本前拒绝启动；可用 `--ui-build` 明确指定另一份经过验证的构建。

`test:vue` 验证默认启动、新版设置/导入导出及所有页面；`test:ui` 和 `test:business` 保留旧界面功能回归，使用测试专用运行器，不能作为新版视觉验收证据。CI 同时执行这些用例；本地通过不等于远程 CI 或正式发布通过。

`test:planning` 使用正式启动入口、动态回环端口和独立临时账本，验证有序多笔试算与不记账、配置层版本/归档/过期价格失效、计划成交快照/差异提示/撤销历史，以及明确确认实际成交与原子关联，包含1440/390/320宽度。四个流程逐个执行，任一失败即停止。测试关闭服务并清理临时数据；结果及截图保存在qa。

`test:diagnosis` 验证缺资料状态、完整评分、编辑清除预览、固定历史与比较、三种宽度及规则入口重载；收盘调度未包含在当前检查中。
