# Setup Guide

## Prerequisites

- **Ollama** (local LLM): Install from https://ollama.com. Use `tinyllama` for minimal RAM; `phi3:mini` or `qwen3:8b` if you have more (better quality).
- **Foundry** (Windows): Run `.\scripts\install-foundry.ps1` (downloads precompiled binaries). Or use WSL + `curl -L https://foundry.paradigm.xyz | bash` then `foundryup`.
- **Node.js** 18+
- **Python** 3.12+

## Install Dependencies

```powershell
.\scripts\ensure-ollama-model.ps1
.\scripts\install-foundry.ps1
```

Then (after Foundry is on PATH):

```bash
forge install OpenZeppelin/openzeppelin-contracts
cd packages/wallet && npm install
cd packages/agents && pip install -r requirements.txt
```

## Create Agent Wallets

Secrets are saved to `.env` and `.gitignore` is updated to exclude them.

```bash
cd packages/wallet && npm run create-accounts
```

Uses Celo Sepolia by default (`CHAIN_ID=11142220`). No LLM API key needed (Ollama local).

## Deploy Contracts

1. Copy `.env.example` to `.env` and set:
   - `FINANCE_DISTRIBUTOR_ADDRESS` (from create-accounts output)
   - `PRIVATE_KEY` (EOA with testnet CELO for deployment)

2. Fund the deployer EOA via [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia).

3. Deploy (Celo Sepolia default):
   ```powershell
   .\scripts\deploy.ps1 --broadcast
   ```
   Set `RPC_URL` or `CELO_SEPOLIA_RPC_URL` (e.g. `https://rpc.ankr.com/celo_sepolia`) if needed.

4. Save deployed addresses to `.env`:
   ```powershell
   .\scripts\fetch-and-save-addresses.ps1
   ```
   This sets `REVENUE_SERVICE_ADDRESS`, `CONSTITUTION_ADDRESS`, and `COMPUTE_MARKETPLACE_ADDRESS`.

## Celo Sepolia public test path

Full scriptable flow (set env → create wallets → deploy → fund → orchestrate → monitor → verify): see **[docs/CELO-SEPOLIA-TESTNET.md](CELO-SEPOLIA-TESTNET.md)** for the full 8-step flow, command reference, and troubleshooting.

**Short path:**

1. Set `.env` (copy `.env.example`); `CHAIN_NAME=celo-sepolia`, `CHAIN_ID=11142220`, `RPC_URL` or `CELO_SEPOLIA_RPC_URL`.
2. `npm run create-accounts` → then fund deployer at [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia).
3. `npm run testnet:celo` (deploys and saves addresses) → fund **ROOT_STRATEGIST_ADDRESS**.
4. `npm run orchestrate` or `npm run simulation`. Check balances: `.\scripts\celo-sepolia-balances.ps1`.

## Local-first test harness (Anvil)

Canonical full-system validation with **no external faucet** and **deterministic keys**:

1. **One command** (recommended):
   ```bash
   npm run harness:local
   ```
   This: starts or connects to Anvil → deploys contracts → writes `.env.local` with a single deterministic key (Anvil’s first account) for all agents → runs full orchestration (LangGraph + simulation + finance) → writes **simulation_report.json** and **simulation_report.md** in the repo root (tx hashes, balances, distribution, elapsed time).

2. **Clean state (reset chain):**
   ```bash
   npm run harness:local:reset
   ```
   Stops Anvil if running, starts a fresh instance, then runs the same flow.

3. **Repeatable:** Re-run `npm run harness:local` without `-Reset` to reuse the same chain and `.env.local`. No faucet or testnet needed.

4. **Artifacts:** After each run you get:
   - `simulation_log.txt` — full log from the simulation step
   - `simulation_report.json` — structured summary (chain_id, addresses, total_paid_eth, tx_hashes, distribution_tx, threshold_met, balances)
   - `simulation_report.md` — human-readable summary table and tx list

5. **Simulation-only (no orchestration):** `npm run simulation:local` deploys to Anvil and runs the 10-user simulation only, then generates the same report files.

## Production (Celo mainnet)

Before launching on Celo mainnet (chain 42220), use **[docs/PRODUCTION-READINESS.md](PRODUCTION-READINESS.md)** for: production deployment checklist, security and operational checklists, secrets handling, monitoring and alerting, wallet key management, upgrade/governance notes, economic risk, abuse/spam and rate limits, accounting/audit logs, and the recommended minimal v1 launch (no DAO; EOA or multisig owner).
