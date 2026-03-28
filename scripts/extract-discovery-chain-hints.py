#!/usr/bin/env python3
"""
Scan docs/discovery-keyword-scan.json (or path arg) for URL paths and known ERC-20 bytes
to infer which *ecosystems* appear in keyword hits. x402 listings are not on-chain claim targets.

Usage:
  python scripts/extract-discovery-chain-hints.py
  python scripts/extract-discovery-chain-hints.py --json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]

# Well-known asset hints → implied EVM chain (for routing / funding notes only)
ASSET_TO_CHAIN_ID: dict[str, tuple[int, str]] = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": (8453, "Base mainnet USDC"),
    "0x036cbd53842c5426634e7929541ec2318f3dcf7e": (84532, "Base Sepolia test USDC"),
    "0xf33cac2bb6b26e7615b1873c84e4174ae193a9aa": (8453, "Common in listings; verify on explorer"),
}

PATH_HINTS = [
    ("base", 8453, "Base (path / product name)"),
    ("bnb", 56, "BNB Chain / BSC (e.g. 402bnb)"),
    ("solana", None, "Solana — not EVM; use Solana wallet, not airdrop_claim"),
    ("celo", 42220, "Celo (name hint)"),
    ("polygon", 137, "Polygon name hint"),
    ("arbitrum", 42161, "Arbitrum name hint"),
    ("optimism", 10, "Optimism name hint"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "path",
        nargs="?",
        default=str(root / "docs" / "discovery-keyword-scan.json"),
        help="discovery-keyword-scan.json",
    )
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.is_file():
        print(f"Missing {p}", flush=True)
        return 1
    data = json.loads(p.read_text(encoding="utf-8"))
    blob = json.dumps(data).lower()
    resources = []
    for h in data.get("top_hits") or []:
        resources.append((h.get("resource") or "") + " " + (h.get("snippet") or ""))

    # Also scan full file if top_hits is truncated
    blob_full = p.read_text(encoding="utf-8").lower()

    path_counts: Counter[str] = Counter()
    for key, _, _ in PATH_HINTS:
        path_counts[key] = blob_full.count(key)

    asset_hits: list[tuple[str, int, str]] = []
    for addr, (cid, note) in ASSET_TO_CHAIN_ID.items():
        if addr.lower() in blob_full:
            asset_hits.append((addr, cid, note))

    out = {
        "source_file": str(p),
        "path_keyword_counts_in_file": dict(path_counts),
        "known_asset_bytecode_hits": [
            {"asset": a, "implied_chain_id": c, "note": n} for a, c, n in asset_hits
        ],
        "evm_chain_ids_to_fund_for_matching_hits": sorted({c for _, c, _ in asset_hits}),
        "non_evm": ["solana"] if path_counts.get("solana", 0) else [],
    }

    if args.as_json:
        print(json.dumps(out, indent=2))
        return 0

    print("Discovery chain / ecosystem hints (from keyword scan file)\n")
    print("URL / name keyword counts (substring, lowercase):")
    for k, v in path_counts.most_common():
        if v:
            print(f"  {k}: {v}")
    print("\nKnown ERC-20 address hints -> implied EVM chain:")
    for a, c, n in asset_hits:
        print(f"  {a[:12]}... chain_id={c} ({n})")
    if not asset_hits:
        print("  (none — snippets may omit full address)")
    print("\nEVM chain IDs implied by asset hints:", out["evm_chain_ids_to_fund_for_matching_hits"])
    print("Non-EVM (not covered by packages/agents/airdrop_claim on EVM):", out["non_evm"] or "—")
    print("\nSee documentation/operations/DISCOVERY_CHAIN_INVENTORY.md for the authoritative mapping table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
