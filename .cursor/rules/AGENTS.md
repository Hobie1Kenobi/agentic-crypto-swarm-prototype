# Agentic Crypto Swarm — Cursor Rules

## Project Overview
Hierarchical multi-agent system for autonomous testnet revenue via on-chain value creation (no trading/speculation). Celo-first: Celo Sepolia (11142220) testnet, Celo mainnet (42220) production; local Anvil (31337); Base Sepolia (84532) legacy/optional.

## Tech Stack
- **Contracts**: Foundry, Solidity 0.8.28+, OpenZeppelin
- **Agent orchestration**: Python 3.12, LangGraph, web3.py
- **Wallet layer**: ERC-4337 via permissionless.js (Pimlico on Base; Celo may use signer or other bundler)
- **Deployment**: viem (TS scripts) + Foundry
- **LLM**: Ollama (local; default model tinyllama, or phi3:mini / qwen3:8b)

## Code Conventions
- No raw private keys in code; use env vars
- Every agent = isolated ERC-4337 smart account with 0.01 ETH daily spending cap
- Session keys for temporary agent signing
- Paymaster for gasless ops where possible
- Ethical constitution: no gambling, no illegal content, sustainable compute

## File Structure
```
/contracts          — Solidity (Foundry)
/scripts            — TS deployment (viem) + Python agents
/packages/agents    — LangGraph swarm orchestration
/packages/wallet    — Smart account creation, UserOps
/tests              — Foundry + pytest
```

## Security Checklist
- Spending limits enforced on all agent wallets
- Reentrancy guards on revenue contract
- Events for verifiable audit trail
- Mainnet only after validation; default testnet Celo Sepolia
