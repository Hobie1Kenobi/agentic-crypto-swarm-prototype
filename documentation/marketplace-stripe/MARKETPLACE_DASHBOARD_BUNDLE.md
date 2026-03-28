# Marketplace: x402 Strategy Dashboard bundle (Stripe MPP)

This adds a **sellable digital product** path: operators pack a **ZIP** (`npm run marketplace:pack`) and take payment via **Stripe PaymentIntents** with **crypto deposit on Tempo**, the same primitive documented in [STRIPE_MPP_INTEGRATION.md](./STRIPE_MPP_INTEGRATION.md).

It does **not** replace x402 sellers, T54 XRPL, or Celo settlement. Those rails keep their own env flags and processes. The marketplace layer is **optional** and **off by default** for HTTP.

## What ships in the bundle

- `marketplace/bundles/x402-strategy-dashboard/` — README, LICENSE, buyer text, `static/index.html` viewer
- At pack time, `external_commerce_data/x402scout-providers-slim.json` is copied to `static/data/catalog-slim.json`
- You may replace `static/index.html` with your full multi-tab dashboard HTML before packing

## Environment

| Variable | Purpose |
|----------|---------|
| `STRIPE_SECRET_KEY` | Required for orders |
| `STRIPE_WEBHOOK_SECRET` | Signing secret from Stripe Dashboard (`whsec_...`) — required for `POST /webhooks/stripe` |
| `MARKETPLACE_BUNDLE_ZIP_PATH` | Absolute or repo-relative path to the ZIP file buyers download after payment |
| `MARKETPLACE_PUBLIC_BASE_URL` | Public origin (e.g. `https://shop.example.com`) — used for absolute `buyer_portal_url` and `download_url` in JSON responses |
| `MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD` | Default list price (min **0.50** USD — Stripe PaymentIntent constraint) |
| `MARKETPLACE_HTTP_ENABLED` | `1` to expose the marketplace API |
| `MARKETPLACE_HTTP_HOST` / `MARKETPLACE_HTTP_PORT` | Bind for `marketplace:serve` (default `127.0.0.1:8055`) |
| `MARKETPLACE_ORDERS_DIR` | Where `pending-pi_*.json` / `fulfilled-pi_*.json` are written (default `marketplace/orders`) |

## One public hostname (T54 + Base + marketplace)

Use **`npm run proxy:unified`** (Caddy on **:9080**) and a **single** ngrok tunnel to **9080** so Stripe can call **`https://<host>/webhooks/stripe`**. Path map and `.env` URL examples: **[scripts/reverse-proxy/README.md](../scripts/reverse-proxy/README.md)**.

## Operator workflow

1. `npm run catalog:scout-slim` (optional refresh)
2. `npm run marketplace:pack` → writes `dist/x402-strategy-dashboard-bundle-<timestamp>.zip` **and** copies it to **`dist/x402-strategy-dashboard-bundle-latest.zip`** (stable path for `MARKETPLACE_BUNDLE_ZIP_PATH`). Use `--no-latest` to skip the copy.
3. Set **`MARKETPLACE_BUNDLE_ZIP_PATH=dist/x402-strategy-dashboard-bundle-latest.zip`** (repo-relative) or an absolute path to the file buyers download.
4. **Webhooks:** Production — Stripe Dashboard → Developers → Webhooks → endpoint `https://<your-host>/webhooks/stripe` (use the Dashboard signing secret as `STRIPE_WEBHOOK_SECRET`). Local — run **`npm run marketplace:webhook-dev`** in a second terminal; paste the CLI **`whsec_...`** into `STRIPE_WEBHOOK_SECRET` (CLI secret differs from Dashboard).
5. **Public URLs:** Set **`MARKETPLACE_PUBLIC_BASE_URL`** in production so `buyer_portal_url` and `download_url` in JSON use your HTTPS origin. If unset, the API builds absolute URLs from the **incoming request** (Host / proxy headers), which is enough for local testing.
6. `npm run marketplace:serve` with `MARKETPLACE_HTTP_ENABLED=1`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` set.
7. **Create order:** `POST /v1/orders` or `npm run marketplace:order` — prints Tempo address and writes `pending-<pi>.json`.
8. Buyer pays; Stripe sends `payment_intent.succeeded` → server writes `fulfilled-<pi>.json` with a download token and removes the pending file.
9. Buyer opens **`GET /marketplace/success?pi=<pi_id>`** (buyer portal); the page polls `GET /v1/orders/{pi_id}` until `fulfilled` is true, then shows the download link.
10. **Manual fallback:** `python scripts/marketplace-verify-order.py --pi pi_xxx` if you need to confirm status without webhooks.

## HTTP API (agents / integrations)

With `MARKETPLACE_HTTP_ENABLED=1`:

```bash
npm run marketplace:serve
```

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/orders` | JSON `{"product_id":"x402_strategy_dashboard_bundle","buyer_ref":"optional"}` — returns `buyer_portal_url` |
| `GET /v1/orders/{payment_intent_id}` | Stripe status + `fulfilled` + `download_url` when ready |
| `POST /webhooks/stripe` | Stripe **webhooks** (signed with `STRIPE_WEBHOOK_SECRET`) — fulfills on `payment_intent.succeeded` |
| `GET /v1/fulfillment/download/{token}` | Serves `MARKETPLACE_BUNDLE_ZIP_PATH` after fulfillment |
| `GET /marketplace/success?pi=pi_xxx` | **Buyer portal** (HTML) — polls until download is available |
| `GET /health` | Config probe (`webhook_configured`, `bundle_zip_ready`) |

**Local webhook testing:** [Stripe CLI](https://stripe.com/docs/stripe-cli) `stripe listen --forward-to localhost:8055/webhooks/stripe` and use the CLI’s signing secret as `STRIPE_WEBHOOK_SECRET` (or use a Dashboard test secret).

**Security:** Do not expose the service on the public internet without TLS, authentication, and rate limits. The webhook secret must match Stripe’s signing key.

## Fulfillment

- **Webhooks (authoritative):** `payment_intent.succeeded` triggers file move + download token.
- **Portal (UX):** `/marketplace/success` keeps buyers on-page until the order shows `fulfilled`.
- **Email:** Optional; add your own SMTP or Stripe + SendGrid later — not required for the core flow.

## Legal

Ship `LICENSE` and `BUYER_README.md` in the ZIP. You are responsible for terms, refunds, and third-party API usage.
