# 路线图

没有排期。这里只写仓库里已经对得上的事，以及还没做、也不承诺日期的事。

## 已经有的

- 本地账本：账户、成交、研究、判断、计划和复盘。数据在你自己的目录里，不配模型也能用。
- macOS Apple Silicon 上用 `python3 start_owner.py` 启动（Python 3.10+）。这是目前验证过的原生安装。
- 可选 DeepSeek、OpenAI，或本机 Ollama（`127.0.0.1:11434`）。
- 实验性 Docker：仓库根目录有 Dockerfile。容器内监听 `0.0.0.0:4322`，数据在 `/data`。v1.1.0 起，`v*` 标签会把镜像发布到 `ghcr.io/jayeeejy/awesome-stock`（`:v1.1.0`、`:1.1.0`、`:latest`）。v1.0.0 和 v1.0.1 没有这张镜像。发行源码包仍然不含 Dockerfile。

## 还没做

- 在 Windows 和 macOS 的 Docker Desktop 上再确认数据目录权限。应用要求目录是 700。Linux 上的绑定挂载由容器入口处理。
- Windows、Linux 和 Intel Mac 的原生安装说明。程序只用 Python 标准库，但这三个环境还没有被标成正式支持。
- 录一段 `docs/screenshots/demo.gif`：记一笔交易，写下判断，让 AI 找反方证据，再复盘。用合成数据。README 里现在先放驾驶舱截图。
- 让容器里的「本机 Ollama」连到宿主机。现在写死的是容器内的 `127.0.0.1`，宿主机上的 Ollama 连不上。
- 在仓库设置里打开 GitHub Discussions，并加上「提问」「想法」「使用方式」这几类。

## 明确不做

不荐股，不自动下单，不做券商同步，也不把这个本地账本变成公网多用户服务。

---

# Roadmap

No dates. This is what the repository can already do, and what is realistic but not scheduled.

## Already here

- A local journal for accounts, trades, research, decisions, plans and reviews. It runs without a model.
- `python3 start_owner.py` on macOS Apple Silicon (Python 3.10+). That is the native install that has been checked.
- Optional DeepSeek, OpenAI, or Ollama on `127.0.0.1:11434`.
- Experimental Docker from the Dockerfile in the repository root. Inside the container the server listens on `0.0.0.0:4322` and stores data in `/data`. From v1.1.0, a `v*` tag publishes `ghcr.io/jayeeejy/awesome-stock` (`:v1.1.0`, `:1.1.0`, `:latest`). The v1.0.0 and v1.0.1 releases do not include that image. The source archive still has no Dockerfile.

## Not done yet

- Recheck data-directory permissions (mode 700) on Docker Desktop for Windows and macOS. On Linux, the container entrypoint handles a bind mount.
- Native install notes for Windows, Linux and Intel Mac. The app is standard-library Python, and those systems are not a supported install yet.
- Record `docs/screenshots/demo.gif` with synthetic data: log a trade, write the thesis, ask for counter-evidence, then review. The README uses the cockpit screenshot until then.
- Point in-container Ollama at the host. It currently uses `127.0.0.1` inside the container.
- Turn on GitHub Discussions in the repository settings, with categories for questions, ideas and workflows.

## Out of scope

This project does not pick stocks, place orders, sync a broker, or run as a public multi-user service.
