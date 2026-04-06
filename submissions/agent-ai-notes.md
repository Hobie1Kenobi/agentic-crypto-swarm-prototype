# Agent.ai — listing notes

**Site:** [agent.ai](https://agent.ai) — professional marketplace for agents built on their **no-code** platform.

## Connections → MCP → Add MCP Server (SSE URL)

This repo exposes **FastMCP over SSE** when you run `npm run mcp:t54:sse` and route HTTPS to it (unified **Caddy `:9080`** strips **`/mcp`** → `127.0.0.1:9050`). Full steps: **[docs/mcp-integration.md](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/mcp-integration.md)** (section **Remote SSE**).

**Paste in Agent.ai (typical):**

- **SSE URL:** `https://<your-unified-tunnel-host>/mcp/sse`  
- If the form asks for a **base** MCP URL, try `https://<host>/mcp` and follow any path hints in their UI.

Set `MCP_SSE_PUBLIC_URL=https://<host>/mcp` in `.env`, then `npm run docs:sync-endpoints` so **endpoints.json** lists `mcp_t54_sse`.

**Security:** No API key on the MCP process — protect with tunnel access controls or run only for demos.

## Other listing options

1. **Suggest demand:** [Request / suggest an agent](https://docs.agent.ai/user/request-an-agent).  
2. **Builder-hosted agent** later — thin wrapper calling your public HTTPS APIs.  
3. **Parallel directories:** [AI Agents Directory](https://aiagentsdirectory.com/submit-agent), TAAFT, etc.

## Copy-paste blurb (documentation / about fields)

**Name:** Agentic Swarm Marketplace  
**URL:** https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/  
**Description:** Open-source hierarchical agents for machine-paid commerce (x402 / T54 on XRPL, Base USDC, Celo). MCP stdio server exposes seller SKUs to Cursor and Claude; broker pays HTTP 402. Repo: `https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype`
