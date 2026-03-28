# Celo Sepolia Public Test Path

Reproducible flow for running the swarm on **Celo Sepolia** (chain ID 11142220). No bundler required; uses signer-based executor.

---

## 1. Set environment variables

Copy the example env and set Celo Sepolia values:

```powershell
copy .env.example .env
```

Edit `.env` and set (minimum for deploy + orchestration):

| Variable | Required | Example / notes |
|----------|----------|-----------------|
| `CHAIN_NAME` | Yes | `celo-sepolia` |
| `CHAIN_ID` | Yes | `11142220` |
| `RPC_URL` or `CELO_SEPOLIA_RPC_URL` | Yes | `https://rpc.ankr.com/celo_sepolia` |
| `EXPLORER_URL` | Optional | `https://celo-sepolia.blockscout.com` |
| `BENEFICIARY_ADDRESS` | For distribution | Your EOA to receive profit share |
| `PRIVATE_KEY` | For deploy | Deployer EOA (see step 2) |
| `FINANCE_DISTRIBUTOR_ADDRESS` | For deploy | From create-accounts (see step 2) |

Optional: `ORCHESTRATE_MAX_STEPS` (default 5), `SIMULATION_PROFIT_THRESHOLD_ETH` (default 0.005), `SIMULATION_NUM_USERS` (default 10).

---

## 2. Create or import agent wallets

**Option A — Generate new keys (recommended for first run):**

```bash
npm run create-accounts
```

This writes to `.env`: `ROOT_STRATEGIST_PRIVATE_KEY`, `IP_GENERATOR_PRIVATE_KEY`, `DEPLOYER_PRIVATE_KEY`, `FINANCE_DISTRIBUTOR_PRIVATE_KEY`, and the corresponding `*_ADDRESS` values. Uses Celo Sepolia by default (`CHAIN_ID=11142220`).

**Option B — Import existing keys:**  
Set the four `*_PRIVATE_KEY` vars and the four `*_ADDRESS` vars in `.env` (addresses must match the keys). For deploy you need at least `PRIVATE_KEY` (can be the same as `ROOT_STRATEGIST_PRIVATE_KEY`) and `FINANCE_DISTRIBUTOR_ADDRESS`.

---

## 3. Deploy contracts

Fund the **deployer** account with testnet CELO:

- Faucet: [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia)
- Use the address that corresponds to `PRIVATE_KEY` (or `ROOT_STRATEGIST_ADDRESS` if you use that key as deployer)

Deploy and save addresses to `.env`:

```powershell
.\scripts\deploy.ps1 --broadcast
.\scripts\fetch-and-save-addresses.ps1
```

Or use the one-shot script (deploy + fetch addresses, then you fund and run):

```powershell
.\scripts\run-celo-sepolia-e2e.ps1
```

After deploy, `.env` will contain `REVENUE_SERVICE_ADDRESS`, `CONSTITUTION_ADDRESS`, `COMPUTE_MARKETPLACE_ADDRESS`.

---

## 4. Fund required accounts

Fund these addresses with CELO on Celo Sepolia (same faucet as above):

| Account | Purpose | Suggested |
|---------|---------|-----------|
| **Deployer** (`PRIVATE_KEY` / address used in step 3) | Already used for deploy | — |
| **Root Strategist** (`ROOT_STRATEGIST_ADDRESS`) | Pays for simulation `fulfillQuery` txs | ≥ 0.02 CELO for 10+ queries |
| **Finance Distributor** (optional) | Receives 50% of query payments; needs CELO to send distribution tx | Small amount for gas |

`BENEFICIARY_ADDRESS` does not need funding; it only receives CELO when distribution runs.

---

## 5. Run orchestration

Full graph (strategist → IP-generator → deployer check → simulation → finance):

```bash
npm run orchestrate
```

Or simulation only (10 synthetic users paying 0.001 CELO each):

```bash
npm run simulation
```

Use `--max-steps` to limit graph steps when running orchestration from the repo root:

```bash
cd packages/agents && python main.py --max-steps 10
```

---

## 6. Monitor balances

