# Celo native x402 seller (`api_402`)

Per-request **HTTP 402** seller on Celo: buyers pay **CELO** via `AgentRevenueService.fulfillQuery`; the server verifies the tx and returns a constitution-bound LLM answer. Same **seller-side** pattern as T54 (XRPL) and `api_seller_x402` (Base USDC) — no `ComputeMarketplace` escrow or worker roles required.

## Public URL (unified API host)

With Caddy (`npm run proxy:unified` on `:9080`):

| Public path | Backend | Purpose |
|-------------|---------|---------|
| `GET/POST …/celo/query?q=` | `api_402` `:8042` `/query` | Paid Q&A (402 until CELO tx) |
| `GET …/celo/health` | `api_402` `/health` | Status, chain, revenue contract |

Set in `.env`:

```env
PUBLIC_API_ORIGIN=https://api.agentic-swarm-marketplace.com
CELO_402_PUBLIC_URL=https://api.agentic-swarm-marketplace.com/celo/query
CHAIN_ID=42220
REVENUE_SERVICE_ADDRESS=0x...
```

`npm run env:mainnet` / `apply_public_api_origin.py` writes `CELO_402_PUBLIC_URL` when `PUBLIC_API_ORIGIN` is set.

## Run locally

```powershell
npm run api:402
# GET http://127.0.0.1:8042/query?q=hello  → 402 + payment JSON
```

Unified stack includes `api:402` automatically: `npm run stack:unified:start`.

## Prerequisites

- `REVENUE_SERVICE_ADDRESS` — deployed `AgentRevenueService` on the chain matching `CHAIN_ID`
- `RPC_URL` / `CELO_MAINNET_RPC_URL` for payment verification
- **No hot seller wallet** per sale — buyers submit `fulfillQuery` with CELO value

## Discovery

- Config row: `swarm-self` in `packages/agents/config/x402_providers.json`
- Runtime URL: `CELO_402_PUBLIC_URL` (see `external_commerce/discovery.py`)
- Regenerate portal links: `npm run docs:sync-endpoints`

## Related

- Base USDC facilitator seller: `api_seller_x402` — [PUBLIC_MAINNET_OPERATIONS.md](../PUBLIC_MAINNET_OPERATIONS.md)
- Private escrow (`ComputeMarketplace`): optional R&D — not required for this seller rail
