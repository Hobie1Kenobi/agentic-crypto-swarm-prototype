# Agentic Crypto Swarm — Architecture Plan

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HUMAN (one-time seed)                                 │
│  • Testnet CELO (Celo Sepolia) or local Anvil                               │
│  • Goals via Constitution.sol                                                │
│  • Beneficiary address for profit claims                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROOT STRATEGIST (ERC-4337 Smart Account)                   │
│  • Receives high-level goal: "maximize sustainable revenue via AI service"   │
│  • Decomposes tasks, delegates to specialists                               │
│  • Full control over swarm; daily cap 0.01 ETH                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ IP-Generator │    │   Deployer   │    │   Finance    │    │   Treasury   │
│ (smart acct) │    │ (smart acct) │    │  Distributor │    │ (shared)     │
│              │    │              │    │ (smart acct) │    │              │
│ Creates      │    │ Deploys/     │    │ Monitors     │    │ Collects     │
│ oracle/      │    │ upgrades     │    │ treasury,    │    │ fees,        │
│ prompt logic │    │ RevenueSvc   │    │ distributes  │    │ holds funds  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │                    │
         └────────────────────┴────────────────────┴────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AgentRevenueService.sol (on-chain)                        │
│  • Pay-per-query: min 0.001 ETH                                              │
│  • 10% protocol fee → treasury                                               │
│  • 50% distributable → Finance-Distributor                                  │
│  • Emits QueryFulfilled(queryHash, payer, amount, metadata)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. ERC-4337 Wallet Infrastructure

| Account            | Role              | Spending Cap | Session Keys | Paymaster |
|--------------------|-------------------|--------------|--------------|-----------|
| Root-Strategist    | Orchestrator      | 0.01 ETH/day | Yes          | Yes       |
| IP-Generator       | Content creation  | 0.01 ETH/day | Yes          | Yes       |
| Deployer           | Contract deploy   | 0.01 ETH/day | Yes          | Yes       |
| Finance-Distributor| Treasury ops      | 0.01 ETH/day | Yes          | Yes       |

**SDK choice**: permissionless.js (Pimlico) + viem — supports Safe, Kernel, LightAccount; Base Sepolia via Pimlico bundler. Fallback: custom MinimalAccount if Pimlico lacks Base Sepolia.

**Creation flow**:
1. Generate EOA keypair per agent (stored in env, never committed)
2. Deploy smart account via factory (counterfactual)
3. Attach session key with daily limit
4. Fund with 0.05 test ETH each

**Agent execution: Signer vs AA mode**
- **Signer mode (default)**: The swarm uses an `AgentExecutor` abstraction. The default implementation (`SimpleSignerAgentExecutor`) signs and sends transactions with the EOA keys from env (`ROOT_STRATEGIST_PRIVATE_KEY`, etc.). This is production-safe and works on Celo (and any chain) without a bundler.
- **AA mode (optional)**: When a bundler is available (e.g. `BUNDLER_RPC_URL` or Pimlico on Base Sepolia), the wallet package can use `AAAgentExecutor` to send ERC-4337 UserOps from smart accounts. The Python stack currently defaults to signer mode so the swarm runs reliably; AA can be wired in later without a major refactor.

## 3. Revenue Contract Design

**AgentRevenueService.sol** (already scaffolded):
- `fulfillQuery(string resultMetadata)` — payable, min 0.001 ETH
- Splits: 10% treasury, 50% finance distributor, remainder stays in contract or configurable
- Events for verifiable audit
- OpenZeppelin Ownable, ReentrancyGuard, Pausable

**Constitution.sol**: Hard-coded ethical rules.

## 3.1 Payment layer (x402)

- **Single source of truth**: `packages/agents/services/payment.py` defines `MIN_PAYMENT_WEI` (0.001 ether), `REVENUE_ABI` (fulfillQuery), `get_min_payment_wei()` (env `PAYMENT_WEI` override), and `verify_payment_tx(tx_hash, revenue_address, expected_metadata)` for on-chain verification.
- **x402 API** (`api_402.py`): GET/POST `/query?q=...` returns **402 Payment Required** with payment details (contract, amount_wei, chain_id, result_metadata). Client sends `fulfillQuery(resultMetadata)` with min payment, then retries with header `X-Payment-Tx-Hash`; server verifies the tx and returns the LLM response. Response and headers include **native_symbol** (CELO/ETH) from chain config so clients see the correct token.
- **Consumers**: Simulation, `pay_and_get_tx_hash`, and the x402 API all use the shared payment module so amounts and ABI stay in sync with the contract.

## 4. LangGraph Workflow

