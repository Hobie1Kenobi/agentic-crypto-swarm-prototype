# Airdrop funding & routing checklist (local copy — do not commit real addresses if private)

Copy this file to `airdrop_funding_checklist.local.md` (or similar) and add `*.local.md` to `.gitignore` if it contains sensitive operational notes.

**Do not** put private keys in this file. Use `.env` for keys.

## Claim signer (EVM)

| Field | Your value |
|-------|------------|
| Label | e.g. `airdrop-hot-1` |
| `AIRDROP_CLAIM_WALLET_ADDRESS` (`0x…`) | |
| Where the key lives | e.g. hardware wallet / MetaMask / `.env` only |

## Per chain (add rows for each network you claim on)

| Chain name | Chain ID | Gas token | RPC env var in `.env` | Funded? (Y/N) | Notes |
|------------|----------|-----------|------------------------|---------------|-------|
| Celo mainnet | 42220 | CELO | e.g. `CELO_MAINNET_RPC_URL` | | |
| Base | 8453 | ETH | | | |
| Ethereum | 1 | ETH | | | |
| … | | | | | |

## Coinbase withdrawal targets (optional — public deposit addresses only)

Use Coinbase **Receive** UI to copy **deposit address for the exact asset + network**. Withdraw to the **same** `0x` self-custody address as your claim wallet when possible.

| Asset | Network in Coinbase | Coinbase receive address (or “same as claim wallet”) |
|-------|---------------------|--------------------------------------------------------|
| e.g. USDC | Base | |
| e.g. ETH | Base | |

## Bridging (after EVM is funded)

| From chain | To chain | Tool | Notes |
|------------|----------|------|-------|
| Celo | Base USDC | `scripts/bridge_utils.py` / LI.FI | See repo `bridge_utils` |

## XRPL (Xaman) — source of liquidity only

| Item | Note |
|------|------|
| XRP balance | Source of funds before conversion via Coinbase |
| Claim execution | Not signed by Xaman for EVM; fund EVM claim wallet first |
