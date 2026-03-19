# Full deployment and testing (local Anvil)

Run these in order to deploy and test x402, compute marketplace, and DAO on local Anvil.

## 1. Deploy contracts

```powershell
.\scripts\deploy-local-only.ps1
```

Writes `.env.local` with `REVENUE_SERVICE_ADDRESS`, `COMPUTE_MARKETPLACE_ADDRESS`, Anvil keys, and `COMPUTE_MINER_URLS=http://127.0.0.1:8043`. Keeps Anvil running (or starts it).

## 2. Test x402 API

**Terminal A – start API:**

```powershell
npm run api:402
```

**Terminal B – get 402, then pay and retry:**

```powershell
# Expect 402 + payment JSON
Invoke-WebRequest -Uri "http://127.0.0.1:8042/query?q=hello" -UseBasicParsing

# Send payment (from repo root; prints tx hash):
cd packages\agents
python pay_and_get_tx_hash.py "x402:hello"
# Use the printed tx hash in the next request (replace YOUR_TX_HASH):
Invoke-WebRequest -Uri "http://127.0.0.1:8042/query?q=hello" -Headers @{"X-Payment-Tx-Hash"="YOUR_TX_HASH"} -UseBasicParsing
```

## 3. Test compute marketplace

**Terminal A – miner (registers on-chain, serves POST /task):**

```powershell
npm run miner
```

**Terminal B – validator (after miner is up):**

```powershell
npm run validator
```

**Fund and distribute:**

```powershell
# Fund marketplace (use COMPUTE_MARKETPLACE_ADDRESS from .env.local)
cast send $env:COMPUTE_MARKETPLACE_ADDRESS --value 0.01ether --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --rpc-url http://127.0.0.1:8545

# Distribute rewards to miners by score
cast send $env:COMPUTE_MARKETPLACE_ADDRESS "distributeRewards()" --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 --rpc-url http://127.0.0.1:8545
```

## 4. Deploy DAO and verify

```powershell
npm run deploy:dao
```

Then verify ownership of `AgentRevenueService` is the Timelock:

```powershell
$revenue = (Get-Content .env.local | Where-Object { $_ -match 'REVENUE_SERVICE_ADDRESS=(.+)' }) -replace 'REVENUE_SERVICE_ADDRESS=',''
cast call $revenue "owner()(address)" --rpc-url http://127.0.0.1:8545
# Should output the TimelockController address (see deploy logs).
```

## One-liner deploy + DAO (no orchestration)

```powershell
.\scripts\deploy-local-only.ps1
npm run deploy:dao
```

Then run x402, miner, validator, and fund/distribute as above.
