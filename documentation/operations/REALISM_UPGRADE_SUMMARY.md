# Market Realism Upgrade — Summary

## What Changed

### 1. Actor model

- **config/realism_config.py**: `get_actors_from_env()` yields 3 requesters, 4 workers, 2 validators from the 5 env keys (ROOT_STRATEGIST, IP_GENERATOR, DEPLOYER, FINANCE_DISTRIBUTOR, TREASURY).
- Each worker has a distinct payout address.
- Actors appear in cycle output as `actors.requester_id`, `actors.worker_payout_address`, `actors.validator_address`, etc.

### 2. Task templates

- **services/task_templates.py**: Task types: summarization, classification, extraction, short_answer.
- Each task has: task_type, complexity, sla_seconds, budget_class, quoted_price_xrp, quoted_price_usd, escrow_eth.
- Budget classes: economy (0.8 XRP, 0.008 CELO), standard (1.0 XRP, 0.01 CELO), premium (1.2 XRP, 0.012 CELO).
- Task is chosen via weighted random (seed via REALISM_SEED).

### 3. Variable economics

- Escrow and XRPL price follow the task budget class.
- `TASK_ESCROW_ETH` and `PRICING_TASK_XRP` are set per cycle from the task spec.

### 4. XRPL metadata

- Each cycle records: tx_hash, sender, receiver, destination_tag, memo_ref, quote_id, expected_amount, delivered_amount, ledger_index, validated, verification_status.
- `ledger_index` comes from the tx response when present.

### 5. Correlation and lifecycle

- **services/correlation.py**: `external_payment_ref(xrpl_tx_hash, destination_tag, delivered_amount, quote_id)`.
- Each cycle has `correlation.external_payment_ref` and `correlation.internal_task_id`.
- Celo lifecycle: labeled steps (createTask, acceptTask, submitResult, validateResult, finalizeTask, withdrawWorkerPayout, settleProtocolFee, settleFinanceFee, refundRequester).

### 6. Cycle artifact schema

- **services/cycle_schema.py**: `build_realism_cycle()` outputs the richer schema.
- Cycle includes: task, actors, boundary, xrpl, correlation, celo (network, task_contract, lifecycle, final_status), settlement, quality, elapsed, errors, warnings.

### 7. Backward compatibility

- **Baseline mode** (`RUN_MODE=baseline` or unset): Old schema and behavior.
- **Realism mode** (`RUN_MODE=realism`): New schema and realism features.
- Existing 6h/24h soak scripts are unchanged.

## How to Run

### Baseline (unchanged)
```bash
python scripts/run-continuous-multi-rail-6h.py
python scripts/run-continuous-multi-rail-24h.py
```

### Realism
```bash
RUN_MODE=realism XRPL_QUOTE_DRIVEN=1 RECONCILIATION_ENABLED=1 python scripts/run-realism-soak.py

# Short run (8 cycles)
REALISM_MAX_CYCLES=8 RUN_MODE=realism python scripts/run-realism-soak.py
```

## New Files

| File | Purpose |
|------|---------|
| packages/agents/config/realism_config.py | RUN_MODE, seed, actor config |
| packages/agents/services/task_templates.py | Task types, economics |
| packages/agents/services/correlation.py | external_payment_ref |
| packages/agents/services/cycle_schema.py | Richer cycle schema builder |
| packages/agents/config/realism_actors.example.json | Example actor config |

## Still Mocked / Not Production

- Public intake: `mocked_external_replay` (no live Olas demand).
- Controlled failure injection: Wired but `FAILURE_INJECTION_ENABLED=0` by default.
- Timing breakdown: Only `total_seconds`; per-phase timing would need instrumentation.
- Stable-denominated settlement: CELO only; no ERC-20 yet.
