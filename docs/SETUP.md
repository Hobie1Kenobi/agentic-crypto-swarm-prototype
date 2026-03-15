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
npm run create-accounts
```

Uses public Base Sepolia RPC if `ALCHEMY_API_KEY` is not set. No LLM API key needed (Ollama local).

## Deploy Contracts

1. Copy `.env.example` to `.env` and set:
   - `ALCHEMY_API_KEY`
   - `FINANCE_DISTRIBUTOR_ADDRESS` (from create-accounts output)
   - `PRIVATE_KEY` (EOA with testnet ETH for deployment)

2. Fund the deployer EOA via [Base Sepolia Faucet](https://basefaucet.com/)

3. Deploy:
   ```bash
   source .env  # or use dotenv
   forge script script/Deploy.s.sol --rpc-url https://base-sepolia.g.alchemy.com/v2/$ALCHEMY_API_KEY --broadcast
   ```

4. Update `.env` with deployed addresses:
   - `REVENUE_SERVICE_ADDRESS`
   - `CONSTITUTION_ADDRESS`
