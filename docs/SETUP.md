# Setup Guide

## Prerequisites

- **Foundry**: Install from https://getfoundry.sh (Windows: `curl -L https://foundry.paradigm.xyz | bash` then `foundryup`)
- **Node.js** 18+
- **Python** 3.12+

## Install Dependencies

```bash
forge install OpenZeppelin/openzeppelin-contracts
cd packages/wallet && npm install
cd ../agents && pip install -r requirements.txt
```

## Create Agent Wallets

Secrets are saved to `.env` and `.gitignore` is updated to exclude them.

```bash
npm run create-accounts
```

Requires `ALCHEMY_API_KEY` in `.env` for reliable RPC (or uses public Base Sepolia RPC).

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
