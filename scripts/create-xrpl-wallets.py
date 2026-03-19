#!/usr/bin/env python3
"""
Create and optionally fund XRPL wallets for multi-rail setup.

Creates:
  - XRPL_RECEIVER_ADDRESS: settlement wallet (where agent payments are received)
  - XRPL_WALLET_SEED: payer wallet (agent sends from this; required for live mode)

On testnet, uses the XRPL faucet API (generate_faucet_wallet) to fund both wallets
programmatically—no manual faucet visit required.

Usage:
  python scripts/create-xrpl-wallets.py [--no-fund]
  --no-fund: generate wallets only; you must fund them manually (e.g. via faucet)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)


def find_env_path() -> Path:
    return root / ".env"


def load_existing_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    raw = path.read_text(encoding="utf-8")
    for line in raw.split("\n"):
        if "=" in line and not line.strip().startswith("#"):
            idx = line.index("=")
            k = line[:idx].strip()
            v = line[idx + 1 :].strip().strip("'\"")
            if k:
                out[k] = v
    return out


def write_env(path: Path, updates: dict[str, str]) -> None:
    existing = load_existing_env(path)
    merged = {**existing, **updates}
    keys = sorted(set(existing.keys()) | set(updates.keys()))
    lines: list[str] = []
    for k in keys:
        v = merged.get(k, "")
        if v is not None and v != "":
            lines.append(f"{k}={v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create XRPL wallets for multi-rail setup")
    parser.add_argument(
        "--no-fund",
        action="store_true",
        help="Generate wallets only; do not fund via testnet faucet",
    )
    parser.add_argument(
        "--rpc-url",
        default=os.getenv("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234"),
        help="XRPL RPC URL (default: testnet)",
    )
    args = parser.parse_args()

    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import Wallet, generate_faucet_wallet
    except ImportError as e:
        print("Error: xrpl-py is required. Install with: pip install xrpl-py")
        print(f"  {e}")
        return 1

    env_path = find_env_path()
    existing = load_existing_env(env_path)

    receiver_seed = existing.get("XRPL_RECEIVER_SEED", "").strip()
    payer_seed = existing.get("XRPL_WALLET_SEED", "").strip()
    if "sEd" in receiver_seed or "sEd" in payer_seed:
        print("Existing XRPL wallets found in .env")
        if receiver_seed and "sEd" in receiver_seed:
            print("  XRPL_RECEIVER_ADDRESS already set")
        if payer_seed and "sEd" in payer_seed:
            print("  XRPL_WALLET_SEED already set")
        resp = input("Overwrite? [y/N]: ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return 0

    client = JsonRpcClient(args.rpc_url)
    updates: dict[str, str] = {}

    if args.no_fund:
        receiver_wallet = Wallet.create()
        payer_wallet = Wallet.create()
        updates["XRPL_RECEIVER_SEED"] = receiver_wallet.seed
        updates["XRPL_RECEIVER_ADDRESS"] = receiver_wallet.address
        updates["XRPL_WALLET_SEED"] = payer_wallet.seed
        print("Generated XRPL wallets (not funded):")
        print(f"  Receiver: {receiver_wallet.address}")
        print(f"  Payer:    {payer_wallet.address}")
        print("\nFund them manually (e.g. https://faucet.rippletest.net/) before using live mode.")
    else:
        print("Creating and funding receiver wallet via testnet faucet...")
        receiver_wallet = generate_faucet_wallet(client, debug=True)
        print("Creating and funding payer wallet via testnet faucet...")
        payer_wallet = generate_faucet_wallet(client, debug=True)
        updates["XRPL_RECEIVER_SEED"] = receiver_wallet.seed
        updates["XRPL_RECEIVER_ADDRESS"] = receiver_wallet.address
        updates["XRPL_WALLET_SEED"] = payer_wallet.seed
        print("\nFunded XRPL wallets:")
        print(f"  Receiver: {receiver_wallet.address}")
        print(f"  Payer:    {payer_wallet.address}")

    updates["XRPL_NETWORK"] = "testnet"
    updates["XRPL_RPC_URL"] = args.rpc_url
    if not existing.get("XRPL_PAYMENT_MODE"):
        updates["XRPL_PAYMENT_MODE"] = "live"
    if not existing.get("XRPL_ENABLED"):
        updates["XRPL_ENABLED"] = "1"

    write_env(env_path, updates)
    print(f"\nSaved to {env_path}")
    print("Set PAYMENT_RAIL_MODE=hybrid_public_request_xrpl_payment_private_celo_settlement for multi-rail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
