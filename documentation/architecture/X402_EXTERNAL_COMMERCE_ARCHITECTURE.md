# x402 External Commerce Layer — Architecture Delta

## Audit Summary

### Current State
- **Orchestration**: `multi_rail_hybrid.py` (Olas intake → XRPL payment → Celo settlement)
- **Payments**: `payment_provider.py` (PaymentProvider ABC), `xrpl_payment_provider.py` (XRPL)
- **Wallets**: role-based keys (ROOT_STRATEGIST, IP_GENERATOR, etc.), XRPL_WALLET_SEED
- **Chains**: `config/chains.json` (celo-sepolia, base-sepolia, polygon-amoy, gnosis)
- **Reporting**: `proof_bundle.py`, `communication_trace.py`, soak runners
- **x402 Seller**: `api_402.py` — 402 + AgentRevenueService (EVM native token)

### Insertion Points
1. **External intake** — `multi_rail_hybrid.py` ~L259 (external_payload)
2. **Payment provider** — `rail_config.py` + new `X402PaymentProvider`
3. **Orchestration** — routing before `run_task_market_demo` to choose internal vs external

---

## File-by-File Architecture Delta

### New Files (Phase 1)

| Path | Purpose |
|------|---------|
| `packages/agents/external_commerce/__init__.py` | Package init |
| `packages/agents/external_commerce/schemas.py` | Provider, Invocation, Relationship dataclasses |
| `packages/agents/external_commerce/discovery.py` | Discovery layer, registry loaders |
| `packages/agents/external_commerce/provider_registry.py` | Provider CRUD, normalization |
| `packages/agents/external_commerce/relationship_memory.py` | Relationship state persistence |
| `packages/agents/external_commerce/x402_buyer.py` | x402 buyer flow (402 → pay → resubmit) |
| `packages/agents/external_commerce/invocation_records.py` | Invocation record persistence |
| `packages/agents/external_commerce/routing_policy.py` | internal_only, external_only, hybrid, fallback |

### New Files (Phase 2)

| Path | Purpose |
|------|---------|
| `packages/agents/external_commerce/adapters/__init__.py` | Adapter interfaces |
| `packages/agents/external_commerce/adapters/base.py` | DiscoveryAdapter, InvokeAdapter, PaymentAdapter |
| `packages/agents/external_commerce/adapters/direct_x402.py` | Generic direct x402 service adapter |
| `packages/agents/external_commerce/facilitator.py` | Facilitator abstraction (test/prod/custom) |
| `packages/agents/external_commerce/wallet_registry.py` | Multi-chain wallet registry |
| `packages/agents/external_commerce/spend_controls.py` | Max spend, whitelists, dry-run |

### New Files (Phase 3 — Scaffold)

| Path | Purpose |
|------|---------|
| `packages/agents/external_commerce/seller.py` | Seller-side x402 abstraction (scaffold) |

### Modified Files

| Path | Changes |
|------|---------|
| `packages/agents/config/rail_config.py` | Add `X402_EXTERNAL_ENABLED`, `EXTERNAL_MARKETPLACE_MODE` |
| `packages/agents/config/x402_config.py` | **New** — x402-specific config (facilitator, networks, max spend) |
| `packages/agents/services/multi_rail_hybrid.py` | Optional call into routing → external commerce when mode=hybrid |
| `.env.example` | Add X402_*, EXTERNAL_MARKETPLACE_* vars |

---

## Phase 1 Implementation Order

1. **schemas.py** — Provider, ExternalInvocationRecord, ProviderRelationship
2. **provider_registry.py** — In-memory + JSON persistence
3. **discovery.py** — Config-based + direct providers
4. **relationship_memory.py** — JSON persistence
5. **invocation_records.py** — Append-only JSONL
6. **x402_buyer.py** — HTTP 402 flow (request → 402 → sign → resubmit)
7. **routing_policy.py** — Mode selection, provider choice
8. **x402_config.py** — Env-driven config
9. **Integration** — Wire routing into multi_rail_hybrid (minimal, non-breaking)

---

## Phase 1 Complete — Files Changed

### New Files
- `packages/agents/external_commerce/__init__.py`
- `packages/agents/external_commerce/schemas.py`
- `packages/agents/external_commerce/provider_registry.py`
- `packages/agents/external_commerce/discovery.py`
- `packages/agents/external_commerce/relationship_memory.py`
- `packages/agents/external_commerce/invocation_records.py`
- `packages/agents/external_commerce/x402_buyer.py`
- `packages/agents/external_commerce/routing_policy.py`
- `packages/agents/external_commerce/seller.py` (Phase 3 scaffold)
- `packages/agents/config/x402_config.py`
- `packages/agents/config/x402_providers.json`
- `scripts/run-x402-discovery.py`
- `scripts/run-x402-invoke.py`
- `scripts/run-x402-federation-report.py`

### Modified Files
- `.env.example` — X402_* and EXTERNAL_MARKETPLACE_* vars

---

## How to Use

### Test Mode
```bash
# Discovery (loads from config/x402_providers.json)
python scripts/run-x402-discovery.py

# One paid invocation (dry run by default)
X402_DRY_RUN=1 python scripts/run-x402-invoke.py

# Federation report
python scripts/run-x402-federation-report.py
```

### Live Mode (requires x402 SDK + Base Sepolia key)
```bash
pip install "x402[requests,evm]"
export X402_DRY_RUN=0
export X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY=0x...
python scripts/run-x402-invoke.py
```

### Inspect Outputs
- `external_commerce_data/providers.json` — provider registry
- `external_commerce_data/provider_relationships.json` — relationship memory
- `external_commerce_data/external-invocations.jsonl` — invocation records
- `external_commerce_data/discovery-results.json` — discovery output
- `external_commerce_data/federation-summary.json` — summary
- `external_commerce_data/federation-report.md` — markdown report

## See also

- [Stripe MPP (optional) — Machine Payments Protocol + Tempo deposit helpers](STRIPE_MPP_INTEGRATION.md) — separate from x402; default off (`STRIPE_MPP_ENABLED=0`).
