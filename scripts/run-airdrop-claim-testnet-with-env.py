#!/usr/bin/env python3
"""
Load repo .env and run testnet claim using the best verified wallet:
prefers FINANCE_DISTRIBUTOR (key/address pair matches; typically well funded on Sepolia).

Override with CLAIM_WALLET_ROLE=ROOT_STRATEGIST etc. if that role's *_ADDRESS matches *_PRIVATE_KEY.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env", override=False)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=False)


def _pick_wallet() -> tuple[str, str, str]:
    role = os.getenv("CLAIM_WALLET_ROLE", "FINANCE_DISTRIBUTOR").strip().upper()
    pk_name = f"{role}_PRIVATE_KEY"
    addr_name = f"{role}_ADDRESS"
    pk = os.getenv(pk_name, "").strip()
    declared = os.getenv(addr_name, "").strip()
    if not pk or "your_" in pk.lower():
        raise SystemExit(f"Missing or placeholder {pk_name}")
    derived = Account.from_key(pk).address
    if not declared:
        return role, pk, derived
    if Web3.to_checksum_address(declared).lower() != derived.lower():
        raise SystemExit(
            f"{addr_name} does not match {pk_name} (derived {derived}). Fix .env or set CLAIM_WALLET_ROLE to a matching role."
        )
    return role, pk, derived


def main() -> int:
    role, pk, addr = _pick_wallet()
    os.environ["AIRDROP_CLAIMANT_PRIVATE_KEY"] = pk
    os.environ["AIRDROP_CLAIM_WALLET_ADDRESS"] = addr
    if not os.getenv("CELO_SEPOLIA_RPC_URL") and os.getenv("RPC_URL"):
        os.environ["CELO_SEPOLIA_RPC_URL"] = os.environ["RPC_URL"]
    print(f"Using {role} wallet {addr}", file=sys.stderr)

    path = root / "scripts" / "run-airdrop-claim-testnet.py"
    spec = importlib.util.spec_from_file_location("run_airdrop_claim_testnet", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.main()


if __name__ == "__main__":
    raise SystemExit(main())
