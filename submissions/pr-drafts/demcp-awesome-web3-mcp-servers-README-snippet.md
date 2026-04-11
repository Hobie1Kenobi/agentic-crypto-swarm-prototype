# PR draft: `demcp/awesome-web3-mcp-servers` — Security / Audit section

**Target repo:** https://github.com/demcp/awesome-web3-mcp-servers  
**Branch:** fork `main` → add snippet → open PR titled: `docs: add Security / Audit category + Agentic Swarm Marketplace MCP`

---

## 1) Table of contents (`## Web3 MCP Categories`)

Add this bullet **after** the existing `* 💬 - [Social](#social)` line (or insert in alphabetical/semantic order with other categories):

```markdown
* 🛡️ - [Security / Audit](#security--audit)
```

---

## 2) New section (place **after** `### 📊 Market Data` and **before** `### 🛠️ Tool` — keeps “infrastructure → security → tooling” flow)

```markdown
### 🛡️ Security / Audit

Security and audit MCP modules expose smart-contract risk intelligence, triage, and monitoring for agents and developers — often with on-chain or micropayment settlement.

- [Hobie1Kenobi/agentic-crypto-swarm-prototype](https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype) - **Agentic Swarm Marketplace MCP** — OpenAPI-driven **T54 x402** tools (XRPL), **Base USDC** routes for contract triage, full audit, and monitoring subscriptions; **HTTP 402** + `x402_broker_client`; **Smithery** + streamable HTTP. [Website](https://www.agentic-swarm-marketplace.com/) · [MCP (streamable HTTP)](https://api.agentic-swarm-marketplace.com/mcp) · [Integration](https://www.agentic-swarm-marketplace.com/mcp-integration.md)
```

---

## 3) PR body (paste into GitHub)

```text
## Summary
- Adds a new **Security / Audit** category to the Web3 MCP curated list.
- First entry: **Agentic Swarm Marketplace** — EVM contract triage/audit/monitoring + T54 x402 SKUs, MCP-native.

## Why this category
Security/audit MCPs are distinct from generic “Tool” or “Market Data” listings; grouping them helps builders and auditors discover contract-focused servers.

## Links
- Repo: https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype
- Smithery: `@hobiecunningham/agentic-swarm-marketplace` (see repo `smithery.yaml`)
```
