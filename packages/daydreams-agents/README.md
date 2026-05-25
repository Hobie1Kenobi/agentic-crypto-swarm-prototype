# Daydreams AI Bounty Agents

x402-enabled agents for [daydreamsai/agent-bounties](https://github.com/daydreamsai/agent-bounties).

| Agent | Port | npm script | Bounty |
|-------|------|------------|--------|
| [fresh-markets-watch](./fresh-markets-watch/) | 8091 | `npm run daydreams:fresh-markets` | [#1](https://github.com/daydreamsai/agent-bounties/issues/1) |
| [slippage-sentinel](./slippage-sentinel/) | 8092 | `npm run daydreams:slippage-sentinel` | [#3](https://github.com/daydreamsai/agent-bounties/issues/3) |
| [gas-route-oracle](./gas-route-oracle/) | 8093 | `npm run daydreams:gas-route-oracle` | [#4](https://github.com/daydreamsai/agent-bounties/issues/4) |
| [approval-risk-auditor](./approval-risk-auditor/) | 8095 | `npm run daydreams:approval-auditor` | [#5](https://github.com/daydreamsai/agent-bounties/issues/5) |
| [yield-pool-watcher](./yield-pool-watcher/) | 8096 | `npm run daydreams:yield-pools` | [#6](https://github.com/daydreamsai/agent-bounties/issues/6) |
| [bridge-route-pinger](./bridge-route-pinger/) | 8100 | `npm run daydreams:bridge-routes` | [#10](https://github.com/daydreamsai/agent-bounties/issues/10) |
| [perps-funding-pulse](./perps-funding-pulse/) | 8101 | `npm run daydreams:perps-funding` | [#8](https://github.com/daydreamsai/agent-bounties/issues/8) |
| [lending-liquidation-sentinel](./lending-liquidation-sentinel/) | 8102 | `npm run daydreams:lending-sentinel` | [#9](https://github.com/daydreamsai/agent-bounties/issues/9) |
| [lp-il-estimator](./lp-il-estimator/) | 8103 | `npm run daydreams:lp-il` | [#7](https://github.com/daydreamsai/agent-bounties/issues/7) |

Lucid TaskMarket APIs live in [`../lucid-data-apis/`](../lucid-data-apis/) (e.g. gas oracle for [lucid-agents#178](https://github.com/daydreamsai/lucid-agents/issues/178)).

Built with `@lucid-dreams/agent-kit` + viem (Base / Base Sepolia).

## Deploy

Each agent exposes `/health` and paywalled `/entrypoints/*/invoke` when `ADDRESS`, `NETWORK`, and `FACILITATOR_URL` are set.

Unified Caddy routes (when stack is wired):

- `/agents/fresh-markets-watch/*` → `:8091`
- `/agents/slippage-sentinel/*` → `:8092`
- `/agents/gas-route-oracle/*` → `:8093`
- `/agents/approval-risk-auditor/*` → `:8095`
- `/agents/yield-pool-watcher/*` → `:8096`
- `/agents/bridge-route-pinger/*` → `:8100`
- `/agents/perps-funding-pulse/*` → `:8101`
- `/agents/lending-liquidation-sentinel/*` → `:8102`
- `/agents/lp-il-estimator/*` → `:8103`
