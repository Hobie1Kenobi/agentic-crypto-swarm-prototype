# Discovery scan → chains & claim routing

`docs/discovery-keyword-scan.json` is built from **Coinbase CDP + PayAI x402 discovery** listings. It is **not** a registry of “where airdrops live.” It mostly contains:

- **HTTP `resource` URLs** (API paths like `/base/`, `/solana/`, `402bnb`, etc.)
- **Snippet text** with payment **asset** addresses (ERC-20 on EVM, or Solana mints)

So the file **does not** include a clean `eip155:…` list. Instead we infer **ecosystems** and map them to **EVM `chain_id`** values for **funding** and **`airdrop_claim_routing.json`**.

## What the keyword scan is *not*

| Expectation | Reality |
|-------------|---------|
| Complete list of chains for real airdrops | **No** — these are x402 **payable APIs**, mostly unrelated to merkle airdrop claims. |
| Same as on-chain claim targets | **No** — your `ClaimSpec` still needs the real distributor contract on the real chain. |

## Inferred ecosystems (typical hits)

From URL paths and names in the scan (run `python scripts/extract-discovery-chain-hints.py` for current counts):

| Ecosystem | Typical `chain_id` (EVM) | Gas token | Notes |
|-----------|----------------------------|-----------|--------|
| **Base** | `8453` (mainnet), `84532` (Sepolia) | ETH | Many snippets reference Base USDC (`0x8335…`). |
| **Celo** | `42220`, `11142220` (Sepolia) | CELO | Aligns with this repo’s default rails. |
| **BNB / BSC** (`402bnb`, etc.) | `56` | BNB | Path/name hints only until you verify on-chain. |
| **Polygon** | `137` | POL/MATIC | Optional x402 path in `config/chains.json`. |
| **Solana** | — | SOL | **Not EVM** — `airdrop_claim` executor does not sign Solana txs. |

## Known asset bytes in snippets (heuristic)

| Address (lowercase) | Implied chain | Asset |
|---------------------|---------------|--------|
| `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | 8453 | Base mainnet USDC |
| `0x036cbd53842c5426634e7929541ec2318f3dcf7e` | 84532 | Base Sepolia USDC |
| `0xf33cac2bb6b26e7615b1873c84e4174ae193a9aa` | Often Base family | USDC variant appearing in listings |

Re-run extraction after each `npm run discovery:keywords` refresh.

## Authoritative routing for the **claim agent** (EVM)

Use **`packages/agents/config/airdrop_claim_routing.json`** (and `AIRDROP_CLAIM_ROUTING_JSON` if you fork it). That file is extended to include the **same** chain IDs as `config/chains.json` where we support agent work, plus **Base mainnet** and **Ethereum mainnet** for mainnet testing.

**You must still** add each **distributor contract** to `allowed_contracts` before execution.

## Regenerate hint summary

```bash
python scripts/extract-discovery-chain-hints.py
python scripts/extract-discovery-chain-hints.py --json
```

## Related docs

- `docs/AIRDROP_CLAIM_EXECUTION.md` — queue, approve, execute
- `docs/airdrop_funding_checklist.example.md` — fund gas per chain
