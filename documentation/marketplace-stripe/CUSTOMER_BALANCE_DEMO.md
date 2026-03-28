# Customer Balance Layer — Live Testnet Demo

This document describes how to run a simulation on **live Celo Sepolia** that showcases the customer balance layer and pricing/metering in action.

## Prerequisites

- `.env` configured for Celo Sepolia (see [CELO-SEPOLIA-TESTNET.md](CELO-SEPOLIA-TESTNET.md))
- Funded agent wallets: ROOT_STRATEGIST, IP_GENERATOR, DEPLOYER, FINANCE_DISTRIBUTOR, TREASURY
- `COMPUTE_MARKETPLACE_ADDRESS` pointing at a deployed marketplace with five distinct addresses (see `deployed_address_manifest.json`; avoid configs that fail the five-distinct-addresses check)
- For **live XRPL** demo: `XRPL_WALLET_SEED`, `XRPL_RECEIVER_ADDRESS`, funded XRPL testnet wallet

## Demo Modes

| Mode | XRPL | Celo | Requires |
|------|------|------|----------|
| **Mock** | Mock receipt (no live payment) | Live | Celo keys only |
| **Live** | Real XRPL testnet payment | Live | Celo + XRPL keys |

## Run the Demo

### Mock XRPL (no XRPL faucet needed)

```bash
python scripts/run-customer-balance-demo.py --prompt "What is one ethical use of AI?"
```

### Live XRPL (full end-to-end)

```bash
python scripts/run-customer-balance-demo.py --live-xrpl --prompt "What is one ethical use of AI?"
```

## What Happens

1. **XRPL payment** — Mock or live payment produces a verified receipt.
2. **Credit** — Customer balance is credited (1 XRP mock → 0.01 ETH wei by default).
3. **Budget check** — Balance must be ≥ `TASK_ESCROW_ETH` (default 0.01 ETH).
4. **Debit** — Escrow amount is debited from customer balance.
5. **createTask** — Celo Sepolia task lifecycle (create → accept → submit → score → finalize → withdraw).
6. **Metering** — A metering record is written for the task.

## Outputs

| File | Description |
|------|-------------|
| `multi_rail_run_report.json` | Full run output including `customer_balance` section |
| `customer_balance_demo_report.json` | Demo-specific report |
| `customer_balance_demo_report.md` | Human-readable demo report with Celo explorer links |
| `communication_trace.json` | Step-by-step event trace |

## Pricing (optional override)

```bash
TASK_ESCROW_ETH=0.02 PRICING_XRP_TO_ETH=0.02 python scripts/run-customer-balance-demo.py ...
```

- `TASK_ESCROW_ETH` — Celo escrow per task
- `PRICING_XRP_TO_ETH` — XRP → ETH conversion for crediting (1 XRP = N ETH)
- `PRICING_TASK_XRP` — XRP amount quoted per task (default 1)

## Documenting a Successful Run

After a successful run:

1. Copy `customer_balance_demo_report.md` to a release or proof folder.
2. Include Celo transaction links from the report (Blockscout).
3. For live XRPL: include XRPL transaction hash and testnet explorer link.
4. Commit the report to the repo or publish as a proof artifact.

Example proof snippet:

```markdown
## Customer Balance Demo — 2026-03-XX

- **Mode:** Mock XRPL + Live Celo Sepolia
- **Task ID:** 42
- **Celo createTask:** [View](https://celo-sepolia.blockscout.com/tx/...)
- **Flow:** Credit 1 XRP mock → 0.01 ETH wei → Debit → createTask → Metering
```
