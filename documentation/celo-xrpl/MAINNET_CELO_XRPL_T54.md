# Celo mainnet + XRPL live + T54 (operational)

Use **`.env.mainnet`** (from [`.env.mainnet.example`](../.env.mainnet.example)) and **`npm run env:mainnet`**.

**Merge behavior:** The activate script **merges** `.env.mainnet` **onto** your existing **`.env`**. Only **non-empty** values in `.env.mainnet` override; **empty** keys (e.g. `PRIVATE_KEY=`) mean *keep the value already in `.env`*, so you do not duplicate secrets. Smoke tests and Python/Forge only ever read **`.env`** at runtime (single file after merge). Use **`-Replace`** on the script only if you want to overwrite `.env` entirely from `.env.mainnet`.

## What runs where

| Piece | What it does in this repo |
|-------|---------------------------|
| **Celo mainnet** | Private settlement: `ComputeMarketplace`, `task_market_demo`, orchestration (`CHAIN_ID=42220`). |
| **XRPL live** | `XRPL_ENABLED=1`, `XRPL_PAYMENT_MODE=live`, `xrpl-py` submits **native Payment** txs on XRPL mainnet (`services/xrpl_payment_provider.py`). |
| **T54** | **HTTP x402** flows: 402 challenge → presigned blob → t54 facilitator `/verify` / `/settle` (`integrations/t54_xrpl/adapter.py`). Used for **paid APIs** (external commerce, x402 sellers), not as a substitute for the simple `Payment` path inside `multi_rail_hybrid`. |

You typically use the **same** `XRPL_WALLET_SEED` (or set `T54_XRPL_WALLET_SEED` explicitly) for both XRPL direct payments and T54 x402, but fund it with **mainnet XRP**.

## Env (combined live)

Minimum for “all rails on” in `.env.mainnet`:

- **Hybrid rail mode:** `MARKET_MODE=hybrid`, `PAYMENT_RAIL_MODE=hybrid_public_request_xrpl_payment_private_celo_settlement`
- **XRPL:** `XRPL_ENABLED=1`, `XRPL_NETWORK=mainnet`, `XRPL_RPC_URL=https://xrplcluster.com` (or your node), `XRPL_PAYMENT_MODE=live`, `XRPL_WALLET_SEED`, `XRPL_RECEIVER_ADDRESS`, `XRPL_ALLOW_MOCK_FALLBACK=0` (fail closed in prod)
- **T54:** `T54_XRPL_ENABLED=1`, `T54_XRPL_MODE=mainnet`, `T54_XRPL_FACILITATOR_URL=https://xrpl-facilitator-mainnet.t54.ai` (default if omitted), `T54_XRPL_DRY_RUN=0`
- **Celo:** align `PRIVATE_RPC_URL` / `RPC_URL` / `CELO_MAINNET_RPC_URL`, deploy addresses, funded agent keys

`OLAS_ENABLED=0` is fine for `run-multi-rail-demo.py`: the “public” leg is **mocked** (`olas_adapter` boundary `mocked_external_replay`) while XRPL + Celo still run.

## Prereqs

```bash
pip install xrpl-py
```

(Already expected for live XRPL; see [`XRPL_PAYMENTS.md`](XRPL_PAYMENTS.md).)

## Commands

- **Multi-rail (XRPL live + Celo settlement):**  
  `python scripts/run-multi-rail-demo.py --force-hybrid`  
  or `npm run demo:multi-rail`

- **T54 full cycle (adapter smoke + optional x402 merchant):**  
  `npm run t54:cycle` — loads `.env`; set `T54_X402_RESOURCE_URL` to a merchant URL, or run `npm run t54:merchant` in another terminal (requires `pip install fastapi uvicorn x402-xrpl`) and set `T54_X402_RESOURCE_URL=http://127.0.0.1:8765/hello`.

- **T54 adapter smoke only:** `npm run t54:smoke -- --mode mainnet` (add `--dry-run` for HTTP-only).

- **Celo marketplace only:**  
  `npm run mainnet:marketplace-smoke`

### Env for T54 marketplace URL

Set **`T54_X402_RESOURCE_URL`** (or `X402_T54_RESOURCE_URL`) to the **protected** HTTPS (or local) URL that returns **402** with XRPL payment terms. The catalog entry `t54-xrpl-example` starts with an empty `resource_url`; discovery fills it from this env. See `packages/agents/external_commerce/discovery.py`.

## T54 seller only (no buyer keys)

Run **`npm run t54:seller`** — paid routes **`/hello`** and **`/x402/v1/query`**, health **`/health`**. Uses **`XRPL_RECEIVER_ADDRESS`** as **pay_to**. Full notes: **[T54_SELLER.md](T54_SELLER.md)**.

## References

- [T54_XRPL_TESTNET_WORKAROUND.md](T54_XRPL_TESTNET_WORKAROUND.md) (mainnet section: hosted facilitator)
- [T54_SELLER.md](T54_SELLER.md)
- [XRPL_PAYMENTS.md](XRPL_PAYMENTS.md)
- [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md)
