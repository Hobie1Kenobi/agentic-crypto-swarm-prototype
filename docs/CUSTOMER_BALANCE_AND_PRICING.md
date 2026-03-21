# Customer Balance Layer & Pricing

## Overview

Two new capabilities:

1. **Customer balance layer** — Pre-funded balances for requesters; XRPL payments credit balances; task creation debits balances.
2. **Pricing & metering** — Configurable fees, XRP/RLUSD support, metering records.

## Customer Balance Layer

### Flow

When `CUSTOMER_BALANCE_ENABLED=1` and the payment rail uses XRPL:

1. **Credit**: After a verified XRPL payment, the customer's balance is credited. The amount is converted from XRP/RLUSD to wei using configurable rates.
2. **Debit**: Before creating a Celo task, the system checks that the customer has sufficient balance, then debits the task cost.
3. **Metering**: After a successful task, a metering record is written for auditing.

Customer ID is derived from `external_request_id` (from Olas or replay payload).

### Environment

| Variable | Description |
|----------|-------------|
| `CUSTOMER_BALANCE_ENABLED` | Set to `1` to enable balance layer. Default: disabled. |
| `CUSTOMER_BALANCE_DB_PATH` | SQLite file path. Default: `customer_balances.db` in repo root. |

### Persistence

- SQLite: `customer_balances`, `balance_credits`, `balance_debits`, `metering` tables
- Database path is gitignored (`*.db`)

## Pricing & Metering

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TASK_ESCROW_ETH` | Celo escrow per task (ETH) | `0.01` |
| `PRICING_TASK_XRP` | XRP amount per task (for XRPL quote) | `1` |
| `PRICING_TASK_RLUSD` | RLUSD amount per task | `1` |
| `PRICING_XRP_TO_ETH` | XRP→ETH rate for crediting balance | `0.01` |
| `PRICING_XRP_TO_WEI` | Override: wei per XRP (integer) | — |
| `PRICING_RLUSD_TO_ETH` | RLUSD→ETH rate | `0.01` |
| `PRICING_RLUSD_TO_WEI` | Override: wei per RLUSD unit | — |

### RLUSD Support

- Set `XRPL_SETTLEMENT_ASSET=RLUSD` for RLUSD payment rail
- `XRPLPaymentProvider.quote_payment()` returns RLUSD amount from `PRICING_TASK_RLUSD`
- Crediting uses `PRICING_RLUSD_TO_ETH` or `PRICING_RLUSD_TO_WEI`

### Metering

`metering_record(service, customer_id, amount_wei, metadata)` writes to the `metering` table. Used after successful task execution when balance layer is enabled.

## Usage

### Enable balance layer

```bash
CUSTOMER_BALANCE_ENABLED=1 PAYMENT_RAIL_MODE=hybrid_public_request_xrpl_payment_private_celo_settlement MARKET_MODE=hybrid XRPL_PAYMENT_MODE=live python scripts/run-multi-rail-demo.py --force-hybrid --prompt "What is one ethical use of AI?"
```

### Custom pricing

```bash
TASK_ESCROW_ETH=0.02 PRICING_TASK_XRP=2 PRICING_XRP_TO_ETH=0.02 python scripts/run-multi-rail-demo.py ...
```

### Query balance (programmatic)

```python
from services.customer_balance import get_balance
balance = get_balance("customer_id")
```
