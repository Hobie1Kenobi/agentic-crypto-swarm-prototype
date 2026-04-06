# Unified reverse proxy (one public host)

Use this when you want **one HTTPS hostname** (one ngrok URL) for:

| Path | Service | Local port |
|------|---------|------------|
| `/mcp/*` | MCP T54 x402 **SSE** (`scripts/mcp_server.py --transport sse`); **`/mcp` is stripped** → `/sse`, `/messages/` | 9050 |
| `/x402/*` | Base x402 seller (`api_seller_x402`) | 8043 |
| `/t54/*` | T54 XRPL seller (`t54_seller_app`); **`/t54` is stripped** before proxying | 8765 |
| `/webhooks/*`, `/v1/*`, `/marketplace/*`, `/docs*`, `/openapi.json`, `/redoc*` | Marketplace (`marketplace_api`) | 8055 |
| everything else (e.g. `/health`) | Defaults to Base x402 (8043) | 8043 |

**Why `/t54`?** Both T54 and Base expose routes under `/x402/v1/...`. Routing Base at `/x402/` and T54 at `/t54/` avoids collisions.

## Prerequisites

1. [Caddy](https://caddyserver.com/docs/install) on your PATH.
2. All three backends running: `npm run t54:seller` (8765), `npm run x402:seller` (8043), `npm run marketplace:serve` (8055).

## Run the proxy

```bash
npm run proxy:unified
```

Or:

```bash
caddy run --config scripts/reverse-proxy/Caddyfile
```

Listens on **`http://127.0.0.1:9080`**.

## Cloudflare Tunnel (stable HTTPS, no router ports)

See **`scripts/cloudflare-tunnel/README.md`** — `cloudflared` + Docker exposes **9080** (this Caddy stack) on your Cloudflare hostname. Set **`T54_SELLER_PUBLIC_BASE_URL=https://YOUR_HOST/t54`** the same way as with ngrok.

## ngrok

**One command (Caddy + dual ngrok + sync .env):** with sellers on **8765/8043/8055**, run **`npm run stack:unified:wire`** — starts Caddy on **9080** if missing, restarts ngrok with **`scripts/ngrok-dual-stack.yml`**, writes **`T54_SELLER_PUBLIC_BASE_URL`**, **`X402_SELLER_PUBLIC_URL`**, **`MARKETPLACE_PUBLIC_BASE_URL`**, reloads T54 discovery. Does not stop your seller processes.

**Option A — one tunnel only (Caddy):** `npm run ngrok:unified` → forwards **9080**.

**Option B — same agent as T54 + x402 (recommended):** `scripts/ngrok-dual-stack.yml` includes a **`unified`** tunnel to **9080**. Start **Caddy first**, then restart ngrok:

```bash
npm run ngrok:dual
```

You should see **three** tunnels in `http://127.0.0.1:4040` (t54_seller, x402_seller, unified).

Do **not** run a second `ngrok http …` if one ngrok agent is already running; add the **unified** tunnel to that agent instead.

## Stripe

Webhook URL:

`https://<your-ngrok-host>/webhooks/stripe`

Set `MARKETPLACE_PUBLIC_BASE_URL=https://<your-ngrok-host>` in `.env`.

## `.env` public URLs (unified host)

Replace `https://YOUR_UNIFIED_HOST` with your real origin (no trailing slash).

```env
X402_SELLER_PUBLIC_URL=https://YOUR_UNIFIED_HOST/x402/v1/query
T54_SELLER_PUBLIC_BASE_URL=https://YOUR_UNIFIED_HOST/t54
MARKETPLACE_PUBLIC_BASE_URL=https://YOUR_UNIFIED_HOST
```

Discovery/listings that build T54 `resource_url` should use base **`.../t54`** so paths become **`.../t54/x402/v1/query`**, etc.

## nginx

See `nginx.conf.example` if you prefer nginx instead of Caddy.
