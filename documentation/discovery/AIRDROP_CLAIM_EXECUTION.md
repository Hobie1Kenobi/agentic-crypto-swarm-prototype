# Airdrop claim execution (approval-gated)

This document describes the **executable** path for on-chain claims after you have **correct calldata** for a distributor contract. It is **not** a generic “find and claim any airdrop” bot: each protocol uses different ABIs; you (or tooling you trust) must supply `chain_id`, `to`, and `data`.

## Components

| Piece | Role |
|-------|------|
| `packages/agents/config/airdrop_claim_routing.json` | Per-chain RPC env order, **contract allowlist**, gas/value caps, explorer URL, optional `expected_signer_env` |
| `external_commerce_data/airdrop_claim_queue.sqlite` | SQLite queue (`AIRDROP_CLAIM_QUEUE_DB` to override path) |
| `AIRDROP_CLAIMANT_PRIVATE_KEY` | Signs claim txs (dedicated hot wallet; low balance) |
| `AIRDROP_CLAIM_WALLET_ADDRESS` | Must match the address derived from the key if `expected_signer_env` is set in routing |
| `scripts/airdrop-claim-queue.py` | CLI: `add`, `list`, `show`, `approve`, `reject`, `dry-run`, `execute` |
| `packages/agents/airdrop_claim/graph_runner.py` | LangGraph wrapper: `run_approved_claim(claim_id)` |

## Safety defaults

1. **`AIRDROP_CLAIM_EXECUTION_ENABLED=1`** must be set to broadcast. Without it, `execute` refuses.
2. **`allowed_contracts`** in routing must list every distributor you are willing to call, **or** you must explicitly set **`AIRDROP_CLAIM_ALLOW_UNLISTED=1`** (dangerous on mainnet).
3. **`approve`** is a human gate: nothing broadcasts until you run `approve` and then `execute --i-understand`.
4. **Constitution / ToS:** Only claim where you are authorized; this repo does not bypass KYC or sybil rules.

## Funding claims: XRPL → EVM, Coinbase, and where tokens land

**Important:** Do **not** paste private keys or seed phrases into chat, tickets, or git. Keep them in **local `.env`** only. Public **deposit addresses** from Coinbase are fine to record **in your own** private notes or a **local** copy of the checklist template — not in a public repo.

### What Xaman / XRP can and cannot do

| | |
|--|--|
| **Xaman (XRPL)** | Holds **XRP**; signs **XRPL** transactions only. |
| **EVM airdrop claims** | Need an **EVM wallet** (same `0x…` family as MetaMask) and **native gas** on the chain where you submit the claim (ETH, CELO, etc.). |
| **Direct “pay gas with XRP”** | **Not** possible on Ethereum/Base/Celo without converting or bridging value into that ecosystem first. |

So “use my XRP” means: **move value** (via Coinbase or another path) until your **claim signer** has enough **native** on each chain you will execute on.

### Using Coinbase to fund the claim wallet

1. In Coinbase, use **Send / Receive** and note the **deposit address per asset and network** (e.g. “Receive ETH on **Base**”, “Receive USDC on **Celo**”). Coinbase shows a **different** deposit string per **network** — always match **asset + network** to where you intend to withdraw.
2. **Sell or convert** XRP → the asset you will withdraw (ETH, USDC, CELO, etc.) per Coinbase’s UI.
3. **Withdraw to self-custody**: send to the **`0x` address** that matches the private key you will use as `AIRDROP_CLAIMANT_PRIVATE_KEY` (or a hardware wallet you export to a **dedicated hot key** only for low-value claims — your operational choice).
4. **Minimum per chain:** fund enough **native** on that chain to cover **deploy (if any) + claim + buffer** (e.g. 2–5× a single claim gas estimate for mainnet).

### Where airdrop tokens “go”

- Most **claim()** contracts credit **`msg.sender`** — the **same address that signs the claim tx**. That should be your **`AIRDROP_CLAIMANT`** EVM address.
- Some contracts allow an **explicit recipient** in the calldata; then you could point to a **vault** address — only if the ABI supports it and you trust the calldata you build.
- **Do not** assume Coinbase deposit addresses are the claim recipient unless you deliberately built the claim that way; default is **your hot claim wallet** receives tokens.

### Bridging between EVM chains (after you have assets on one EVM)

This repo already includes **Celo → Base (USDC)** via LI.FI for other flows (`scripts/bridge_utils.py`). Same idea applies conceptually: move **USDC / native** between chains using an aggregator or official bridge **after** you have funds on an EVM. There is **no** automatic “XRP → all chains” in this repo; fund the **target chain** your `ClaimSpec.chain_id` uses.

### What to prepare locally (checklist)

Copy `docs/airdrop_funding_checklist.example.md` to a **gitignored** file (e.g. `docs/airdrop_funding_checklist.local.md` — add to `.gitignore` if you store real addresses) and fill:

- Which **chains** you will claim on (chain IDs).
- **RPC URLs** (mainnet) in `.env` — never commit keys.
- **One EVM claim signer** (`AIRDROP_CLAIMANT_PRIVATE_KEY` / matching `AIRDROP_CLAIM_WALLET_ADDRESS`).
- Optional: Coinbase **receive** addresses you use **only** as withdrawal destinations (still your custody once withdrawn).

### Mainnet testing (agents)

1. Complete routing in `airdrop_claim_routing.json` for each **mainnet** `chain_id` (RPC env vars, `explorer_url`, **strict** `allowed_contracts`).
2. Fund the claim wallet on **each** chain you will execute on.
3. Set `AIRDROP_CLAIM_EXECUTION_ENABLED=1` only when ready; use `dry-run` first.
4. Start with **one** small claim and verify on the block explorer before scaling.

