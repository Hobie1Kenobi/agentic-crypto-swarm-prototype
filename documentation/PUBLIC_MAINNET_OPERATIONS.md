# Public surface and mainnet alignment

This is the **completion checklist** for inbound machine-paid traffic: stable HTTPS URLs, correct settlement networks, and discovery that points buyers at **your** services—not `localhost`.

## What “public + mainnet” means here

| Rail | Production network | Asset | Your receive address env |
|------|-------------------|-------|---------------------------|
| **Base x402** (facilitator seller, `api_seller_x402`) | `eip155:8453` (Base mainnet) | USDC | `X402_SELLER_PAY_TO` or address from `ROOT_STRATEGIST_PRIVATE_KEY` |
| **T54 XRPL** (`t54_seller_server.py`) | `xrpl:0` (XRPL mainnet) | XRP | `XRPL_RECEIVER_ADDRESS` / `T54_LOCAL_MERCHANT_PAY_TO` |
| **Celo settlement** (marketplace / agents) | `42220` (Celo mainnet) | CELO | `BENEFICIARY_ADDRESS`, role keys, contract addresses |

**Base Sepolia (`eip155:84532`)** and **Celo Sepolia (`11142220`)** are for **development and testing** only. Real USDC from Bazaar-style clients targets **Base mainnet** (`8453`).

## Why wallets stay quiet without this

1. **Localhost is not reachable** — Buyers on the internet cannot open `http://127.0.0.1:8043` or `:8765`.
2. **Discovery must see HTTPS** — Set public URLs in `.env`, then refresh **`docs/endpoints.json`** so GitHub Pages and tools list the same origins as `external_commerce/discovery.py` (which overlays `X402_SELLER_PUBLIC_URL` and `T54_SELLER_PUBLIC_BASE_URL`).
3. **Network mismatch** — Watching Base mainnet while the seller is still on Sepolia (or the reverse) shows no matching transfers.

## One-time alignment (stable host)

Prefer a **stable** HTTPS origin (Cloudflare Tunnel, fixed VPS, or long-lived tunnel with a reserved hostname). Ephemeral free ngrok URLs work for demos but **break listings** every time the hostname changes.

1. Run sellers locally (or on a host):
   - `npm run x402:seller` → `127.0.0.1:8043`
   - `npm run t54:seller` → `127.0.0.1:8765`
2. Put **Caddy** / **unified proxy** / tunnel in front so the world sees one origin, e.g. `https://your-host/x402/...` and `https://your-host/t54/...` (see `scripts/reverse-proxy/README.md`, `npm run stack:unified:wire`).
3. In **repo root `.env`** (never commit):
   - `X402_SELLER_NETWORK=eip155:8453`
   - `X402_SELLER_PUBLIC_URL=https://your-host/x402/v1/query` (must match how you route to the seller)
   - `T54_SELLER_PUBLIC_BASE_URL=https://your-host/t54` (or full `T54_SELLER_PUBLIC_URL` per `documentation/x402-t54-base/T54_SELLER.md`)
   - `X402_SELLER_PAY_TO=0x...` (Base mainnet USDC receive) if not using the strategist key address
   - `XRPL_RECEIVER_ADDRESS=r...` for T54 XRP receive
4. **Regenerate public registry:**
   ```bash
   npm run docs:sync-endpoints
   ```
   Commit **`docs/endpoints.json`** and push so [GitHub Pages](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/) matches your live URLs.
5. **Optional:** `npm run stack:unified:wire` after tunnel changes (sets env + sync in one flow per `scripts/reverse-proxy/README.md`).

## Prove one paid sale (before expecting organic hits)

- Base USDC: run your repo’s x402 seller smoke against **`X402_SELLER_PUBLIC_URL`** with `X402_DRY_RUN=0` and a funded buyer key on **Base mainnet** (see `documentation/architecture/SWARM_REVENUE_FOCUS.md`).
- XRPL: complete one **402 → pay → settle** against your public T54 query URL; confirm XRP at your **receive** address on an XRPL explorer.

## x402 Scout (optional — list your HTTPS endpoint)

After **`T54_SELLER_PUBLIC_BASE_URL`** / **`X402SCOUT_SERVICE_URL`** use your stable **`api.`** origin (see `scripts/x402scout_ops.py`):

```bash
npm run x402scout:register
```

Registration is a **free** POST with your concrete x402 URL; paid **discover** / **scan** need a funded Base mainnet buyer key and `X402_ALLOWED_NETWORKS=eip155:8453`.

## Cloudflare edge (cache, SSL, secrets)

After **`api.<domain>`** is live: **[operations/CLOUDFLARE_CACHE_AND_SECURITY.md](./operations/CLOUDFLARE_CACHE_AND_SECURITY.md)** — bypass cache for API paths, **Full** SSL mode, rotation hygiene.

## Registry files (no secrets)

| File | Role |
|------|------|
| `docs/endpoints.json` | Machine-readable **public** URLs for Pages + agents (generated from `.env`) |
| `packages/agents/config/x402_providers.json` | Discovery seeds; **runtime** URLs are overridden from env when set (`discovery.py`) |
| `DIRECTORY_SUBMISSION_KIT.md` | Copy for listings; link **endpoints.json** after sync |

## Related docs

- Revenue focus: [architecture/SWARM_REVENUE_FOCUS.md](./architecture/SWARM_REVENUE_FOCUS.md)
- T54 ops: [x402-t54-base/T54_SELLER.md](./x402-t54-base/T54_SELLER.md)
- Celo + XRPL mainnet notes: [celo-xrpl/MAINNET_CELO_XRPL_T54.md](./celo-xrpl/MAINNET_CELO_XRPL_T54.md)
- Production readiness (contracts / keys): [operations/PRODUCTION-READINESS.md](./operations/PRODUCTION-READINESS.md)
- Cloudflare cache / SSL / secrets: [operations/CLOUDFLARE_CACHE_AND_SECURITY.md](./operations/CLOUDFLARE_CACHE_AND_SECURITY.md)
- Custom domain + tunnel setup: [operations/AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md](./operations/AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md)
