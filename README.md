# Agentic Crypto Swarm Prototype

A hierarchical multi-agent system that autonomously earns testnet revenue through on-chain value creation — no trading, no speculation. Proves "Agentic GDP" orchestration on Base Sepolia.

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
- [Alchemy](https://alchemy.com/) API key (optional; for Base Sepolia RPC)

## Setup

1. **Clone and install**

   ```bash
   git clone https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype.git
   cd agentic-crypto-swarm-prototype
   ```

2. **Environment**

   Copy `.env.example` to `.env`. Optional: `ALCHEMY_API_KEY`, `BENEFICIARY_ADDRESS`, `PIMLICO_API_KEY`. For Ollama use `OLLAMA_MODEL` (default `qwen3:8b`).

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

5. **Claim testnet ETH**

   - [Alchemy Faucet](https://basefaucet.com/)
   - [Coinbase CDP Faucet](https://portal.cdp.coinbase.com/products/faucet)

## Run

```bash
# 1. Deploy contracts (once)
.\scripts\deploy.ps1 --broadcast
# Then set REVENUE_SERVICE_ADDRESS and FINANCE_DISTRIBUTOR_ADDRESS in .env

# 2. Run the LangGraph swarm
npm run swarm

# 3. Run Phase 4 simulation (10 synthetic users, LLM responses, optional on-chain txs)
npm run simulation
```

**Simulation:** Without `REVENUE_SERVICE_ADDRESS` it runs in dry-run (LLM only, log to `simulation_log.txt`). With contract address and a funded `ROOT_STRATEGIST_PRIVATE_KEY` or `PRIVATE_KEY`, it sends real `fulfillQuery` txs on Base Sepolia.

## How to Monitor / Claim Profits

- Treasury / finance distributor: see `FINANCE_DISTRIBUTOR_ADDRESS` in `.env`
- Basescan Sepolia: `https://sepolia.basescan.org/address/<ADDRESS>`
- Profit distribution: when finance balance ≥ `SIMULATION_PROFIT_THRESHOLD_ETH` (default 0.005), simulation sends 60% to `BENEFICIARY_ADDRESS` and leaves 40% reinvested

## How to Run in Production (testnet)

1. Install deps, create agent wallets (`npm run create-accounts`), fund them with testnet ETH.
2. Deploy contracts: `.\scripts\deploy.ps1 --broadcast`; set `REVENUE_SERVICE_ADDRESS` in `.env`.
3. Fund the payer (e.g. root strategist) with ≥0.01 ETH for 10 queries.
4. Set `BENEFICIARY_ADDRESS` and optionally `FINANCE_DISTRIBUTOR_PRIVATE_KEY` for distribution.
5. Run `npm run simulation` for the 10-user revenue loop; check `simulation_log.txt` for tx hashes and profit proof.
6. For full 0.05 ETH profit target, set `SIMULATION_PROFIT_THRESHOLD_ETH=0.05` and run until finance balance reaches it (or run more queries).

## Constraints

- **Testnet only**: Base Sepolia (84532). Never mainnet.
- **No trading/DEX/speculation** — revenue from usage fees only
- **Ethical constitution** — no gambling, illegal content; sustainable compute

## Deliverables

- **Repo:** Monorepo with `contracts/`, `packages/wallet/`, `packages/agents/`, `script/`, `scripts/`
- **.cursor/rules:** `AGENTS.md` with tech stack and conventions
- **Deployed addresses:** After `.\scripts\deploy.ps1 --broadcast`, set `REVENUE_SERVICE_ADDRESS` and `FINANCE_DISTRIBUTOR_ADDRESS` in `.env` (see `.env.example`)
- **Simulation log:** `npm run simulation` writes `simulation_log.txt` with tx hashes and profit summary
- **Tests:** `forge test` for `AgentRevenueService` (min payment, fee split, pause)

## License

MIT
