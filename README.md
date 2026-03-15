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
- [Alchemy](https://alchemy.com/) API key (Base Sepolia)
- LLM API key (Groq preferred)

## Setup

1. **Clone and install**

   ```bash
   git clone https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype.git
   cd agentic-crypto-swarm-prototype
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set:

   - `ALCHEMY_API_KEY` — Base Sepolia RPC
   - `LLM_API_KEY` — Groq or OpenAI
   - `BENEFICIARY_ADDRESS` — Human EOA on Base Sepolia
   - `PIMLICO_API_KEY` — (optional) for bundler/paymaster

3. **Install dependencies**

   ```bash
   forge install OpenZeppelin/openzeppelin-contracts
   cd packages/wallet && npm install
   cd ../agents && pip install -r requirements.txt
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
# Deploy contracts
forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast

# Run swarm (requires LLM_API_KEY in .env)
npm run swarm
# Or: cd packages/agents && python main.py --goal "maximize sustainable revenue via AI service" --max-steps 5
```

## How to Monitor / Claim Profits

- Treasury address: see `.env` after deployment
- Basescan Sepolia: `https://sepolia.basescan.org/address/<TREASURY>`
- Profit distribution triggers when ≥0.05 ETH net profit

## Constraints

- **Testnet only**: Base Sepolia (84532). Never mainnet.
- **No trading/DEX/speculation** — revenue from usage fees only
- **Ethical constitution** — no gambling, illegal content; sustainable compute

## License

MIT
