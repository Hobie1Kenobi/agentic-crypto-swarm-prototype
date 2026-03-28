#!/usr/bin/env python3
"""
Real testnet run (default: Celo Sepolia 11142220): deploy MockClaimDistributor → queue → approve → execute.

Requires in .env (or environment):
  - CELO_SEPOLIA_RPC_URL or PRIVATE_RPC_URL or RPC_URL pointing at Celo Sepolia
  - AIRDROP_CLAIMANT_PRIVATE_KEY  (funded with test CELO for gas)
  - AIRDROP_CLAIM_WALLET_ADDRESS  optional; defaults to address derived from the key (must match routing expected_signer)

Costs a small amount of test CELO for deploy + claim gas.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

load_dotenv(root / ".env", override=False)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=False)

DEFAULT_CHAIN = 11142220
MIN_BALANCE_WEI = 50_000_000_000_000_000  # 0.05 native — warn below this
ARTIFACT = root / "out" / "MockClaimDistributor.sol" / "MockClaimDistributor.json"
BASE_ROUTING = root / "packages" / "agents" / "config" / "airdrop_claim_routing.json"


def _resolve_celo_sepolia_rpc() -> str:
    for key in ("CELO_SEPOLIA_RPC_URL", "PRIVATE_RPC_URL", "RPC_URL"):
        v = os.getenv(key, "").strip()
        if v and "your_" not in v.lower():
            return v
    return ""


def main() -> int:
    from airdrop_claim.calldata_builders import encode_claim_uint256
    from airdrop_claim.executor import execute_claim
    from airdrop_claim.models import ClaimSpec, ClaimStatus
    from airdrop_claim.pipeline import deploy_mock_distributor, forge_build, merge_routing_allowlist, wait_rpc
    from airdrop_claim.store import ClaimQueueStore

    ap = argparse.ArgumentParser(description="Deploy mock claimer on Celo Sepolia and run approval-gated claim tx")
    ap.add_argument("--chain-id", type=int, default=DEFAULT_CHAIN, help="Must match RPC (default Celo Sepolia)")
    ap.add_argument("--amount", type=int, default=42, help="claim(uint256) argument")
    ap.add_argument(
        "--min-balance-wei",
        type=int,
        default=MIN_BALANCE_WEI,
        help="Abort if wallet balance below this (wei)",
    )
    ap.add_argument(
        "--routing-out",
        default="",
        help="Write merged routing JSON here (default: external_commerce_data/airdrop_claim_routing.celo-sepolia-session.json)",
    )
    args = ap.parse_args()

    pk = os.getenv("AIRDROP_CLAIMANT_PRIVATE_KEY", "").strip()
    if not pk or "your_" in pk.lower():
        print(
            "Set AIRDROP_CLAIMANT_PRIVATE_KEY in .env to a funded Celo Sepolia test wallet.",
            file=sys.stderr,
        )
        return 2

    acct = Account.from_key(pk)
    addr = acct.address
    env_addr = os.getenv("AIRDROP_CLAIM_WALLET_ADDRESS", "").strip()
    if env_addr:
        if Web3.to_checksum_address(env_addr).lower() != addr.lower():
            print("AIRDROP_CLAIM_WALLET_ADDRESS does not match AIRDROP_CLAIMANT_PRIVATE_KEY", file=sys.stderr)
            return 2
    else:
        os.environ["AIRDROP_CLAIM_WALLET_ADDRESS"] = addr

    rpc = _resolve_celo_sepolia_rpc()
    if not rpc:
        print("Set CELO_SEPOLIA_RPC_URL (or PRIVATE_RPC_URL / RPC_URL) to a Celo Sepolia HTTP endpoint.", file=sys.stderr)
        return 2

    w3 = wait_rpc(rpc)
    chain_id = int(w3.eth.chain_id)
    if chain_id != args.chain_id:
        print(f"RPC chain_id={chain_id} but --chain-id={args.chain_id}. Fix RPC or flag.", file=sys.stderr)
        return 2

    bal = w3.eth.get_balance(addr)
    print(f"Claim wallet {addr} balance: {bal} wei")
    if bal < args.min_balance_wei:
        print(
            f"Balance below --min-balance-wei ({args.min_balance_wei}). Fund from https://faucet.celo.org/celo-sepolia",
            file=sys.stderr,
        )
        return 2

    forge_build(root)
    print("Deploying MockClaimDistributor...")
    deployed = deploy_mock_distributor(w3, pk, chain_id, ARTIFACT)
    print(f"Deployed at {deployed}")

    routing_out = Path(args.routing_out) if args.routing_out.strip() else (
        root / "external_commerce_data" / "airdrop_claim_routing.celo-sepolia-session.json"
    )
    routing_out.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_routing_allowlist(BASE_ROUTING, chain_id, deployed)
    routing_out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote session routing: {routing_out}")

    os.environ["CELO_SEPOLIA_RPC_URL"] = rpc
    os.environ["PRIVATE_RPC_URL"] = rpc
    os.environ["RPC_URL"] = rpc
    os.environ["AIRDROP_CLAIM_ROUTING_JSON"] = str(routing_out.resolve())
    os.environ["AIRDROP_CLAIM_QUEUE_DB"] = str((root / "external_commerce_data" / "airdrop_claim_testnet.sqlite").resolve())
    os.environ["AIRDROP_CLAIM_EXECUTION_ENABLED"] = "1"
    os.environ["AIRDROP_CLAIMANT_PRIVATE_KEY"] = pk

    data = encode_claim_uint256(args.amount)
    spec = ClaimSpec(
        chain_id=chain_id,
        to=deployed,
        data=data,
        value_wei=0,
        signer_role="AIRDROP_CLAIMANT",
        label="testnet MockClaimDistributor",
        source_url="contracts/MockClaimDistributor.sol",
        notes="run-airdrop-claim-testnet.py",
    )

    st = ClaimQueueStore()
    cid = st.add_pending(spec, meta={"network": "celo-sepolia", "demo": "testnet"})
    print(f"Queued claim id: {cid}")
    st.update_status(cid, ClaimStatus.approved, approved_by="testnet-script")
    print("Approved (auto). Executing on-chain...")

    out = execute_claim(cid, dry_run=False)
    print(json.dumps(out, indent=2))

    txh = out.get("tx_hash")
    if txh:
        rcpt = w3.eth.wait_for_transaction_receipt(txh)
        print(f"Receipt status: {rcpt.get('status')} (1=success)")
        ex = merged["routes"][str(chain_id)].get("explorer_url") or ""
        if ex:
            print(f"Explorer: {ex.rstrip('/')}/tx/{txh}")
        cs_addr = Web3.to_checksum_address(deployed)
        cs_wallet = Web3.to_checksum_address(addr)
        dist = w3.eth.contract(
            address=cs_addr,
            abi=json.loads(ARTIFACT.read_text(encoding="utf-8"))["abi"],
        )
        got = 0
        for _ in range(8):
            got = dist.functions.claimed(cs_wallet).call()
            if int(got) == int(args.amount):
                break
            time.sleep(0.35)
        print(f"claimed[{cs_wallet}] = {got} (expected {args.amount})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
