# Daydreams AI Bounty Agents

x402-enabled agents for [daydreamsai/agent-bounties](https://github.com/daydreamsai/agent-bounties).

| Agent | Port | npm script | Bounty |
|-------|------|------------|--------|
| [fresh-markets-watch](./fresh-markets-watch/) | 8091 | `npm run daydreams:fresh-markets` | [#1](https://github.com/daydreamsai/agent-bounties/issues/1) |
| [slippage-sentinel](./slippage-sentinel/) | 8092 | `npm run daydreams:slippage-sentinel` | [#3](https://github.com/daydreamsai/agent-bounties/issues/3) |
| [gas-route-oracle](./gas-route-oracle/) | 8093 | `npm run daydreams:gas-route-oracle` | [#4](https://github.com/daydreamsai/agent-bounties/issues/4) |

Lucid TaskMarket APIs live in [`../lucid-data-apis/`](../lucid-data-apis/) (e.g. gas oracle for [lucid-agents#178](https://github.com/daydreamsai/lucid-agents/issues/178)).

Built with `@lucid-dreams/agent-kit` + viem (Base / Base Sepolia).

## Deploy

Each agent exposes `/health` and paywalled `/entrypoints/*/invoke` when `ADDRESS`, `NETWORK`, and `FACILITATOR_URL` are set.

Unified Caddy routes (when stack is wired):

- `/agents/fresh-markets-watch/*` → `:8091`
- `/agents/slippage-sentinel/*` → `:8092`
- `/agents/gas-route-oracle/*` → `:8093`