- **From repo:** Use the balance helper (if available) or check the explorer.
- **Explorer:** [Celo Sepolia Blockscout](https://celo-sepolia.blockscout.com)

Check these addresses (from `.env`):

- `REVENUE_SERVICE_ADDRESS` — holds the 40% remainder of each payment
- `FINANCE_DISTRIBUTOR_ADDRESS` — receives 50% of each payment; balance used for distribution when above threshold
- `ROOT_STRATEGIST_ADDRESS` — payer; balance decreases with each `fulfillQuery`
- `BENEFICIARY_ADDRESS` — receives 60% of finance balance when distribution runs

**Using the balance script (reads addresses from `.env`):**

```powershell
.\scripts\celo-sepolia-balances.ps1
```

**Using Foundry `cast` (optional):**

```powershell
$rpc = "https://rpc.ankr.com/celo_sepolia"
cast balance $env:FINANCE_DISTRIBUTOR_ADDRESS --rpc-url $rpc
cast balance $env:REVENUE_SERVICE_ADDRESS --rpc-url $rpc
```

---

## 7. Verify distributions

- When finance distributor balance ≥ `SIMULATION_PROFIT_THRESHOLD_ETH` (default 0.005), the simulation step sends 60% to `BENEFICIARY_ADDRESS` and leaves 40% in the finance address.
- Check `simulation_log.txt` for lines like `Distribution tx: 0x...` and `Threshold met`.
- In the explorer, open `BENEFICIARY_ADDRESS` and confirm incoming CELO transfer(s) after a run that hit the threshold.

---

## 8. Inspect events in explorer

- **Contract:** [Blockscout Celo Sepolia](https://celo-sepolia.blockscout.com) → search for `REVENUE_SERVICE_ADDRESS`.
- **Events:** `QueryFulfilled(queryHash, payer, amount, resultMetadata)`, `FeeDistributed(to, amount)`.
- **Tx hashes:** Listed in `simulation_log.txt`; open `https://celo-sepolia.blockscout.com/tx/<TX_HASH>`.

---

## Quick reference: deploy/run commands

| Step | Command |
|------|--------|
| Create wallets | `npm run create-accounts` |
| Deploy + save addresses | `npm run testnet:celo` or `.\scripts\run-celo-sepolia-e2e.ps1` (then fund Root Strategist) |
| Deploy only | `.\scripts\deploy.ps1 --broadcast` then `npm run fetch-addresses` |
| Run orchestration | `npm run orchestrate` |
| Run simulation only | `npm run simulation` |
| Check balances | `.\scripts\celo-sepolia-balances.ps1` |

---

## Troubleshooting

### "Set PRIVATE_KEY" or "Set FINANCE_DISTRIBUTOR_ADDRESS"
- Run `npm run create-accounts` so `.env` gets `PRIVATE_KEY` and `FINANCE_DISTRIBUTOR_ADDRESS` (and other agent keys/addresses). If you import keys, set these two and the deploy script will use them.

### "Insufficient funds" or deploy/orchestration fails with balance errors
- Fund the deployer address (the one for `PRIVATE_KEY`) with CELO from the [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia).
- For simulation, fund `ROOT_STRATEGIST_ADDRESS` (at least ~0.02 CELO for 10 queries + gas).

### RPC errors or "could not connect"
- Set `RPC_URL` or `CELO_SEPOLIA_RPC_URL` to a working RPC, e.g. `https://rpc.ankr.com/celo_sepolia` or `https://forno.celo-sepolia.celo-testnet.org`.
- If one provider is rate-limited, try another (e.g. Infura with `CELO_SEPOLIA_RPC_URL=https://celo-sepolia.infura.io/v3/YOUR_KEY`).

### Wrong chain / wrong explorer
- Ensure `CHAIN_ID=11142220` and `CHAIN_NAME=celo-sepolia` in `.env`. Do not use 84532 (Base) or 31337 (Anvil) for this path.
- Explorer for Celo Sepolia: https://celo-sepolia.blockscout.com (not Basescan).

### Simulation runs but no distribution
- Distribution runs only when the **finance distributor** balance is ≥ `SIMULATION_PROFIT_THRESHOLD_ETH` (default 0.005). With 10 users at 0.001 CELO each, 50% goes to finance (0.005 CELO), so one full run may exactly meet the threshold. If it doesn’t, run simulation again or lower `SIMULATION_PROFIT_THRESHOLD_ETH` in `.env`.

### "REVENUE_SERVICE_ADDRESS not set"
- Run deploy and then `.\scripts\fetch-and-save-addresses.ps1` (or `.\scripts\run-celo-sepolia-e2e.ps1`) so that `REVENUE_SERVICE_ADDRESS` is written to `.env`.

### Orchestration exits after one step
- Default `--max-steps` is 5. Use `cd packages/agents && python main.py --max-steps 10` for more steps, or set `ORCHESTRATE_MAX_STEPS=10` in `.env`.

### Faucet does not send or rate-limits
- Use the official [Celo Sepolia Faucet](https://faucet.celo.org/celo-sepolia). If you hit limits, wait and retry or use an alternative Celo Sepolia faucet if documented by the Celo ecosystem.
