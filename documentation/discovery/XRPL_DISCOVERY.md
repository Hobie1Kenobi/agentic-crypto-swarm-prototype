# XRPL discovery & validation (x402)

Separate from the EVM keyword scan (`discovery:keywords`). This pipeline **filters** the same public x402 discovery catalogs (Coinbase CDP + PayAI) for listings that appear to use **XRPL or XRP** as the payment rail.

## Commands

```bash
npm run discovery:xrpl
# or
python scripts/run-xrpl-discovery-scan.py
```

Optional config: `XRPL_DISCOVERY_CONFIG` → path to `packages/agents/config/xrpl_discovery_scan.json`.

Outputs:

- `external_commerce_data/xrpl-discovery-hits.jsonl`
- `external_commerce_data/xrpl-discovery-scan-summary.json`
- `docs/xrpl-discovery-scan.json` / `docs/xrpl-discovery-scan.md`

## Validator (`packages/agents/xrpl_discovery/validate.py`)

- **`is_valid_classic_address(addr)`** — classic `r…` addresses (uses `xrpl-py` when available).
- **`validate_discovery_hit(record)`** — optional checks on JSON rows you build (e.g. `wallet_hint`).
- **`validate_env_wallet_hint`** — for sanity-checking `XRPL_RECEIVER_ADDRESS` / similar in env.

## Xaman

- **Discovery** is **read-only HTTP** — no wallet secret required.
- **Xaman** does not expose signing to this repo. For **automated** XRPL payments (x402, T54), the codebase uses **`XRPL_WALLET_SEED`** (or related env) for a **hot** machine wallet — keep balance small.
- Use **Xaman** to **review** discovered URLs and to operate manually when you do not want agent signing.

## Optional keywords

Edit `optional_keywords` in `xrpl_discovery_scan.json`. If non-empty, only rows matching **at least one** optional keyword (in addition to passing the XRPL filter) are kept.

## Relation to EVM airdrop claiming

XRPL discovery surfaces **payable HTTP APIs**, not on-ledger merkle airdrops. For EVM claims, see `docs/AIRDROP_CLAIM_EXECUTION.md`.
