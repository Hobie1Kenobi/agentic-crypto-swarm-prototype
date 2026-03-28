# Market Realism Proof

Upgrade from "single-loop proof" to "market realism proof": multiple actors, quote-driven ingress, reconciliation, controlled failures, auditable evidence.

## Features

### A) XRPL ingress hardening

- **Quote-driven payment**: `XRPL_QUOTE_DRIVEN=1` enables `jobId`, `quoteId`, `destinationTag`, `memo_ref`, expected amount, expiry
- **Destination tags** and **memos** on Payment for routing and internal references
- **Delivered amount validation**: payment accepted only when within `XRPL_AMOUNT_TOLERANCE_PCT`
- **Optional X-address**: `XRPL_USE_X_ADDRESS=1` for user-facing payment instructions

### B) Celo settlement

- Unchanged: Celo Sepolia, native CELO. Stable-denominated mode requires contract changes (config placeholders exist).
- Flow: simulate → write → waitForReceipt → parse logs → persist evidence

### C) Reconciliation / idempotency

- **SQLite store** at `RECONCILIATION_DB_PATH` (default `reconciliation.db`)
- Maps: `xrpl_tx_hash` → jobId, quoteId, celoTaskId, celo tx hashes, disposition
- Prevents duplicate settlement: same XRPL payment cannot produce two Celo tasks
- Set `RECONCILIATION_ENABLED=1` for realism runs

### D) Actor realism

- **3 requesters**, **4 workers**, **2 validators** via `REALISM_*_ROLES`
- Round-robin selection per cycle
- Default: ROOT_STRATEGIST, IP_GENERATOR, DEPLOYER (requesters); IP_GENERATOR, DEPLOYER, FINANCE_DISTRIBUTOR, TREASURY (workers); DEPLOYER, FINANCE_DISTRIBUTOR (validators)

### E) Controlled failure injection

- `FAILURE_INJECTION_ENABLED=1`
- `FAILURE_INJECTION_WEIGHTS=wrong_destination_tag:0.01,expired_quote:0.01,...`
- `FAILURE_INJECTION_FLAGS=wrong_destination_tag` (force) or `!wrong_destination_tag` (disable)

### F) Proof bundle

- `run-summary.json`: run metadata, aggregates
- `cycles.csv`: per-cycle data
- `exceptions.csv`: failed cycle classifications
- `evidence/<cycle>.json`: per-cycle proof artifacts

## Run realism soak

```bash
# 6h default (24 cycles)
XRPL_QUOTE_DRIVEN=1 RECONCILIATION_ENABLED=1 python scripts/run-realism-soak.py

# 2h (8 cycles)
REALISM_MAX_CYCLES=8 python scripts/run-realism-soak.py
```

## Env reference

| Var | Default | Purpose |
|-----|---------|---------|
| XRPL_QUOTE_DRIVEN | 0 | Quote-driven payment with job/quote/destination_tag |
| RECONCILIATION_ENABLED | 0 | Idempotency and duplicate prevention |
| XRPL_QUOTE_VALIDITY_SECONDS | 300 | Quote expiry |
| XRPL_AMOUNT_TOLERANCE_PCT | 0.1 | Delivered amount tolerance |
| RECONCILIATION_DB_PATH | reconciliation.db | Reconciliation SQLite path |
| REALISM_*_ROLES | (see actor_registry) | Actor role lists |
| FAILURE_INJECTION_ENABLED | 0 | Enable failure injection |
| REALISM_MAX_CYCLES | duration-based | Override cycle count |

## Acceptance criteria

- Multi-actor concurrency supported
- XRPL ingress validated (quote/tag/memo/amount)
- Duplicate external payments cannot produce duplicate settlements
- Controlled failure cases configurable
- Proof bundle (run-summary, cycles.csv, evidence/) generated
- Existing proven path unchanged when realism flags are off
