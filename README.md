# Agentic Crypto Swarm Prototype

A hierarchical multi-agent system that autonomously earns testnet revenue through on-chain value creation — no trading, no speculation. **Celo-first:** Celo Sepolia (testnet), Celo mainnet (production); local Anvil for zero-faucet testing; optional Base/Polygon paths.

## Architecture

```
Human (seeds ETH + goals)
    │
    ▼
Root Strategist (ERC-4337 smart account)
    │
    ├──► IP-Generator (creates novel oracle/prompt logic)
    ├──► Deployer (deploys/upgrades AgentRevenueService)
    └──► Finance-Distributor (treasury, profit distribution)
```

- **4 isolated smart accounts** with session keys + 0.01 ETH daily cap
- **AgentRevenueService.sol** — pay-per-query AI service (min 0.001 ETH)
- **LangGraph** — stateful multi-agent orchestration
- **Profit split**: 60% human beneficiary, 40% reinvested

## Prerequisites

- [Foundry](https://getfoundry.sh/)
- Python 3.12+
- Node.js 18+
- [Ollama](https://ollama.com) (local LLM; no API key). Default model: `qwen3:8b`; use `tinyllama` if low RAM.
- RPC: set `RPC_URL` or `CELO_SEPOLIA_RPC_URL` for Celo Sepolia; Alchemy optional for Base legacy

## Setup

1. **Clone and install**

   ```bash
   git clone https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype.git
   cd agentic-crypto-swarm-prototype
   ```

2. **Environment**

   Copy `.env.example` to `.env`. Set `CHAIN_NAME=celo-sepolia` (default) or `anvil` for local. Optional: `RPC_URL`, `BENEFICIARY_ADDRESS`, `PIMLICO_API_KEY` (Base only). For Ollama use `OLLAMA_MODEL` (default `qwen3:8b`).

3. **Install dependencies**

   ```powershell
   .\scripts\ensure-ollama-model.ps1
   .\scripts\install-foundry.ps1
   ```
   Restart the terminal so `forge` is on PATH, then:

   ```bash
   forge install OpenZeppelin/openzeppelin-contracts
   cd packages/wallet && npm install
   cd packages/agents && pip install -r requirements.txt
   ```

4. **Create agent wallets** (saves secrets to `.env`, updates `.gitignore`)

   ```bash
   npm run create-accounts
   ```

5. **Claim testnet CELO (Celo Sepolia)**

   - [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia)
   - For local runs use `npm run simulation:local` (no faucet). For legacy Base Sepolia: basefaucet.com, CDP faucet.

## Run

**Full orchestration (one command):** strategist → IP-generator → deployer check → 10-user simulation → finance check (and loop until profit threshold or max steps).

**Celo Sepolia public test:** Full flow (env → create wallets → deploy → fund → orchestrate → monitor) and troubleshooting: **[docs/CELO-SEPOLIA-TESTNET.md](docs/CELO-SEPOLIA-TESTNET.md)**. Short path: `npm run create-accounts` → fund deployer → `npm run testnet:celo` → fund ROOT_STRATEGIST_ADDRESS → `npm run orchestrate`. Check balances: `.\scripts\celo-sepolia-balances.ps1`.

**Manual deploy then orchestrate:**
```bash
# 1. Deploy contracts (once)
.\scripts\deploy.ps1 --broadcast
.\scripts\fetch-and-save-addresses.ps1
# Ensure REVENUE_SERVICE_ADDRESS and FINANCE_DISTRIBUTOR_ADDRESS in .env

# 2. Run full orchestration (LangGraph + simulation in one graph)
npm run orchestrate
# or: npm run swarm   (same thing)
```

Use `--max-steps` to limit graph steps (default 5), e.g. `cd packages/agents && python main.py --max-steps 3`.

**Run steps separately (optional):**

```bash
npm run swarm          # LangGraph only (no simulation)
npm run simulation     # 10-user revenue loop only
```

**Simulation:** Without `REVENUE_SERVICE_ADDRESS` it runs in dry-run (LLM only, log to `simulation_log.txt`). With contract address and a funded key, it sends real `fulfillQuery` txs.

**Local-first test harness (no faucet, repeatable):** One command to validate the full system on Anvil:

```bash
npm run harness:local
```

This starts Anvil, deploys the contracts, and runs the 10-user simulation using Anvil’s pre-funded account (10,000 ETH). Report artifacts: simulation_report.json, simulation_report.md. Clean state: npm run harness:local:reset. Simulation-only: npm run simulation:local.

## How to Monitor / Claim Profits

- Treasury / finance distributor: see `FINANCE_DISTRIBUTOR_ADDRESS` in `.env`
- Celo Sepolia: `https://celo-sepolia.blockscout.com/address/<ADDRESS>`; Celo mainnet: `https://explorer.celo.org/address/<ADDRESS>`. Legacy Base: sepolia.basescan.org
- Profit distribution: when finance balance ≥ `SIMULATION_PROFIT_THRESHOLD_ETH` (default 0.005), simulation sends 60% to `BENEFICIARY_ADDRESS` and leaves 40% reinvested

## How to Run in Production (testnet)

1. Install deps, create agent wallets (`npm run create-accounts`), fund them with testnet ETH.
2. Deploy contracts: `.\scripts\deploy.ps1 --broadcast`; set `REVENUE_SERVICE_ADDRESS` in `.env`.
3. Fund the payer (e.g. root strategist) with ≥0.01 ETH for 10 queries.
4. Set `BENEFICIARY_ADDRESS` and optionally `FINANCE_DISTRIBUTOR_PRIVATE_KEY` for distribution.
5. Run `npm run simulation` for the 10-user revenue loop; check `simulation_log.txt` for tx hashes and profit proof.
6. For full 0.05 ETH profit target, set `SIMULATION_PROFIT_THRESHOLD_ETH=0.05` and run until finance balance reaches it (or run more queries).

## Constraints

- **Default testnet**: Celo Sepolia (11142220). Production: Celo mainnet (42220). Local: Anvil (31337). Base Sepolia (84532) legacy/optional.
- **No trading/DEX/speculation** — revenue from usage fees only
- **Ethical constitution** — no gambling, illegal content; sustainable compute

## Production readiness

For Celo mainnet launch: deployment, security, operations, secrets, monitoring, wallets, upgrades, economic risk, abuse/spam, rate limits, accounting, and DAO recommendation are in **[docs/PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md)**. v1 minimal launch: deploy without DAO; keep revenue contract owned by EOA or multisig.

## Compute marketplaces and DAO

- **x402 API:** `npm run api:402` — HTTP 402 pay-per-query; client pays to `AgentRevenueService`, retries with `X-Payment-Tx-Hash`, gets LLM response.
- **Compute marketplace:** Deploy includes `ComputeMarketplace`. Run miner: `npm run miner` (POST /task); run validator: `npm run validator` (scores miners, submitScores). Fund the contract with CELO and call `distributeRewards()` to pay miners.
- **Public marketplace adapter (Olas / Mech):** See **[docs/PUBLIC-ADAPTER.md](docs/PUBLIC-ADAPTER.md)**. This repo supports a dual-chain operating model:
  - **Private settlement (Celo Sepolia):** `MARKET_MODE=private_celo`
  - **Live/public Olas attempts (Gnosis):** `MARKET_MODE=public_olas` (requires Gnosis config + `mechx`)
  - **Hybrid (Gnosis intake → Celo settlement):** `MARKET_MODE=hybrid`
  - Replay-only hybrid is supported via `docs/examples/olas_request_replay_example.json`
  - Reports: `olas_preflight_report.json`, `olas_env_checklist.md`, `olas_live_attempt_report.(md|json)`, `hybrid_gnosis_celo_report.(md|json)`
- **DAO (optional/advanced):** After deploy, `npm run deploy:dao` deploys SwarmGovernanceToken, Timelock, Governor and transfers `AgentRevenueService` ownership to the Timelock. Recommended only after validating core flow; see [PRODUCTION-READINESS.md](docs/PRODUCTION-READINESS.md) and [COMPUTE_MARKETPLACES_AND_DAOS.md](docs/COMPUTE_MARKETPLACES_AND_DAOS.md).

## Deliverables

- **Repo:** Monorepo with `contracts/`, `packages/wallet/`, `packages/agents/`, `script/`, `scripts/`
- **.cursor/rules:** `AGENTS.md` with tech stack and conventions
- **Deployed addresses:** After `.\scripts\deploy.ps1 --broadcast`, set `REVENUE_SERVICE_ADDRESS` and `FINANCE_DISTRIBUTOR_ADDRESS` in `.env` (see `.env.example`)
- **Simulation log:** `npm run simulation` writes `simulation_log.txt` with tx hashes and profit summary
- **Tests:** `npm run test` runs Forge contract tests (32 tests) and Python agent tests (25 tests). Contracts: `npm run test:contracts`. Agents: `npm run test:agents`.

## License

MIT