## See it work locally (Anvil demo)

Uses a **mock** distributor contract (`contracts/MockClaimDistributor.sol`) and the Anvil default account — **not** mainnet.

1. Install Foundry (`forge`, `anvil` on PATH).
2. From repo root:

```bash
npm run airdrop:claim:demo
```

This runs `python scripts/run-airdrop-claim-local-demo.py --spawn-anvil` (starts Anvil on **8546** to avoid clashing with anything on 8545), compiles the contract, deploys, queues `claim(42)`, approves, executes, and prints the tx hash.

If you already run Anvil yourself on `http://127.0.0.1:8545`:

```bash
python scripts/run-airdrop-claim-local-demo.py --rpc http://127.0.0.1:8545
```

Artifacts: `external_commerce_data/airdrop_claim_routing.anvil-demo.json`, `external_commerce_data/airdrop_claim_demo.sqlite`.

## Real testnet (Celo Sepolia)

Uses the **same** mock contract and claim queue, but on **chain 11142220** with your RPC and keys (real test CELO for gas — not mainnet).

1. Fund a **dedicated** test wallet from [Celo Sepolia faucet](https://faucet.celo.org/celo-sepolia).
2. In `.env` set:
   - `CELO_SEPOLIA_RPC_URL` (or `PRIVATE_RPC_URL` / `RPC_URL` if it points at Celo Sepolia)
   - `AIRDROP_CLAIMANT_PRIVATE_KEY` — private key of the funded wallet  
   - Optionally `AIRDROP_CLAIM_WALLET_ADDRESS` — must match the address derived from that key (routing uses `expected_signer_env`)
3. Run:

```bash
npm run airdrop:claim:testnet
```

This deploys `MockClaimDistributor`, writes `external_commerce_data/airdrop_claim_routing.celo-sepolia-session.json` (allowlists that deployment), uses `airdrop_claim_testnet.sqlite`, then queues → approves → executes. You get a **Blockscout** link in the output.

**Using existing swarm keys from `.env`** (must have matching `*_ADDRESS` / `*_PRIVATE_KEY` pairs):

```bash
npm run airdrop:claim:testnet:env
```

This runs `scripts/run-airdrop-claim-testnet-with-env.py`, defaulting to **`CLAIM_WALLET_ROLE=FINANCE_DISTRIBUTOR`**. Override with e.g. `CLAIM_WALLET_ROLE=TREASURY` if that role’s keys match.

For a **production-style** claim (your own distributor + calldata), skip this script and use `airdrop:claim` with a hand-built `ClaimSpec` after adding the contract to `airdrop_claim_routing.json`.

## Workflow

### 1. Configure routing

Edit `packages/agents/config/airdrop_claim_routing.json` (or copy to a private path and set `AIRDROP_CLAIM_ROUTING_JSON`):

- Set **`allowed_contracts`** to the distributor contract address(es) per chain.
- Set **`rpc_env_vars`** so your `.env` provides a working RPC (e.g. `CELO_SEPOLIA_RPC_URL`).
- Set **`explorer_url`** for transaction links in logs.

### 2. Build calldata

Use your protocol’s ABI (or helpers below):

- **OpenZeppelin-style Merkle claim** (common):

```python
from airdrop_claim.calldata_builders import encode_claim_oz_merkle

data = encode_claim_oz_merkle(
    index=0,
    account="0xYourClaimWallet",
    amount=1234567890123456789,
    merkle_proof=["0x...", "0x..."],
)
```

- **Raw**: any `0x` calldata from Etherscan “Write contract”, cast, or your own script.

### 3. Create a ClaimSpec JSON

Example `claim.json`:

```json
{
  "chain_id": 11142220,
  "to": "0xYourDistributorContract",
  "data": "0x...",
  "value_wei": 0,
  "signer_role": "AIRDROP_CLAIMANT",
  "label": "Project X merkle claim",
  "source_url": "https://docs.example.com/airdrop",
  "notes": "Approved by me after reading the contract on Blockscout"
}
```

### 4. Queue → approve → execute

```bash
# From repo root, .env loaded
python scripts/airdrop-claim-queue.py add claim.json
python scripts/airdrop-claim-queue.py list
python scripts/airdrop-claim-queue.py approve <uuid>
python scripts/airdrop-claim-queue.py dry-run <uuid>
set AIRDROP_CLAIM_EXECUTION_ENABLED=1
python scripts/airdrop-claim-queue.py execute <uuid> --i-understand
```

Or: `npm run airdrop:claim -- add claim.json` (npm passes args after `--`).

### 5. Programmatic (LangGraph)

```python
from airdrop_claim.graph_runner import run_approved_claim

run_approved_claim("<uuid>", dry_run=False)
```

## Relation to discovery / scout

- **Keyword discovery** and **airdrop intelligence** produce *candidates* and *scores*; they do **not** generate calldata.
- Typical pipeline: scout → you verify contract + proof off-chain → build `ClaimSpec` → queue → approve → execute.

## Troubleshooting

| Issue | Check |
|-------|--------|
| “No routing entry for chain_id” | Add chain to `airdrop_claim_routing.json` |
| “Contract … not in allowed_contracts” | Add address to `allowed_contracts` or (test only) `AIRDROP_CLAIM_ALLOW_UNLISTED=1` |
| “expected_signer_env … does not match signer” | Align `AIRDROP_CLAIM_WALLET_ADDRESS` with `AIRDROP_CLAIMANT_PRIVATE_KEY` |
| “Execution disabled” | `AIRDROP_CLAIM_EXECUTION_ENABLED=1` |
