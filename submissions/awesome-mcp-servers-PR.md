# Awesome MCP Servers — PR checklist (punkpeye/awesome-mcp-servers)

**Upstream:** [github.com/punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) (default branch `main`).

## Before you open the PR

1. **Glama listing (often required)**  
   Maintainers frequently ask for a **Glama** badge link next to the repo link. Add or claim the server so the badge resolves:  
   [https://glama.ai/mcp/servers](https://glama.ai/mcp/servers) → search `Hobie1Kenobi/agentic-crypto-swarm-prototype` or submit the repo / `smithery.yaml`.  
   Expected badge URL pattern:  
   `https://glama.ai/mcp/servers/Hobie1Kenobi/agentic-crypto-swarm-prototype`  
   Badge image (for reference):  
   `https://glama.ai/mcp/servers/Hobie1Kenobi/agentic-crypto-swarm-prototype/badges/score.svg`

2. **Fork** `punkpeye/awesome-mcp-servers` → branch `add-agentic-crypto-swarm-mcp`.

3. **Edit** `README.md` → section **### 💰 Finance & Fintech** (alphabetical by repo name).

4. **Insert** the following line **after** `[Handshake58/DRAIN-marketplace]` and **before** `[hifriendbot/agentwallet-mcp]`:

```markdown
- [Hobie1Kenobi/agentic-crypto-swarm-prototype](https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype) [![Hobie1Kenobi/agentic-crypto-swarm-prototype MCP server](https://glama.ai/mcp/servers/Hobie1Kenobi/agentic-crypto-swarm-prototype/badges/score.svg)](https://glama.ai/mcp/servers/Hobie1Kenobi/agentic-crypto-swarm-prototype) 🐍 ☁️ 🏠 🍎 🪟 🐧 - T54 x402 seller SKUs as MCP tools: OpenAPI-driven stdio server pays HTTP 402 via x402_broker_client (XRPL / Base USDC per env). Cursor & Claude Desktop; `smithery.yaml` + `mcp-manifest.json`. [Live portal](https://www.agentic-swarm-marketplace.com/) · [MCP setup](https://www.agentic-swarm-marketplace.com/mcp-integration.md).
```

5. **Open PR** with title: `feat: add Hobie1Kenobi/agentic-crypto-swarm-prototype (T54 x402 MCP)`  
   Body: link this repo, mention `scripts/mcp_server.py`, `smithery.yaml`, and that Glama listing is claimed (when done).

## Legend emojis (from upstream README)

- 🐍 Python  
- ☁️ Cloud (remote T54 / x402 HTTP APIs)  
- 🏠 Local (stdio MCP on the developer machine)  
- 🍎 🪟 🐧 macOS / Windows / Linux clients
