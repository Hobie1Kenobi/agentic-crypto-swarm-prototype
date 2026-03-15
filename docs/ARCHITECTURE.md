# Agentic Crypto Swarm — Architecture Plan

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HUMAN (one-time seed)                                 │
│  • Testnet ETH via faucet                                                    │
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

## 3. Revenue Contract Design

**AgentRevenueService.sol** (already scaffolded):
- `fulfillQuery(string resultMetadata)` — payable, min 0.001 ETH
- Splits: 10% treasury, 50% finance distributor, remainder stays in contract or configurable
- Events for verifiable audit
- OpenZeppelin Ownable, ReentrancyGuard, Pausable

**Constitution.sol**: Hard-coded ethical rules.

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
            └─► finance_distributor_node
                    │
                    ├─► check_treasury_balance
                    ├─► if >= 0.05 ETH profit → distribute(60% human, 40% reinvest)
                    └─► loop until goal met
```

**State**: `TypedDict` with `goal`, `tasks`, `balances`, `tx_hashes`, `profit_so_far`.

**Persistence**: SQLite for run state; on-chain events for verification.

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
| RPC         | Alchemy Base Sepolia                 |
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
