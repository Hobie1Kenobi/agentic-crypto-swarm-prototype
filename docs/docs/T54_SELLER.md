# T54 XRPL x402 — seller side only

This stack is **seller-only**: your server returns **402 Payment Required** with **XRPL mainnet** (`xrpl:0`) terms; the **t54 facilitator** (`https://xrpl-facilitator-mainnet.t54.ai`) verifies and settles. You do **not** put private keys in the seller process — only your **receive address** (`r...`).

## Prerequisites

```bash
pip install fastapi uvicorn x402-xrpl python-dotenv
```

## Multi-SKU (per-path pricing)

Paths and **price in drops** are defined in **`packages/agents/config/t54_seller_skus.json`**. Override the file path with **`T54_SELLER_SKUS_JSON`** (absolute path or path relative to the repo root / `packages/agents`).

Each SKU registers its own `require_payment` middleware (exact path match) and returns **JSON** validated against a Pydantic model (also exposed as `output_schema` on the 402 challenge).

Default SKUs (see `t54_seller_skus.json` — prices in **drops**, `version` bumps when the catalog changes):

| Path | Drops (approx.) | Purpose |
|------|-----------------|--------|
| `GET /hello` | 1000 | Micropayment ping (x402 + facilitator) |
| `GET /x402/v1/query?q=` | 2500 | Short constitution-safe LLM answer |
| `GET /x402/v1/research-brief?topic=&context=` | 12000 | Multi-section research brief (optional URLs in `context`) |
| `GET /x402/v1/constitution-audit?prompt_snippet=` | 8000 | Heuristic ethics / constitution-style review of a prompt excerpt |
| `GET /x402/v1/agent-commerce-data?depth=` | 350000 | **Premium** — verifiable proof bundle + external commerce data (federation, discovery, providers, T54 attempts, invocations; `depth=standard` or `full`) |
| `GET /x402/v1/airdrop-intelligence?topic=&context=` | 22000 | Constitution-first **airdrop / incentive screening** (Farm Score 0–100, risk flags; **no** on-chain execution) |

**Standalone scan (no seller):** `npm run airdrop:scout` or `python scripts/run-airdrop-scout.py` — appends JSON lines to `external_commerce_data/airdrop-scans.jsonl`; safe to cron separately from `t54:seller`.

**Discovery keyword scan (CDP + PayAI listings, weak signal):** `npm run discovery:keywords` or `python scripts/scan-discovery-keywords.py` — writes `docs/discovery-keyword-scan.json` and `docs/discovery-keyword-scan.md`; use hit URLs as `context` for `airdrop:scout` / `airdrop-intelligence`.

**EVM claim execution (separate from seller):** `docs/AIRDROP_CLAIM_EXECUTION.md` — approval-gated queue, per-chain routing allowlists, `npm run airdrop:claim`. **Local smoke:** `npm run airdrop:claim:demo`. **Celo Sepolia testnet:** `npm run airdrop:claim:testnet` (funded `AIRDROP_CLAIMANT_PRIVATE_KEY` + RPC).

**Unpaid:** `GET /health` lists configured SKUs, paths, and prices.

## Environment (minimum)

| Variable | Purpose |
|----------|---------|
| `XRPL_RECEIVER_ADDRESS` or `T54_LOCAL_MERCHANT_PAY_TO` | Your **r-address** — XRP lands here |
| `XRPL_FACILITATOR_URL` | Optional; default mainnet t54 facilitator |
| `T54_SELLER_SKUS_JSON` | Optional path to alternate SKU JSON |
| `T54_SELLER_HOST` | Default `127.0.0.1`; use `0.0.0.0` behind a reverse proxy |
| `T54_SELLER_PORT` | Default `8765` |
| `T54_SELLER_PUBLIC_BASE_URL` | Optional — `https://your-host` (no path). Discovery builds full URLs for every T54 SKU row in `x402_providers.json` |
| `T54_SELLER_PUBLIC_URL` | Optional — full URL to one endpoint, or used with path stripping to derive `T54_SELLER_PUBLIC_BASE_URL` for multi-SKU discovery |

## Run the seller

```bash
npm run t54:seller
```

- **Health:** `GET /health` (no payment)
- **Paid:** routes listed in `t54_seller_skus.json` (402 until buyer pays via x402)

## Long-running process (Windows)

```bash
npm run t54:seller:daemon
```

Restart loop — use `systemd`, PM2, or a Windows service for production.

## ngrok (free tier, public HTTPS)

