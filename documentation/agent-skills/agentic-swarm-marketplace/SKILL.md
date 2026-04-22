---
name: agentic-swarm-marketplace
description: Operate the Agentic Swarm Marketplace API — x402-paid smart contract and airdrop intelligence, MCP HTTP tools, and machine discovery under /.well-known.
---

# Agentic Swarm Marketplace

Use this skill when integrating or operating **Agentic Swarm Marketplace**: multi-rail agent commerce (Base USDC x402, XRPL where configured), MCP over HTTP, and passive discovery for agents.

## Discovery (no payment)

On the public API host, fetch:

- `/.well-known/ucp` — Universal Commerce Protocol business profile (services, capabilities, API/OpenAPI links).
- `/.well-known/acp.json` — Agentic Commerce Protocol discovery (`protocol`, `api_base_url`, transports, `capabilities.services`).
- `/.well-known/x402.json` — paid resource catalog (paths, prices, network).
- `/.well-known/mcp/server-card.json` — MCP Server Card (SEP-1649); connect to `transport.endpoint` (e.g. `/mcp`).
- `/.well-known/api-catalog` — RFC 9727 linkset (`Accept: application/linkset+json`).
- `/.well-known/agent-skills/index.json` — this repo’s Agent Skills index (RFC v0.2.0).

## Paid HTTP (x402)

Resources require a facilitator-settled x402 payment per `x402.json`. Typical flows: contract triage/audit, airdrop intelligence, research briefs, agent commerce data bundles.

## MCP

Prefer **Streamable HTTP** at `/mcp` (see server card). SSE may be available at `/mcp/sse` depending on deployment.

## Ethics

Constitution-safe outputs only — no gambling, illegal content, or unsustainable compute guidance.
