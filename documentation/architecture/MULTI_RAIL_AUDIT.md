# Multi-Rail Agent Commerce Audit

## 1. Audit Summary

### Current Celo Private Marketplace
- **ComputeMarketplace.sol**: Task lifecycle (create, accept, submit, score, finalize, withdraw), escrow, fee routing
- **AgentRevenueService.sol**: fulfillQuery (min 0.001 ether), treasury/finance splits
- **task_market_demo.py**: Full lifecycle orchestration, five distinct roles (requester, worker, validator, treasury, finance_distributor)
- **deployed_address_manifest.json**: Celo Sepolia addresses (marketplace `0x159074...`, treasury, finance_distributor)

### AgentRevenueService
- Used by x402 API and pay_and_get_tx_hash
- Native token payment to fulfillQuery; no customer balance layer
- Payment verification via `payment.py` (verify_payment_tx)

### Customer Balance / Pricing / Metering
- **None present**. No customer balance, pricing catalog, or metering layer in the repo.
- PAYMENT_WEI env override exists; MIN_PAYMENT hardcoded in contract.

### x402 / Payment-Related Code
- **payment.py**: MIN_PAYMENT_WEI, REVENUE_ABI, get_min_payment_wei(), verify_payment_tx() — EVM-only
- **api_402.py**: FastAPI 402 endpoint; returns payment details; verifies X-Payment-Tx-Hash against AgentRevenueService
- **pay_and_get_tx_hash.py**: CLI to pay fulfillQuery and get tx hash
- All payment paths are EVM native (CELO/ETH) to AgentRevenueService

### Olas / Public Adapter
- **olas_adapter.py**: send_olas_mech_request via mechx CLI; Gnosis/base/polygon/optimism
- **public_market_adapter.py**: run_public_adapter_demo — Olas intake → normalize → hybrid Celo settlement
- **request_normalizer.py**: normalize_olas_request → NormalizedTask
- **result_formatter.py**: format_hybrid_result

### Communication Trace and Correlation
- **communication_trace.py**: TraceEvent, CommunicationTrace; boundaries: real_external_integration, contract_level_execution, local_simulation, mocked_external_replay
- **generate-hybrid-gnosis-celo-report.py**: Correlates external_request_id, external_tx_hash, internal_task_id, internal_tx_hashes

### Chain Config
- **config/chains.json**: anvil, celo-sepolia, celo-mainnet, base-sepolia, polygon-amoy, polygon-mainnet, gnosis
- **config/chains.py**: get_rpc, get_chain_id, get_chain_config (single-chain, RPC_URL)
- **config/dual_chain.py**: get_private_chain_config, get_public_olas_chain_config, PRIVATE_*, PUBLIC_OLAS_*

### XRPL References
- **None**. No XRPL, xrpl-py, or x402 XRPL client in the repo.

---

## 2. Reusable Components

| Component | Location | Reuse for XRPL |
|-----------|----------|----------------|
| CommunicationTrace | services/communication_trace.py | Extend with payment_rail, xrpl_tx_hash |
| request_normalizer | services/request_normalizer.py | Add payment_receipt, xrpl fields |
| dual_chain config | config/dual_chain.py | Add XRPL config section |
| public_market_adapter | services/public_market_adapter.py | Insert XRPL payment step before Celo task |
| task_market_demo | task_market_demo.py | Keep unchanged; called after payment verified |

---

## 3. Gaps for XRPL Payment Integration

1. **No payment abstraction**: payment.py is EVM-only; need provider interface
2. **No XRPL config**: XRPL_ENABLED, XRPL_NETWORK, XRPL_RPC_URL, XRPL_WALLET_SEED, XRPL_RECEIVER_ADDRESS, XRPL_SETTLEMENT_ASSET
3. **No XRPL payment provider**: request creation, verification, receipt normalization
4. **No payment-to-task correlation**: XRPL tx hash → internal_task_id mapping
5. **Trace boundaries**: Need real_xrpl_payment, mock_xrpl_payment, replayed_xrpl_payment
6. **No xrpl-py or x402 XRPL client** in dependencies

---

## 4. Files to Change

| File | Action |
|------|--------|
| packages/agents/config/rail_config.py | **Create** — multi-rail config model |
| packages/agents/services/payment_provider.py | **Create** — abstraction interface |
| packages/agents/services/xrpl_payment_provider.py | **Create** — XRPL provider |
| packages/agents/services/payment_correlation.py | **Create** — map payment → task |
| packages/agents/services/communication_trace.py | **Modify** — add payment_rail, xrpl fields |
| packages/agents/services/public_market_adapter.py | **Modify** — insert XRPL payment step |
| packages/agents/services/request_normalizer.py | **Modify** — accept payment_receipt |
| scripts/run_multi_rail_demo.py | **Create** — orchestration script |
| scripts/generate-multi-rail-report.py | **Create** — multi-rail reports |
| .env.example | **Modify** — add XRPL vars |
| docs/ARCHITECTURE.md | **Modify** — multi-rail section |
| docs/XRPL_PAYMENTS.md | **Create** — XRPL docs |

---

## 5. Implementation Plan

1. **Phase 1**: Multi-rail config (rail_config.py, .env.example)
2. **Phase 2**: Payment abstraction (payment_provider.py, xrpl_payment_provider.py, payment_correlation.py)
3. **Phase 3**: XRPL integration (mock + replay first; live behind env gate)
4. **Phase 4**: Hybrid flow (public_market_adapter + XRPL payment step)
5. **Phase 5**: Reporting (xrpl_payment_report, xrpl_to_celo_correlation_report, multi_rail_run_report)
6. **Phase 6**: Business-layer stubs (customer_balance, pricing catalog interfaces)
7. **Phase 7**: Tests
8. **Phase 8**: Execution (regression, mock, replay, live attempt)
9. **Phase 9**: Documentation