1. Keep **`npm run t54:seller`** running on `127.0.0.1:8765`.
2. In another terminal, start the tunnel (**agent ≥ 3.20** required for current ngrok accounts):
   - **Recommended (repo):** `npm run t54:ngrok` — uses `scripts/ngrok.cmd`, which calls `%LOCALAPPDATA%\Programs\Ngrok\ngrok.exe` (3.37.x).
   - **Or:** `ngrok http 8765` after a one-time install:  
     `powershell -ExecutionPolicy Bypass -File scripts/install-ngrok-global.ps1`  
     (installs under `%LOCALAPPDATA%\Programs\Ngrok`, updates your PowerShell profile, and can replace Chocolatey’s old shim with UAC approval.)
3. Write the public origin into **`.env`** and refresh discovery:

```bash
npm run t54:sync-ngrok-env
npm run t54:reload-discovery
```

`sync_t54_env_from_ngrok.py` reads `http://127.0.0.1:4040/api/tunnels` and sets **`T54_SELLER_PUBLIC_BASE_URL`** (scheme + host only; discovery appends each SKU path).

**GitHub Pages:** After syncing env, run **`npm run docs:sync-endpoints`** to refresh **`docs/endpoints.json`** (also picks up **`X402_SELLER_PUBLIC_URL`**). Commit and push so [the public portal](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/) “Live endpoints” matches discovery.

**T54 + Base x402 (Bazaar) on one ngrok agent:** with **`npm run t54:seller`** (8765) and **`npm run x402:seller`** (8043) both listening, run **`npm run stack:dual-ngrok`**. That merges your account authtoken config with `scripts/ngrok-dual-stack.yml`, starts two tunnels, and writes **`T54_SELLER_PUBLIC_BASE_URL`** and **`X402_SELLER_PUBLIC_URL`** to `.env` (and **`X402_SELLER_PUBLIC_URL`** to `.env.mainnet` when present). Use **`npm run sync:ngrok-all`** if ngrok is already running with both tunnels.

Free tunnels get a **new hostname** whenever ngrok restarts — run **`npm run t54:sync-ngrok-env`** again after each restart.

## Run 24/7 on Windows (background)

1. **One command stack** (seller + ngrok + `.env` sync):

```bash
npm run t54:stack:start
```

Logs: **`logs/t54-seller.log`**, **`logs/t54-ngrok.log`** (gitignored).

2. **Start automatically on every logon** (no Administrator required):

```bash
npm run t54:stack:install-startup
```

This adds a **Startup** shortcut that runs `scripts/start-t54-stack.ps1` hidden. Remove with **`npm run t54:stack:uninstall-startup`**.

3. **Optional — Scheduled Tasks** (logon + every 15 min watchdog): run **`npm run t54:stack:install-task`** in **PowerShell as Administrator** if your policy allows task creation. If you see “Access is denied”, rely on the Startup shortcut only, or create the tasks manually in Task Scheduler.

4. **Stop** the seller and ngrok: **`npm run t54:stack:stop`**

**Notes:** Put the machine to sleep or disconnect Wi‑Fi and tunnels pause. For always-on production, use a small VPS or PaaS instead of a sleeping laptop. Ensure **`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`** if Startup scripts are blocked.

## Discovery / buyers

Set **`T54_SELLER_PUBLIC_BASE_URL=https://your-host`** (no trailing path) so **`external_commerce/discovery.py`** fills **`resource_url`** for each provider row that has **`metadata.t54_path`**.

If you only set **`T54_SELLER_PUBLIC_URL=https://host/x402/v1/query`**, the host is derived and all **`t54_path`** rows get the same origin plus their path.

The catalog entry **`t54-xrpl-example`** and the additional **`t54-xrpl-*`** rows in `x402_providers.json` pick this up.

## Optional report

```bash
npm run report:t54-commerce
```

## Not in scope here

- **Buyer** flows use `T54XrplAdapter` / `npm run t54:cycle` (separate wallet seed on the buyer machine).
- **Base USDC** x402 seller remains **`api_seller_x402.py`** / port 8043 — different rail.

## Code

- App factory: `packages/agents/t54_seller_app.py`
- SKU catalog: `packages/agents/t54_seller_catalog.py`, `packages/agents/config/t54_seller_skus.json`
- Models / handlers: `packages/agents/t54_seller_models.py`, `packages/agents/t54_seller_handlers.py`
- Runner: `scripts/t54_seller_server.py`
