# Directory submission kit — Agentic Swarm Marketplace

Use this file when submitting to **Awesome MCP**, **Smithery**, **Glama**, **TAAFT**, **Agent.ai**, **CDP / Base**, **Farcaster**, and similar. Paths refer to this repo: [`Hobie1Kenobi/agentic-crypto-swarm-prototype`](https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype).

## Canonical URLs

| Asset | URL |
|--------|-----|
| **Live dashboard & docs (custom domain)** | https://www.agentic-swarm-marketplace.com/ |
| **Same site (github.io mirror)** | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/ |
| **Agent / crawler overview** | https://www.agentic-swarm-marketplace.com/llms.txt |
| **MCP setup (Cursor / Claude)** | https://www.agentic-swarm-marketplace.com/mcp-integration.md |
| **Public API + tunnel registry (`endpoints.json`)** | https://www.agentic-swarm-marketplace.com/endpoints.json |
| **Production API host (x402 / T54 / marketplace via tunnel)** | https://api.agentic-swarm-marketplace.com/health |
| **T54 OpenAPI (raw)** | https://raw.githubusercontent.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/master/documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml |
| **ai-plugin.json (Pages)** | https://www.agentic-swarm-marketplace.com/.well-known/ai-plugin.json (mirror: https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/.well-known/ai-plugin.json) |
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

**Before expecting inbound paid traffic:** set **stable HTTPS** `X402_SELLER_PUBLIC_URL` and `T54_SELLER_PUBLIC_BASE_URL`, run **`npm run docs:sync-endpoints`**, commit **`docs/endpoints.json`**, and use **Base mainnet** (`eip155:8453`) and **XRPL mainnet** (`xrpl:0`) for real settlement — see **[documentation/PUBLIC_MAINNET_OPERATIONS.md](documentation/PUBLIC_MAINNET_OPERATIONS.md)**.

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

See [`mcp-integration.md`](https://www.agentic-swarm-marketplace.com/mcp-integration.md) (or [github.io mirror](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/mcp-integration.md)) for full detail. Minimal shape:

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

**Step-by-step:** **[submissions/SMITHERY_GLAMA_TAAFT.md](submissions/SMITHERY_GLAMA_TAAFT.md)** — Glama first (Awesome MCP badge), then Smithery (GitHub **`smithery.yaml`** and/or URL **`https://api.agentic-swarm-marketplace.com/mcp`**), Cloudflare **`SmitheryBot`** note.

- **Smithery:** Repo root **`smithery.yaml`** — `startCommand.type: stdio` with **`commandFunction`** running **`uv`** from `packages/agents` with `--with mcp[cli]` and `--with pyyaml`, then `python -u ../../scripts/mcp_server.py`. Config fields are **optional** (empty defaults + `mock`). URL publish: **[smithery.ai/new](https://smithery.ai/new)** for hosted Streamable HTTP MCP.
- Submit the **GitHub repo URL** where the wizard asks; **`mcp-manifest.json`** for package-style metadata.
- **Glama:** **[glama.ai/mcp/servers](https://glama.ai/mcp/servers)** → **Add Server** with the same repo link.
- **Local dev without `uv`:** `python -u scripts/mcp_server.py` from repo root (see **mcp-integration.md**) or **PowerShell** + `scripts/run-mcp-t54.ps1` on Windows.

### ThereIsAnAIForThat.com / Agent.ai

- **TAAFT:** Pre-filled copy: **[submissions/taaft-form-copy.md](submissions/taaft-form-copy.md)** · submit: [theresanaiforthat.com/s/submit/](https://theresanaiforthat.com/s/submit/) · order with Smithery/Glama: **[submissions/SMITHERY_GLAMA_TAAFT.md](submissions/SMITHERY_GLAMA_TAAFT.md)**.
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
| **Smithery + Glama + TAAFT** (ordered runbook) | [submissions/SMITHERY_GLAMA_TAAFT.md](submissions/SMITHERY_GLAMA_TAAFT.md) |
| **Awesome MCP** (PR to punkpeye list) | [submissions/awesome-mcp-servers-PR.md](submissions/awesome-mcp-servers-PR.md) |
| **Web3 MCP portals** (DeMCP, mcp.so, MCP Market, AgentKit, ElizaOS, …) | [submissions/MCP_WEB3_PORTALS.md](submissions/MCP_WEB3_PORTALS.md) |
| **TAAFT** (form copy) | [submissions/taaft-form-copy.md](submissions/taaft-form-copy.md) |
| **Agent.ai** (expectations + blurb) | [submissions/agent-ai-notes.md](submissions/agent-ai-notes.md) |

---

## After you submit

1. **Push** `master` so **GitHub Pages** deploys `docs/` (includes **`docs/.well-known/ai-plugin.json`**).
2. Verify JSON: **`https://www.agentic-swarm-marketplace.com/.well-known/ai-plugin.json`** (and optionally the **github.io** mirror URL above).
3. **Search Console:** keep **sitemap.xml** submitted; optional URL inspection for new paths.

**Custom domain note:** `docs/CNAME` maps **`www.agentic-swarm-marketplace.com`** to the **project site root** — use **`https://www.agentic-swarm-marketplace.com/...`** paths without `/agentic-crypto-swarm-prototype/` in the path (that segment is only for the default **github.io** project URL).

---

## Files generated in this repo

| File | Role |
|------|------|
| `mcp-manifest.json` | Smithery / Glama–style MCP package metadata + `python` launch |
| `smithery.yaml` | Smithery **stdio** `commandFunction` + optional `configSchema` (wizard / one-click) |
| `docs/.well-known/ai-plugin.json` | Legacy ChatGPT plugin–style metadata + OpenAPI URL (**served on Pages**) |
| `.well-known/ai-plugin.json` | Same JSON at repo root for tools that scan the repository |
| `submissions/*.md` | Smithery/Glama/TAAFT runbook, Awesome MCP PR, TAAFT copy, Agent.ai notes |

**Note:** GitHub Actions deploys **`docs/`** only. The live **ai-plugin** URL for directories must use the **Pages** path above, not raw GitHub path under `.well-known` at repo root.
