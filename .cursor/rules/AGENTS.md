# Agentic Crypto Swarm — Cursor Rules

## Project Overview
Hierarchical multi-agent system for autonomous testnet revenue via on-chain value creation (no trading/speculation). Base Sepolia only (chain ID 84532).

## Tech Stack
- **Contracts**: Foundry, Solidity 0.8.28+, OpenZeppelin
- **Agent orchestration**: Python 3.12, LangGraph, web3.py
- **Wallet layer**: ERC-4337 via permissionless.js (Pimlico) or ZeroDev
- **Deployment**: viem (TS scripts) + Foundry
- **LLM**: Groq or OpenAI

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
- No mainnet deployment
