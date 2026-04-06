# Directory submission kit — Agentic Swarm Marketplace

Use this file when submitting to **Awesome MCP**, **Smithery**, **Glama**, **TAAFT**, **Agent.ai**, **CDP / Base**, **Farcaster**, and similar. Paths refer to this repo: [`Hobie1Kenobi/agentic-crypto-swarm-prototype`](https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype).

## Canonical URLs

| Asset | URL |
|--------|-----|
| **Live dashboard & docs (GitHub Pages)** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/ |
| **Agent / crawler overview** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/llms.txt |
| **MCP setup (Cursor / Claude)** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/mcp-integration.md |
| **Live tunnel & seller origins** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/endpoints.json |
| **T54 OpenAPI (raw)** | https://raw.githubusercontent.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/master/documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml |
| **ai-plugin.json (Pages)** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/.well-known/ai-plugin.json |
| **mcp-manifest.json (repo root)** | https://raw.githubusercontent.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/master/mcp-manifest.json |
| **smithery.yaml (Smithery wizard)** | https://raw.githubusercontent.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/master/smithery.yaml |

---

## Tagline (max ~50 characters)

**Multi-rail x402 agent swarm: XRPL, Base USDC, Celo, Olas.**

(49 characters)

---

## Short description (max ~200 characters)

**Hierarchical agents for paid API commerce: T54 XRPL x402 seller, Base USDC x402, Celo marketplace, Olas intake. MCP stdio server, OpenAPI SKUs, HTTP 402 + broker. GitHub Pages + tunnel registry.**

(199 characters)

---

## Long description (Markdown)

**Agentic Swarm Marketplace** is a hierarchical multi-agent stack built for **machine-paid** commerce — not trading or speculation. It exposes **HTTP 402** + **x402** seller APIs (notably **T54 on XRPL** with the T54 facilitator), **Base USDC** x402 / Bazaar-style routes, **Celo** private settlement and marketplace contracts, and **Olas**-style public intake when configured.

**Payments & rails:** Buyers hit priced routes; the stack routes settlement across **XRPL (XRP)** and **EVM (USDC / CELO)** depending on SKU and deployment. An **x402 broker client** pays 402 invoices from agent processes (mock, XRPL testnet/mainnet, Xaman, or Base USDC modes — see repo `.env.example`).

**MCP:** A **stdio MCP server** (`scripts/mcp_server.py`) exposes T54 **OpenAPI** operations as LLM tools so **Cursor** and **Claude Desktop** can call your seller with automatic 402 handling when env is set. Integration guide: **mcp-integration.md** on GitHub Pages.

**Discovery:** External commerce discovery uses a growing provider catalog; x402 Scout–style snapshots in-repo reference on the order of **~1,175** cataloged third-party services in chunk metadata (see `external_commerce_data/x402scout-catalog-chunks/`) — your **T54 seller SKUs** are a separate, first-party OpenAPI catalog.

**Public machine-readable entry points:** **llms.txt**, **endpoints.json**, and **.well-known/ai-plugin.json** on Pages.

---

## SEO tags (comma-separated)

AI Agent, MCP, x402, HTTP 402, Crypto, Web3, Base, USDC, XRPL, T54, Celo, Olas, DeFi, Agent Commerce, LangChain, Autonomous Agents, Machine Payments, OpenAPI

---

## Copy-paste: GitHub repo URL

```
https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype
```

---

## Copy-paste: MCP Cursor config (local clone)

See [`mcp-integration.md`](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/mcp-integration.md) for full detail. Minimal shape:

```json
{
  "mcpServers": {
    "swarm-t54-x402": {
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "${workspaceFolder}/scripts/run-mcp-t54.ps1"
      ]
    }
  }
}
```

---

## Per-directory notes

### Awesome MCP Servers (GitHub)

- **Started:** Step-by-step fork/PR + exact README line → **[submissions/awesome-mcp-servers-PR.md](submissions/awesome-mcp-servers-PR.md)**. Upstream: [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers). **Claim or add the server on Glama first** so the badge URL in the PR resolves (maintainers often require it).

