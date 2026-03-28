# XRPL Machine Payments

XRPL is integrated as a **machine-native payments rail** for agent commerce. Celo remains the **private settlement rail** for task lifecycle and escrow.

## XRPL x402 discovery (separate)

Filter public x402 catalogs for XRPL/XRP payment listings: [`../discovery/XRPL_DISCOVERY.md`](../discovery/XRPL_DISCOVERY.md), `npm run discovery:xrpl`.

## Architecture

- **Rail 1 — Celo**: Task creation, escrow, worker assignment, validator scoring, fee routing, worker payout, requester refund
- **Rail 2 — XRPL**: x402-style per-request machine payments; XRP or RLUSD; payment receipt correlation
- **Rail 3 — Public adapters**: Olas / external demand intake (unchanged)

## Payment Modes

| Mode | Description |
|------|-------------|
| `mock` | Simulated XRPL receipt; no live ledger |
| `replay` | Replay a pre-recorded XRPL payment payload |
| `live` | Real XRPL payment (requires `xrpl-py`, `XRPL_WALLET_SEED`, funded wallet) |

## Env Vars

```
XRPL_ENABLED=1
XRPL_NETWORK=testnet
XRPL_RPC_URL=https://s.altnet.rippletest.net:51234
XRPL_RECEIVER_ADDRESS=rYourReceiver...
XRPL_WALLET_SEED=sEd...   # Payer; required for live only
XRPL_SETTLEMENT_ASSET=XRP
XRPL_PAYMENT_MODE=mock
```

## Wallet Setup

Create and fund XRPL wallets (testnet) in one step:

```bash
pip install xrpl-py
python scripts/create-xrpl-wallets.py
```

This generates a **receiver** (settlement) and **payer** (agent) wallet, funds both via the XRPL testnet faucet API, and writes `XRPL_RECEIVER_ADDRESS`, `XRPL_WALLET_SEED`, and related vars to `.env`. No manual faucet visit required.

To generate wallets without funding (e.g. for mainnet or manual funding):

```bash
python scripts/create-xrpl-wallets.py --no-fund
```

## How to Run

### Private Celo (no XRPL)

```bash
PAYMENT_RAIL_MODE=direct_onchain_celo_payment MARKET_MODE=private_celo python -c "from task_market_demo import run_task_market_demo; run_task_market_demo()"
```

### XRPL Mock + Celo Hybrid

```bash
$env:PAYMENT_RAIL_MODE="mock_payment"
$env:XRPL_PAYMENT_MODE="mock"
$env:MARKET_MODE="hybrid"
python scripts/run-multi-rail-demo.py --force-hybrid --prompt "What is one ethical use of AI?"
```

### XRPL Replay + Celo Hybrid

```bash
python scripts/run-multi-rail-demo.py --force-hybrid --replay-xrpl scripts/sample_xrpl_replay.json --prompt "Replay test"
```

### XRPL Live (if configured)

```bash
$env:XRPL_PAYMENT_MODE="live"
$env:XRPL_WALLET_SEED="sYourSecret..."
$env:XRPL_RECEIVER_ADDRESS="rReceiver..."
python scripts/run-multi-rail-demo.py --force-hybrid --prompt "Live test"
```

## Reports

- `multi_rail_run_report.json` / `.md`
- `xrpl_payment_report.json` / `.md`
- `xrpl_to_celo_correlation_report.json` / `.md`
- `communication_trace.json` / `.md`
- **`live_xrpl_to_celo_proof_report.json` / `.md`** — Presentation-grade proof when XRPL + Celo both run live (verifiable tx hashes, settlement accounting)

## Live XRPL Blocker

If `xrpl-py` is not installed or `XRPL_WALLET_SEED` is missing, the system falls back to mock and documents the blocker. Install: `pip install xrpl-py`.
