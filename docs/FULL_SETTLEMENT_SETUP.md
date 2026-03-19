# Full Celo Settlement Setup

Full settlement requires five distinct addresses: requester, worker, validator, treasury, finance_distributor.

## Steps

### 1. Create accounts (includes TREASURY)

```bash
npm run create-accounts
```

This generates `TREASURY_PRIVATE_KEY` and `TREASURY_ADDRESS` (EOA) in addition to the four agent keys.

### 2. Deploy contracts

Ensure `.env` has:
- `PRIVATE_KEY` (deployer EOA with CELO)
- `TREASURY_ADDRESS` (from create-accounts)
- `FINANCE_DISTRIBUTOR_ADDRESS` (from create-accounts)

```powershell
.\scripts\deploy.ps1 --broadcast
.\scripts\fetch-and-save-addresses.ps1
```

### 3. Fund addresses

Fund on Celo Sepolia:
- **ROOT_STRATEGIST_ADDRESS** — requester; needs ~0.02 CELO for escrow + gas
- **TREASURY_ADDRESS** — receives protocol fee; can be funded with 0.001 CELO for gas to claim
- **IP_GENERATOR_ADDRESS** — worker; needs gas for accept/submit
- **DEPLOYER_ADDRESS** — validator; needs gas for score/finalize
- **FINANCE_DISTRIBUTOR_ADDRESS** — receives finance fee; needs gas to claim

### 4. Role defaults

For five distinct addresses, use:
- `TASK_REQUESTER_ROLE=ROOT_STRATEGIST`
- `TASK_WORKER_ROLE=IP_GENERATOR`
- `TASK_VALIDATOR_ROLE=DEPLOYER`

### 5. Run task demo

```bash
cd packages/agents && python -c "
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('../../.env'), override=True)
from task_market_demo import run_task_market_demo
r = run_task_market_demo()
print('ok:', r.get('ok'), 'task_id:', (r.get('task') or {}).get('task_id'))
"
```

## Or use the script

```powershell
.\scripts\enable-full-settlement.ps1
```

This runs create-accounts, deploy, fetch-addresses, and task demo. You will be prompted before deploy. Ensure deployer and ROOT_STRATEGIST are funded first.
