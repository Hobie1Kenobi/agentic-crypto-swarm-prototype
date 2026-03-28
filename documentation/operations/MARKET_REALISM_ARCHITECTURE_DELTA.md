# Market Realism — Architecture Delta

## 1. Repo audit summary

| Domain | Files |
|--------|-------|
| XRPL | `packages/agents/services/xrpl_payment_provider.py`, `xrpl_quote.py`, `pricing.py` |
| Celo | `packages/agents/task_market_demo.py`, `contracts/ComputeMarketplace.sol` |
| Orchestration | `packages/agents/services/multi_rail_hybrid.py`, `scripts/soak_test_runner.py` |
| Reports | `multi_rail_hybrid._write_live_proof_report`, `soak_test_runner.compute_summary`, `proof_bundle.py` |

## 2. Architecture changes

### 2.1 Additive (no breaking changes)

| Change | File(s) | Behavior |
|--------|---------|----------|
| Quote-driven ingress | `xrpl_quote.py`, `xrpl_payment_provider.py` | When `XRPL_QUOTE_DRIVEN=1`, create quote (job/quote/destination_tag/memo), submit with memos, validate amount |
| Reconciliation store | `reconciliation.py` | SQLite idempotency; `RECONCILIATION_ENABLED=1` to use |
| Actor registry | `actor_registry.py` | Round-robin requester/worker/validator from `REALISM_*_ROLES` |
| Failure injection | `failure_injection.py` | Configurable weights/flags; `FAILURE_INJECTION_ENABLED=1` |
| Proof bundle | `proof_bundle.py` | `run-summary.json`, `cycles.csv`, `exceptions.csv`, `evidence/` |

### 2.2 Integration points

| Flow | Before | After |
|------|--------|-------|
| XRPL payment | `quote_payment` → `attempt_live_xrpl_payment` | Same when `XRPL_QUOTE_DRIVEN=0`; when `=1`, quote-driven path with tag/memo |
| Multi-rail | `run_multi_rail_hybrid_demo` → `run_task_market_demo` | If `RECONCILIATION_ENABLED` and settled, return existing; else `record_payment_pending` before createTask, `record_settlement` after |
| Soak cycle | `run_cycle` → `run_multi_rail_hybrid_demo` | Pass `requester_role`, `worker_role`, `validator_role` from actor registry |

### 2.3 Preserved

- Existing 6h/24h soak scripts unchanged (no realism flags)
- Celo Sepolia, native CELO settlement
- ComputeMarketplace contract unchanged (no `externalPaymentRef` in contract; app-layer idempotency only)
- Olas intake boundary (mocked)

## 3. Implementation order (completed)

1. Reconciliation store (SQLite)
2. Quote model (`xrpl_quote.py`)
3. XRPL provider: destination_tag, memos, delivered-amount, quote-driven path
4. Actor registry
5. Multi-rail: reconciliation check, record_payment_pending, record_settlement
6. Soak runner: actor selection
7. Failure injection module
8. Proof bundle generator
9. Realism soak script

## 4. File-level changes

| File | Action |
|------|--------|
| `packages/agents/services/reconciliation.py` | New |
| `packages/agents/services/xrpl_quote.py` | New |
| `packages/agents/services/actor_registry.py` | New |
| `packages/agents/services/failure_injection.py` | New |
| `packages/agents/services/proof_bundle.py` | New |
| `packages/agents/services/xrpl_payment_provider.py` | Modified: destination_tag, memos, quote-driven, delivered amount |
| `packages/agents/services/multi_rail_hybrid.py` | Modified: reconciliation, actor role params |
| `scripts/soak_test_runner.py` | Modified: actor selection in run_cycle |
| `scripts/run-realism-soak.py` | New |
| `docs/MARKET_REALISM.md` | New |
| `.env.example` | Added realism env vars |

## 5. Commands

```bash
# Run realism soak (6h default)
XRPL_QUOTE_DRIVEN=1 RECONCILIATION_ENABLED=1 python scripts/run-realism-soak.py

# Short run (8 cycles)
REALISM_MAX_CYCLES=8 XRPL_QUOTE_DRIVEN=1 RECONCILIATION_ENABLED=1 python scripts/run-realism-soak.py
```

## 6. Acceptance tests (manual)

- [ ] Run 2 cycles with `XRPL_QUOTE_DRIVEN=1`, `RECONCILIATION_ENABLED=1` — both complete
- [ ] Verify `artifacts/proof_bundle/run-summary.json` and `artifacts/proof_bundle/evidence/000000.json` exist
- [ ] Run existing 6h soak without realism flags — behavior unchanged
- [ ] Duplicate XRPL tx hash (replay) with reconciliation — second attempt returns "duplicate" without creating task

## 7. Stable-denominated settlement

Config placeholders exist (`STABLE_SETTLEMENT_ASSET_ADDRESS`, etc.). ComputeMarketplace uses native CELO only. ERC-20 stable settlement requires contract changes (not implemented).
