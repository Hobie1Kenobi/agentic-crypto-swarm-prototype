# x402scout catalog integration (buy-side expansion)

This adds an **optional** path to merge **curated rows** from the public [x402scout](https://x402scout.com) `.well-known` catalog into `ProviderRegistry`, so `invoke_by_provider` / routing can target hundreds of HTTPS x402 services **without** changing seller ports or dual-stack processes.

## Default (safe for background runs)

- **`X402_SCOUT_CATALOG_ENABLED=0`** (default) — no merge; `run-x402-discovery.py` behaves as before (config + optional remote only when `X402_DISCOVERY_ENABLED=1`).

## Data flow

1. **Full catalog** (large): `npm run catalog:x402scout` → `external_commerce_data/x402scout-catalog-full.json` (+ optional chunks).
2. **Slim bundle** (committed / CI-built): `npm run catalog:scout-slim` → `external_commerce_data/x402scout-providers-slim.json` — top **N** providers by trust, HTTPS-only, `agent_callable`, price cap.
3. **Registry merge** (when enabled): `Discovery.discover_from_scout_catalog()` loads the slim file and `add()`s normalized `ExternalProvider` rows with `discovery_source=x402scout_catalog` and stable ids `scout-{16-hex}`.

## Environment

| Variable | Purpose |
|----------|---------|
| `X402_SCOUT_CATALOG_ENABLED` | `1` to merge slim catalog into registry during `run-x402-discovery.py` / `discover_all()`. |
| `X402_SCOUT_SLIM_JSON` | Optional path override for slim JSON (default: `external_commerce_data/x402scout-providers-slim.json`). |
| `X402_DISCOVERY_ENABLED` | Unchanged — controls legacy remote discovery URLs in `discovery.py`. |

## Commands

```bash
# Refresh full catalog from x402scout (network)
npm run catalog:x402scout

# Rebuild slim curated list (filters + cap)
npm run catalog:scout-slim

# Rebuild discovery-results.json (respects .env flags)
npm run commerce:discover
```

## Wiring after your background run stops

1. Set **`X402_SCOUT_CATALOG_ENABLED=1`** in `.env`.
2. Run **`npm run catalog:scout-slim`** if the full catalog changed.
3. Run **`npm run commerce:discover`** (or your discovery job) to refresh `discovery-results.json` and `providers.json`.
4. Use **`invoke_by_provider`** / **`RoutingPolicy.select_provider`** with `EXTERNAL_MARKETPLACE_MODE` / trust thresholds as before — scout rows compete with config providers by `trust_score` and relationship memory.

## Notes

- Slim build **excludes** non-HTTPS URLs and `agent_callable: false` entries.
- **Earning** still requires orchestration to call external APIs with funded x402 buyers — this layer only **registers** candidates.
