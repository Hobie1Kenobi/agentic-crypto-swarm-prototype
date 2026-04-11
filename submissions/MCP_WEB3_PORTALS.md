# Web3 MCP portal landscape — Agentic Swarm Marketplace

Use this playbook with **[DIRECTORY_SUBMISSION_KIT.md](../DIRECTORY_SUBMISSION_KIT.md)** (canonical URLs, descriptions, Cursor config).

| Portal | Tier | Action | Status |
|--------|------|--------|--------|
| [DeMCP awesome-web3-mcp-servers](https://github.com/demcp/awesome-web3-mcp-servers) | 1 | PR: new **Security / Audit** section | **Done** — [PR #69](https://github.com/demcp/awesome-web3-mcp-servers/pull/69) |
| [mcp.so](https://mcp.so/submit) | 1 | Web form | ☐ Manual (JSON below in **§2. MCP.so**) |
| [MCP Market](https://mcpmarket.com/) | 1 | Submit / Index (see site nav) | ☐ Manual |
| [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers) (`mcpservers.org`) | 1 | PR: **Security** section | **Done** — [PR #4527](https://github.com/punkpeye/awesome-mcp-servers/pull/4527) |
| [Coinbase AgentKit](https://github.com/coinbase/agentkit) | 2 | PR: `action-providers/` wrapper for audit SKUs | ☐ |
| [ElizaOS registry](https://github.com/elizaos-plugins/registry) | 3 | Follow [Publish a Plugin](https://docs.elizaos.ai/guides/publish-a-plugin) + MCP bridge | ☐ |
| [Virtuals](https://www.virtuals.io/) | 4 | Agent registry + Discord | ☐ |
| [AgentAudit](https://agentaudit.dev/) | 5 | Submit MCP for trust score | ☐ |
| [ChainAware](https://chainaware.com/) | 5 | Partnership / cross-listing outreach | ☐ |

---

## Tier 1 — Submit this week

### 1. DeMCP (`demcp/awesome-web3-mcp-servers`)

- **Site:** https://www.demcp.ai · **List:** https://github.com/demcp/awesome-web3-mcp-servers  
- **Steps:** Fork → edit `README.md` per **[pr-drafts/demcp-awesome-web3-mcp-servers-README-snippet.md](pr-drafts/demcp-awesome-web3-mcp-servers-README-snippet.md)** → PR to `main`.  
- **Angle:** First **Security / Audit** subsection — contract triage + x402 + MCP.

### 2. MCP.so

- **Submit:** https://mcp.so/submit  
- **Type:** MCP Server  
- **Name:** `Agentic Swarm Marketplace` (or `agentic-swarm-t54-x402`)  
- **URL:** `https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype`  
- **Server config (JSON shape — adapt to their form):**

```json
{
  "mcpServers": {
    "agentic-swarm-marketplace": {
      "url": "https://api.agentic-swarm-marketplace.com/mcp"
    }
  }
}
```

- **Notes:** For **local stdio**, point users to `mcp-integration.md`; hosted URL is the primary discoverability hook.

### 3. MCP Market (`mcpmarket.com`)

- **Home:** https://mcpmarket.com/ — use **Submit** / **Collector** / **Index** flows per current site (they evolve).  
- **Keywords for listing:** `smart contract audit`, `EVM security`, `x402`, `Base`, `MCP`, `Web3`.  
- **Evidence URL:** `https://www.agentic-swarm-marketplace.com/mcp-integration.md`

### 4. Awesome MCP Servers (`punkpeye/awesome-mcp-servers` → mcpservers.org)

- **Submit docs:** https://mcpservers.org/submit  
- **Source repo:** https://github.com/punkpeye/awesome-mcp-servers  
- **Steps:** PR with one line under **`### 🔒 Security`** per **[pr-drafts/punkpeye-awesome-mcp-servers-security-line.md](pr-drafts/punkpeye-awesome-mcp-servers-security-line.md)**.  
- **Sync:** Glama directory mirrors this list — one PR can feed multiple surfaces.

---

## Tier 2 — Coinbase ecosystem

### AgentKit action provider

- **Repo:** https://github.com/coinbase/agentkit/tree/main/python/coinbase-agentkit/coinbase_agentkit/action_providers  
- **Idea:** Add a provider that wraps **contract triage**, **contract audit**, and **contract monitor** (and optionally T54 `t54_*` tools) using your public Base/x402 endpoints — aligns with **x402** as the payment story.  
- **Prereqs:** Stable `MARKETPLACE_PUBLIC_BASE_URL` / seller URL, documented env, smoke tests.  
- **Community:** CDP Discord **#agentkit** — share DRUGS triage result + MCP URL after listing is stable.

---

## Tier 3 — ElizaOS

- **Docs:** [Plugin registry](https://docs.elizaos.ai/plugin-registry/registry) · [Publish a plugin](https://docs.elizaos.ai/guides/publish-a-plugin)  
- **Registry repo:** https://github.com/elizaos-plugins/registry  
- **MCP bridge:** https://github.com/elizaos-plugins/plugin-mcp  
- **What to submit:** Streamable HTTP MCP base URL `https://api.agentic-swarm-marketplace.com/mcp`, plus short tool summary (contract + T54 SKUs).

---

## Tier 4 — Virtuals Protocol

- **Track:** Agent Commerce Protocol / agent registry (check current season’s docs).  
- **Pitch:** Contract-level security SKUs as **purchasable agent services** — complementary to wallet-level risk products.

---

## Tier 5 — Security credibility

### AgentAudit (`agentaudit.dev`)

- Submit the MCP server for analysis; use any **trust badge** output on the marketplace site and Smithery card if offered.

### ChainAware

- Positioning: **wallet / behavior risk (them)** + **contract static analysis + fuzzing (you)** — partnership or co-marketing, not competition.

---

## Copy-paste short pitch (DMs / forms)

> **Agentic Swarm Marketplace** is a Web3-native MCP server: paid **x402** APIs for T54 (XRPL) research/audit SKUs and **Base USDC** EVM contract triage, full audit, and monitoring. OpenAPI-driven tools, HTTP 402 + broker, listed on Smithery. Repo: https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype — live: https://www.agentic-swarm-marketplace.com/

---

## Maintenance

- After each merge or URL change, run `npm run docs:sync-endpoints` (if applicable) and keep **[DIRECTORY_SUBMISSION_KIT.md](../DIRECTORY_SUBMISSION_KIT.md)** URLs in sync.
