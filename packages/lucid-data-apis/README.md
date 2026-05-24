# Lucid Data APIs

Paid HTTP data APIs for [daydreamsai/lucid-agents](https://github.com/daydreamsai/lucid-agents) TaskMarket bounties.

| API | Port | npm script | Bounty |
|-----|------|------------|--------|
| [gas-oracle](./gas-oracle/) | 8094 | `npm run lucid:gas-oracle` | [#178](https://github.com/daydreamsai/lucid-agents/issues/178) |

Endpoints: `GET /v1/gas/quote`, `/v1/gas/forecast`, `/v1/gas/congestion` with Zod contracts and optional x402 paywall.

Tests: `npm run lucid:gas-oracle:test`