### Smithery.ai / Glama.ai

- **Smithery one-click:** Repo root includes **`smithery.yaml`** — `startCommand.type: stdio` with a **`commandFunction`** that runs **`uv`** from `packages/agents` with `--with mcp[cli]` and `--with pyyaml`, then `python -u ../../scripts/mcp_server.py`. Config fields are **optional** (empty defaults + `mock`) so tool listing works without secrets.
- Submit the **GitHub repo URL**; the wizard should detect **`smithery.yaml`** automatically.
- Also submit **`mcp-manifest.json`** if a form asks for package-style metadata.
- **Glama:** use the same repo link + **`mcp-manifest.json`** per their form.
- **Local dev without `uv`:** use `python -u scripts/mcp_server.py` from repo root (see **mcp-integration.md**) or **PowerShell** + `scripts/run-mcp-t54.ps1` on Windows.

### ThereIsAnAIForThat.com / Agent.ai

- **TAAFT:** Pre-filled copy for their form is in **[submissions/taaft-form-copy.md](submissions/taaft-form-copy.md)** — submit at [theresanaiforthat.com/s/submit/](https://theresanaiforthat.com/s/submit/).
- **Agent.ai:** Their marketplace targets agents built **on platform**; see **[submissions/agent-ai-notes.md](submissions/agent-ai-notes.md)** for realistic options (suggest-agent, future builder listing, parallel directories).
- General: use **tagline**, **short / long description** from this kit; **GitHub Pages** as live URL; **repo** as source; categories **Developer Tools**, **Crypto**, **Finance**, **Automation** where applicable.

### CDP (Coinbase Developer Platform) / Base

- Tag **Base** and **USDC** in descriptions; link **Base** x402 endpoints from **endpoints.json** when live.
- If they have an **AgentKit** or ecosystem list, submit **repo + Pages + OpenAPI**.

### Awesome-Olas / Fetch.ai Almanac / Farcaster

- **Olas:** point to **hybrid / public adapter** docs under `documentation/` and `MARKET_MODE`.
- **Farcaster:** not a form — share **Frames** or **casts** linking **Pages** + **llms.txt**; join `/agents` channels with the short description.

### e2b.dev / LangChain Hub

- Publish **templates** as separate artifacts (notebook or repo template); link this monorepo as **source** and **OpenAPI** + **MCP** as integration paths.

---

## In-repo submission artifacts (started)

| Target | File |
|--------|------|
| **Awesome MCP** (PR to punkpeye list) | [submissions/awesome-mcp-servers-PR.md](submissions/awesome-mcp-servers-PR.md) |
| **TAAFT** (form copy) | [submissions/taaft-form-copy.md](submissions/taaft-form-copy.md) |
| **Agent.ai** (expectations + blurb) | [submissions/agent-ai-notes.md](submissions/agent-ai-notes.md) |

---

## After you submit

1. **Push** `master` so **GitHub Pages** deploys `docs/` (includes **`docs/.well-known/ai-plugin.json`**).
2. Verify: `https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/.well-known/ai-plugin.json` returns JSON.
3. **Search Console:** keep **sitemap.xml** submitted; optional URL inspection for new paths.

---

## Files generated in this repo

| File | Role |
|------|------|
| `mcp-manifest.json` | Smithery / Glama–style MCP package metadata + `python` launch |
| `smithery.yaml` | Smithery **stdio** `commandFunction` + optional `configSchema` (wizard / one-click) |
| `docs/.well-known/ai-plugin.json` | Legacy ChatGPT plugin–style metadata + OpenAPI URL (**served on Pages**) |
| `.well-known/ai-plugin.json` | Same JSON at repo root for tools that scan the repository |
| `submissions/*.md` | Awesome MCP PR, TAAFT copy, Agent.ai notes |

**Note:** GitHub Actions deploys **`docs/`** only. The live **ai-plugin** URL for directories must use the **Pages** path above, not raw GitHub path under `.well-known` at repo root.
