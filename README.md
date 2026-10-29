<div align="center">

# 📒 Awesome Stock

**不荐股的 AI 投资复盘工作台：记下每笔交易的依据，事后复盘，越投越有方法。**

数据全在你的电脑上 · 可接 DeepSeek / OpenAI / 本地 Ollama · 不配 API 也能用

[![Release](https://img.shields.io/github/v/release/JayeeeJY/awesome-stock)](https://github.com/JayeeeJY/awesome-stock/releases)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Stars](https://img.shields.io/github/stars/JayeeeJY/awesome-stock?style=social)](https://github.com/JayeeeJY/awesome-stock/stargazers)

简体中文 | [English](README.en.md)

<!-- 演示动图尚未录制。录好后把下面这张图换成 docs/screenshots/demo.gif。 -->

![Community 驾驶舱：从资产事实与待办开始](docs/screenshots/cockpit.png)

</div>

> 你是不是也这样：持仓在券商 App，研究在备忘录，买卖理由全靠记忆。等到亏了，却想不起来当初为什么买。

**Awesome Stock 把这条线连起来：** 资产 → 研究证据 → 投资判断 → 执行计划 → 实际成交 → 决策复盘

- 🧾 **看清钱在哪**：多账户、多币种的持仓和成交，缺价格、缺汇率会直接提示
- 🔍 **判断有依据**：支持证据、反方观点、失效条件和历史版本一起保存
- 📋 **行动前先核对**：预算、现金、风险约束试算，执行与否由你决定
- 🔁 **事后能复盘**：把「是否按计划执行」和「结果好坏」分开看，经验越攒越多
- 🤖 **AI 只当助手**：Ask Awesome 帮你理解材料、找证据缺口；发送什么内容由你确认，不自动下单

## 🚀 三步跑起来（macOS Apple Silicon，Python 3.10+）

原生安装目前在 macOS Apple Silicon 上验证。发行包自带已编译界面，不需要 Node、数据库或模型。

```sh
# 1. 下载并解压 Release 中的源码包
# https://github.com/JayeeeJY/awesome-stock/releases/latest
cd awesome-stock-owner
# 2. 启动（无需 Node、数据库或模型）
python3 start_owner.py --data-dir "$HOME/Awesome-Stock-Data" --open-browser
# 3. 浏览器打开 http://127.0.0.1:4322/ledger ，创建本地账号
```

`/ledger` 会进入交易流水。默认端口是 4322；被占用时加上 `--port 4324`，并打开对应地址。没有默认账号密码。

## Docker（Linux、Windows、macOS）

容器里的服务监听 `0.0.0.0:4322`，账本写在 `/data`。镜像名是 `ghcr.io/jayeeejy/awesome-stock`。推送 `v*` 标签后，GitHub Actions 会用 `GITHUB_TOKEN` 构建并发布。v1.0.0 和 v1.0.1 还没有这张镜像；下一个版本标签出来之前，请自己构建。

```sh
# 已发布镜像（下一个 v* 标签发布之后；在此之前这张镜像还不存在）
docker run -p 4322:4322 -v "$HOME/Awesome-Stock-Data:/data" ghcr.io/jayeeejy/awesome-stock

# 自己构建。需要克隆本仓库，发行包里没有 Dockerfile。
git clone https://github.com/JayeeeJY/awesome-stock.git
cd awesome-stock
docker build -t awesome-stock .
docker run -p 4322:4322 -v "$HOME/Awesome-Stock-Data:/data" awesome-stock
```

然后打开 http://127.0.0.1:4322/ledger 。`-p 4322:4322` 会在这台电脑的所有网卡上监听；只想给自己用时，改成 `-p 127.0.0.1:4322:4322`。启动时会把 `/data` 收成仅本人可读（权限 700）。Windows PowerShell 可以把卷写成 `-v "${env:USERPROFILE}/Awesome-Stock-Data:/data"`。

容器里的「本机 Ollama」指向容器自己的 `127.0.0.1`，不是宿主机上的 Ollama。DeepSeek 和 OpenAI 走容器的出站网络，Key 仍然只留在进程内存里。

📖 [第一次使用](docs/QUICKSTART.md) · ⚙️ [模型与行情配置](docs/OPTIONAL_PROVIDERS.md) · 💬 [讨论区](https://github.com/JayeeeJY/awesome-stock/discussions) · 🗺️ [路线图](ROADMAP.md)

> ⭐ 如果它对你有帮助，点个 Star，方便跟进后续版本（包括 Windows 原生安装）。

*界面截取于 2026-10-07，来自 Community v1.0.1。账号、标的和金额都是合成示例，不代表真实持仓或收益，也不构成任何投资建议。*

## 在 Community 里，走完一次投资工作流程

### 1. 先了解资产，而不是从一条孤立的信息开始

驾驶舱和持仓工作区把资金账户、持仓、估值与待核对事项放在一起。多账户、多币种保留各自的事实；手工价格带日期和来源，方便核账。

![持仓总览：账户、成本与价格快照](docs/screenshots/portfolio.png)

### 2. 把观点变成可以核对的研究

从保存的本地材料开始研究，记录事实与推断、支持与反方证据。研究笔记可以修订，已有版本引用保留当时的内容；判断不只是一句“看好”，还包括哪些证据可能让你改变主意。

![个股研究：本地材料、判断范围与证据缺口](docs/screenshots/research.png)

<details>
<summary>查看研究笔记与版本界面</summary>

![研究笔记：保留论点与版本](docs/screenshots/notes.png)

</details>

### 3. 在实际行动前，把计划写清楚

记录计划依据、触发条件、分步执行方式与停止条件。用资产配置、分批预算和交易前试算核对假设；自行执行之后，再把实际成交关联到计划。

![投资计划：固定判断依据与执行步骤](docs/screenshots/plan.png)

### 4. 复盘当时的决定，积累自己的经验

用投资日记记录观察，在决策复盘中回看当时的研究与判断。记录过程是否遵守计划、结果是否已经出现，以及下一步需要核对什么。Community 的规则由用户手工维护。

![进化工作区：投资日记与决策复盘](docs/screenshots/evolve-review.png)

### 5. 需要时，让 AI 协助你理解材料

从一个问题开始，也可以把当前页面的材料带入对话。用 Ask Awesome 梳理概念、核对依据，或找出还需要补充的证据。

![Ask Awesome：自由提问与可选材料](docs/screenshots/ask-awesome.png)

AI 回复供你阅读、核对和整理；模型连接、发送内容与费用说明见下文。

<details>
<summary>查看学院与手机宽度界面</summary>

![学院：阅读投资知识与图示](docs/screenshots/academy.png)

![手机宽度的持仓界面](docs/screenshots/portfolio-mobile.png)

*手机宽度截图展示浏览器界面的响应式布局，不代表已经发布独立手机应用。*

</details>

## AI 围绕你的材料协作，判断与行动由你掌握

AI 原生在 Community 中的具体体验，是让模型帮助理解和核对材料，同时保留你的控制权：

- **直接提问，也可以继续追问。** Ask Awesome 有自由输入对话框，可以讨论投资概念，也可以围绕已有材料展开交流。
- **上下文由你选择。** 主动附加当前页面材料，发送前核对问题、材料与对话历史；打开助手不会自动调用模型。
- **服务由你配置，结论由你核对。** 使用自己的 DeepSeek、OpenAI API Key 或本地 Ollama。模型回复是辅助草稿，不自动成为已确认的判断、计划或交易。

模型是可选连接，账本、研究、计划与复盘可以独立使用。数据默认保存在本机；只有你确认发送的内容会交给所配置的模型服务。

## 不配 API，也可以先用起来

先创建本地账号与资金账户，记录期初现金、成交和研究，再保存带来源的手工价格。CSV 用于成交导入，导入前有预览；不是行情历史导入。

如果需要 AI 或自动行情查询，再配置自己的服务：

- **模型：** DeepSeek、OpenAI 或自行安装的 Ollama；云端费用由你的供应商账号承担。
- **日级行情：** 自有 Alpha Vantage（美股/A股）或 EODHD（港股）账号与权限；查询后核对，再明确保存。首发没有 Yahoo 免 Key 行情，不提供统一 Key 或代付。
- **数据：** 默认保存在本机，可指定独立目录并创建备份。Key 只留在服务进程内存，不进入备份或导出；完整备份未加密，需要妥善保管。

下载 [Release 中的命名源码包](https://github.com/JayeeeJY/awesome-stock/releases/tag/v1.0.1)，解压进入 `awesome-stock-owner`，按[安装指南](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/OWNER_INSTALL.md)运行。包自带编译界面，无需 Node、数据库服务或模型即可启动。

没有默认账号密码。原生安装目前在 macOS Apple Silicon 上验证。Docker 可以在 Linux、Windows 和 macOS 上跑同一套本地服务，见上文，仍是实验支持。Intel Mac 原生安装和独立移动客户端还不在正式支持范围。当前版本不支持券商同步、自动下单、空头或期权记账。

## 一起让投资经验变得更有价值

如果你愿意自己管理投资记录、认真保留判断依据，并从每次决策中积累经验，欢迎试用 Community。

[下载稳定版](https://github.com/JayeeeJY/awesome-stock/releases/tag/v1.0.1) · [阅读使用指南](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/docs/QUICKSTART.md) · [提出问题与产品反馈](https://github.com/JayeeeJY/awesome-stock/issues) · [关注版本进展](https://github.com/JayeeeJY/awesome-stock/releases)

### 由真实使用驱动，持续迭代

Awesome Stock 是 Atom Awareness 工作室的个人投资产品，由 Evan 创建并维护。我会基于自己的日常使用，持续打磨 Community 的功能与体验，也欢迎你分享使用中的问题、想法与建议。

使用上的问题请到 [GitHub Discussions](https://github.com/JayeeeJY/awesome-stock/discussions)，缺陷和功能想法请开 [Issue](https://github.com/JayeeeJY/awesome-stock/issues)。想改代码的话，先在 Issue 里说清楚，再提 Pull Request，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

Issue 和讨论都欢迎。请勿公开 API Key、真实持仓、交易明细或备份；安全问题请使用 [GitHub 私密漏洞报告](https://github.com/JayeeeJY/awesome-stock/security/advisories/new)。

Copyright (c) 2026 Evan。项目自有代码采用 [AGPL-3.0-only](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/LICENSE)，第三方保留原许可；本次不提供独立商业许可。安装、隐私、安全与验证细节见仓库文档。

## 登录界面

![Community 登录页：星光与粒子连线](docs/screenshots/login.png)

首次使用创建自己的本地账号；已有账号直接登录。深蓝星空与粒子连线构成登录页背景，系统开启「减少动效」时保留静态星光。

[English](README.en.md)

---

Awesome Stock Community / Powered by Atom Awareness<br>
Independent AI Product & Research Studio · Make complexity perceivable.
