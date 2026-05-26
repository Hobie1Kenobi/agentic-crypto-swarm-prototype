# Port registry (local stack)

Snapshot from live listeners on the dev machine. Public URLs use Caddy `:9080` paths; backend ports are internal only.

## Core stack

| Port | Process | Service |
|------|---------|---------|
| 8042 | python | Celo-native api_402 (`/query`; public `/celo/query` via Caddy) |
| 8043 | python | Base x402 seller (default catch-all) |
| 8044 | python | auxiliary seller / worker |
| 8046 | python | auxiliary seller / worker |
| 8055 | python | Marketplace API |
| 8056 | python | Autonomous buyer |
| 8765 | python | T54 XRPL seller |
| 9051 | python | MCP SSE (optional) |
| 9052 | python | MCP streamable HTTP |
| 9080 | caddy | Unified reverse proxy |
| 4040 | ngrok | Tunnel API |
| 11434 | ollama | LLM |

## Daydreams bounty agents (agent-kit + x402)

| Port | Agent | npm script | Public path |
|------|-------|------------|-------------|
| 8091 | fresh-markets-watch | `daydreams:fresh-markets` | `/agents/fresh-markets-watch/*` |
| 8092 | slippage-sentinel | `daydreams:slippage-sentinel` | `/agents/slippage-sentinel/*` |
| 8093 | gas-route-oracle | `daydreams:gas-route-oracle` | `/agents/gas-route-oracle/*` |
| 8095 | approval-risk-auditor | `daydreams:approval-auditor` | `/agents/approval-risk-auditor/*` |
| 8096 | yield-pool-watcher | `daydreams:yield-pools` | `/agents/yield-pool-watcher/*` |
| **8100** | bridge-route-pinger | `daydreams:bridge-routes` | `/agents/bridge-route-pinger/*` |
| **8101** | perps-funding-pulse | `daydreams:perps-funding` | `/agents/perps-funding-pulse/*` |
| **8102** | lending-liquidation-sentinel | `daydreams:lending-sentinel` | `/agents/lending-liquidation-sentinel/*` |
| **8103** | lp-il-estimator | `daydreams:lp-il` | `/agents/lp-il-estimator/*` |
| **8104** | cross-dex-arbitrage-alert | `daydreams:cross-dex-arbitrage` | `/agents/cross-dex-arbitrage-alert/*` |

**8094** — reserved for Lucid TaskMarket `gas-oracle` (`npm run lucid:gas-oracle`).

**8097–8099** — previously assigned to bridge / perps / lending agents; occupied by other processes on this host. New agents use **8100–8102** instead. Override via env: `BRIDGE_ROUTE_PINGER_PORT`, `PERPS_FUNDING_PULSE_PORT`, `LENDING_LIQUIDATION_SENTINEL_PORT`, `CROSS_DEX_ARBITRAGE_PORT`.

## Free ports (next agents)

8094 (when gas-oracle not running), 8105+.
