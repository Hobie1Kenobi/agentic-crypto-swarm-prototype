# Celo Sepolia Public Test Run Report

## Summary
- Goal: Minimal Celo Sepolia deployment + revenue orchestration (`fulfillQuery` fee split + `finance_distributor` distribution).
- Result: SUCCESS for the revenue flow on Celo Sepolia.
- Note: The task marketplace demo hit an error in this run (`Task marketplace demo error: ('0x90a1afd6', '0x90a1afd6')`) but the revenue orchestration still completed.

## Environment
- Chain ID: `11142220`
- Explorer: `https://celo-sepolia.blockscout.com`
- RPC used: `https://forno.celo-sepolia.celo-testnet.org`

## Accounts (from `.env`)
- Deployer EOA (`PRIVATE_KEY`): `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b`
- Root Strategist payer EOA (`ROOT_STRATEGIST_PRIVATE_KEY`): `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC`
- Finance Distributor signer EOA (`FINANCE_DISTRIBUTOR_PRIVATE_KEY`): `0xCF3572136265A5ED34D412200E63017e39223592`
- Beneficiary: `0x5551abbAF9Eb240BaC81aE49199f96f678D58f05`

## Deployed Contracts
- AgentRevenueService (`REVENUE_SERVICE_ADDRESS`): `0xd3696313f9b40edc6d5e5b48b888fe5b81ac5627`
- Constitution (`CONSTITUTION_ADDRESS`): `0x1831aecf19865cdcdb6b1bccebee91f08d3a80fb`
- ComputeMarketplace (`COMPUTE_MARKETPLACE_ADDRESS`): `0xca23af67b8a0518fc69d4b858b0cdfd3aac19d9c`

## Revenue Flow tx hashes
- `fulfillQuery` tx: `https://celo-sepolia.blockscout.com/tx/0x16e3f58052364a1307ee2fbdff01e655fe5c661563065ce73c86cb23ca256592`
- `distribution` tx: `https://celo-sepolia.blockscout.com/tx/0x1fcc3573afe1e5c8e64366ff8cf5f489340eae8894245b90ec056e0ecdf725ad`

## Post-run Balances (Forno)
- `AgentRevenueService` contract: `0.0004` CELO
- `FINANCE_DISTRIBUTOR_ADDRESS` EOA: `2.399497` CELO
- `BENEFICIARY_ADDRESS` EOA: `8.4` CELO