```
[START] → strategist_node
            │
            ├─► ip_generator_node (creates prompt/oracle)
            │       └─► persist to SQLite + emit event
            │
            ├─► deployer_node (deploy/upgrade RevenueService)
            │       └─► UserOp via Deployer smart account
            │
            ├─► (mode switch) private marketplace OR public adapter
            │
            ├─► task_market_demo_node (private mode: Celo/Anvil onchain escrow settlement)
            │       └─► writes marketplace reports + tx hashes
            │
            ├─► public_adapter_node (public/hybrid mode: Olas adapter intake, live or replay)
            │       └─► writes public adapter reports + communication trace
            │
            └─► finance_distributor_node
                    │
                    ├─► check_treasury_balance
                    ├─► if >= 0.05 ETH profit → distribute(60% human, 40% reinvest)
                    └─► loop until goal met
```

**State**: `TypedDict` with `goal`, `tasks`, `balances`, `tx_hashes`, `profit_so_far`.

**Persistence**: SQLite for run state; on-chain events for verification.

## 4.0 Multi-Rail Agent Commerce

| Rail | Role | Status |
|------|------|--------|
| **XRPL** | Machine-native payments (x402-style; XRP or RLUSD); payment receipt correlation | **Live-proven** on testnet |
| **Celo** | Private task marketplace and settlement (escrow, worker payout, requester refund) | **Live-proven** on Celo Sepolia |
| **Public adapters** | Olas / external demand intake | Mock/replay; live configurable |

Payment rail modes: `direct_onchain_celo_payment`, `mock_payment`, `xrpl_x402_payment`, `hybrid_public_request_xrpl_payment_private_celo_settlement`. See [`../celo-xrpl/XRPL_PAYMENTS.md`](../celo-xrpl/XRPL_PAYMENTS.md).

**Proof artifacts:** `live_xrpl_to_celo_proof_report.(md|json)` — presentation-grade proof of live XRPL payment + Celo settlement with verifiable tx hashes.

## 4.1 Dual-mode marketplace execution (Private vs Public vs Hybrid)

The repo supports a `MARKET_MODE` switch:

- **`private_celo`**: run our onchain task lifecycle on `ComputeMarketplace` (Celo Sepolia / Anvil).
- **`public_olas`**: run the public adapter intake (Olas-compatible live attempts). In this repo, live external requests target **Gnosis** via `OLAS_CHAIN_CONFIG=gnosis` (Celo is not used for mechx calls). If live config/tooling is missing, the adapter falls back to explicit replay/mock boundaries.
- **`hybrid`**: public adapter intake (live or replay on Gnosis/Olas) → normalize into internal task → execute private `ComputeMarketplace` settlement on **Celo** (`MARKET_MODE=hybrid` always settles on the private chain).

Evidence artifacts:

- **Public adapter**: `public_adapter_run_report.(md|json)`, `communication_trace.(md|json)`
- **Private marketplace**: `celo_sepolia_task_market_report.(md|json)` or `local_task_market_report.(md|json)`
- **Merged proof**: `dual_mode_run_report.(md|json)`
- **XRPL → Celo live proof**: `live_xrpl_to_celo_proof_report.(md|json)` — presentation-grade proof when XRPL payment + Celo settlement both run live

Details: [`../operations/PUBLIC-ADAPTER.md`](../operations/PUBLIC-ADAPTER.md)

## 5. End-to-End Simulation

1. **Setup**: Deploy contracts, create 4 smart accounts, fund each with 0.05 ETH
2. **Synthetic users**: 10 addresses, each pays 0.001 ETH for AI query
3. **Swarm loop**:
   - IP-Generator creates response (LLM call)
   - Deployer ensures RevenueService is live
   - Simulated users call `fulfillQuery` with payment
   - Finance-Distributor monitors, distributes when ≥0.05 ETH net profit
4. **Output**: Log tx hashes, balances, profit share; proof of 60/40 split to human

## 6. Tech Stack Summary

| Layer        | Technology                          |
|-------------|--------------------------------------|
| Contracts   | Foundry, Solidity 0.8.28, OpenZeppelin |
| Wallets     | permissionless.js, viem, Pimlico    |
| Agents      | Python 3.12, LangGraph, web3.py     |
| LLM         | Groq (fast) or OpenAI                |
| RPC         | Celo Sepolia / Celo mainnet (or Anvil local); Base optional |
| Testing     | Anvil, Base Sepolia, pytest          |

## 7. Secrets Required (ask user once)

- `ALCHEMY_API_KEY`
- `LLM_API_KEY` (Groq preferred)
- `BENEFICIARY_ADDRESS` (EOA)
- `PIMLICO_API_KEY` (optional)

## 8. Phased Execution

| Phase | Deliverable |
|-------|-------------|
| Setup | Repo, .cursor/rules, deps, env template |
| 1     | 4 smart accounts, session keys, test UserOp |
| 2     | AgentRevenueService deployed, verified |
| 3     | LangGraph workflow, agent nodes, on-chain calls |
| 4     | 10-user simulation, ≥0.05 ETH profit, distribution proof |
| Test  | Unit + integration, security checklist, video demo |
