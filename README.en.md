# Awesome Stock Community

**An AI-native personal investing workspace that evolves with your experience.**

**Powered by Atom Awareness**<br>
Independent AI Product & Research Studio.

**Evolve Every Trade.**

Released · Community v1.0.1 · Runs locally · macOS Apple Silicon

Connect your assets, research, decisions, plans and reviews. Preserve the basis of each decision and develop an investing approach that fits you.

Ask questions, follow up or explicitly attach your own material in Ask Awesome. You confirm the outbound content and model call, and review AI replies as drafts. Decisions and actions remain yours. Core workflows need no model or market-data API.

[Download Community v1.0.1](https://github.com/JayeeeJY/awesome-stock/releases/tag/v1.0.1) · [Get started](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/docs/QUICKSTART.md) · [Configure optional services](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/docs/OPTIONAL_PROVIDERS.md)

Supports macOS Apple Silicon and Python 3.10+. Project-owned code is AGPL-3.0-only.

![Community cockpit: asset facts and items to review](docs/screenshots/cockpit.png)

*Screenshots were captured on 2026-10-07 and show the released Community v1.0.1 interface. Accounts, symbols, trades, prices, research and plans are synthetic examples, not a real portfolio or a performance claim.*

## Turn scattered records into a process you can revisit

You may track holdings in one place, write research elsewhere, and keep buy or sell reasons in your head. Later, it becomes difficult to reconstruct why you made a decision.

Awesome Stock helps preserve that connection:

**Asset facts → Research evidence → Investment decision → Execution plan → Actual trade → Decision review**

- **Understand where your money is.** Keep clear account, cash, holding and trade records; see when prices or exchange rates are missing.
- **Preserve the basis of a decision.** Record support, counterarguments and invalidation conditions, along with historical versions.
- **Check your plan before acting.** Review budget, cash and your own risk limits before deciding whether to execute.
- **Review the process afterward.** Revisit the original evidence, separate adherence to the plan from its outcome, and record what you learned.

## A complete workflow in Community

### 1. Start with your assets

The cockpit and portfolio bring together accounts, holdings, valuation and review items. Different accounts and currencies retain their own facts. Manual price snapshots include dates and sources.

![Portfolio: accounts, costs and price snapshots](docs/screenshots/portfolio.png)

### 2. Turn an opinion into research you can check

Start with saved local material. Separate facts from inferences, and record both supporting and opposing evidence. Notes can be revised while references to older versions preserve the original content. A decision includes the evidence that could change your mind.

![Research: local material and evidence gaps](docs/screenshots/research.png)

<details>
<summary>See versioned research notes</summary>

![Research notes and versions](docs/screenshots/notes.png)

</details>

### 3. Write a plan before taking action

Record the basis, trigger, steps and stop conditions. Check assumptions with allocation, staged-budget and pre-trade scenarios. Execute independently, then link your recorded trade to the plan.

![Plans: fixed decision references and execution steps](docs/screenshots/plan.png)

### 4. Review the original decision

Keep an investing journal and revisit the research and decision you held at the time. Record whether you followed the plan, whether an outcome is observable, and what to check next. Community rules are maintained manually by the user.

![Decision review: preserve the process and its evidence](docs/screenshots/evolve-review.png)

### 5. Add AI when it helps

Start with a question, or bring current-page material into the conversation. Use Ask Awesome to explain concepts, check the basis of a decision or identify missing evidence.

![Ask Awesome: free questions and optional material](docs/screenshots/ask-awesome.png)

Responses are for you to read, check and organize. Model connections, outbound content and costs are explained below.

<details>
<summary>See Academy and a mobile-width layout</summary>

![Academy: investing knowledge and diagrams](docs/screenshots/academy.png)

![Portfolio at mobile browser width](docs/screenshots/portfolio-mobile.png)

*This demonstrates responsive browser layout, not a released mobile application. The supported installation platform remains macOS Apple Silicon.*

</details>

## AI works with your material; you own the judgment and action

In Community, AI-native collaboration means help understanding and checking material while preserving your control:

- **Ask freely and follow up.** Ask Awesome has a free-text conversation box for investing concepts or discussion of your material.
- **Choose the context.** Explicitly attach current-page material and review the question, material and conversation history before sending. Opening the assistant does not call a model.
- **Choose your service and check the answer.** Use your own DeepSeek or OpenAI API key, or local Ollama. Model responses are assistive drafts, not automatically confirmed decisions, plans or trades.

Models are optional. Ledger, research, planning and review workflows work independently. Data is local by default; only content you confirm for sending is passed to your configured model service.

## Start without an API

Create a local login and capital account, record opening cash and trades, save research, and enter verified manual prices with sources. CSV imports trades after preview, not quote history.

Add optional services when you need them:

- **Models:** your own DeepSeek or OpenAI API account, or user-installed Ollama. API usage charges go to your provider account.
- **Daily market data:** your own Alpha Vantage access for US/A-share data, or EODHD access for Hong Kong. Inspect the query result before explicitly saving it. Yahoo key-free data is deferred; no shared project key or subsidy is provided.
- **Data:** local by default, with a configurable directory and backups. Keys stay in server process memory and are excluded from backups and exports. Full backups are unencrypted and need safe storage.

Download the named source archive from [Releases](https://github.com/JayeeeJY/awesome-stock/releases/tag/v1.0.1), extract it, enter `awesome-stock-owner`, and follow the [installation guide](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/OWNER_INSTALL.md). It includes the compiled interface and needs no Node runtime, database service or model to start.

There are no default credentials. Windows, Linux, Intel Mac, Docker and standalone mobile clients are outside the first-release support scope. Community v1.0.1 has no broker synchronization, automated trading, short-position or options accounting.

## Make your experience useful

If you want to manage your own investing records, preserve the basis for your decisions and learn from each review, try Community.

[Download](https://github.com/JayeeeJY/awesome-stock/releases/tag/v1.0.1) · [Read the guide](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/docs/QUICKSTART.md) · [Share feedback](https://github.com/JayeeeJY/awesome-stock/issues) · [Follow releases](https://github.com/JayeeeJY/awesome-stock/releases)

### Built through everyday use, continually improved

Awesome Stock is a personal investing product from Atom Awareness, created and maintained by Evan. I will keep improving Community through my own everyday use, and welcome questions, ideas and feedback from yours.

You can reach me through:

| Channel | Contact |
| --- | --- |
| WhatsApp username | `Jiayong987` |
| WeChat ID | `ChuanLin007` |
| Email | [316600025@qq.com](mailto:316600025@qq.com) |

The first release accepts issues and product feedback, not external code contributions. Do not publish API keys, real holdings, transaction details or backups. Security issues should use [GitHub private vulnerability reporting](https://github.com/JayeeeJY/awesome-stock/security/advisories/new).

Copyright (c) 2026 Evan. Project-owned code is [AGPL-3.0-only](https://github.com/JayeeeJY/awesome-stock/blob/v1.0.1/LICENSE); third-party inputs retain their licenses. No separate commercial license is offered for this release. See repository documentation for installation, privacy, security and validation details.

## Sign in

![Community sign-in: stars and particle connections](docs/screenshots/login.png)

Create your local account on first use; sign in on subsequent visits. The page features a midnight-blue starfield with particle connections and shows static stars when reduced motion is enabled.

[简体中文](README.md)

---

Awesome Stock Community / Powered by Atom Awareness<br>
Independent AI Product & Research Studio · Make complexity perceivable.
