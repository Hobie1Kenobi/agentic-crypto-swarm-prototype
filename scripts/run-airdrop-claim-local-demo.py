#!/usr/bin/env python3
"""
Local end-to-end demo: Anvil → deploy MockClaimDistributor → queue → approve → execute.

Prerequisites:
  - Foundry on PATH (`forge`, `anvil`)
  - Or:     --spawn-anvil   (starts Anvil on 8546)

Does not use your mainnet keys: defaults to Anvil account #0 unless you set AIRDROP_CLAIMANT_PRIVATE_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
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

ANVIL_DEFAULT_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ARTIFACT = root / "out" / "MockClaimDistributor.sol" / "MockClaimDistributor.json"
SPAWN_ANVIL_PORT = 8546


def main() -> int:
    from airdrop_claim.calldata_builders import encode_claim_uint256
    from airdrop_claim.executor import execute_claim
    from airdrop_claim.models import ClaimSpec, ClaimStatus
    from airdrop_claim.pipeline import deploy_mock_distributor, forge_build, wait_rpc
    from airdrop_claim.store import ClaimQueueStore

    ap = argparse.ArgumentParser(description="Run airdrop claim pipeline on local Anvil")
    ap.add_argument(
        "--rpc",
        default="",
        help="Anvil HTTP RPC (default: http://127.0.0.1:8545, or :8546 if --spawn-anvil)",
    )
    ap.add_argument(
        "--private-key",
        default=os.getenv("AIRDROP_CLAIMANT_PRIVATE_KEY", ANVIL_DEFAULT_KEY),
        help="Defaults to Anvil account #0 (local only)",
    )
    ap.add_argument(
        "--spawn-anvil",
        action="store_true",
        help=f"Background anvil on :{SPAWN_ANVIL_PORT} (avoids colliding with a node on :8545)",
    )
    ap.add_argument("--amount", type=int, default=42, help="claim(uint256) argument (wei-style integer)")
    args = ap.parse_args()

    rpc_url = args.rpc.strip()
    if args.spawn_anvil:
        os.environ.pop("RPC_URL", None)
        rpc_url = f"http://127.0.0.1:{SPAWN_ANVIL_PORT}"
    elif not rpc_url:
        rpc_url = os.getenv("RPC_URL", "http://127.0.0.1:8545").strip() or "http://127.0.0.1:8545"

    anvil_proc: subprocess.Popen | None = None
    if args.spawn_anvil:
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        anvil_proc = subprocess.Popen(
            ["anvil", "--port", str(SPAWN_ANVIL_PORT)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        time.sleep(1.2)

    try:
        w3 = wait_rpc(rpc_url)
        chain_id = int(w3.eth.chain_id)
        if chain_id not in (31337, 1337) and not args.spawn_anvil:
            print(
                f"Warning: chain_id={chain_id} is not local Anvil (31337). Use real routing + keys only if intended.",
                file=sys.stderr,
            )

        forge_build(root)
        pk = args.private_key.strip()
        if "your_" in pk.lower():
            raise RuntimeError("Refusing placeholder private key; use Anvil default or set AIRDROP_CLAIMANT_PRIVATE_KEY")

        deployed = deploy_mock_distributor(w3, pk, chain_id, ARTIFACT)
        acct = Account.from_key(pk)
        print(f"Deployed MockClaimDistributor at {deployed}")
        print(f"Signer (claim wallet): {acct.address}")

        data = encode_claim_uint256(args.amount)
        spec = ClaimSpec(
            chain_id=chain_id,
            to=deployed,
            data=data,
            value_wei=0,
            signer_role="AIRDROP_CLAIMANT",
            label="local-demo MockClaimDistributor",
            source_url="contracts/MockClaimDistributor.sol",
            notes="run-airdrop-claim-local-demo.py",
        )

        routing_path = root / "external_commerce_data" / "airdrop_claim_routing.anvil-demo.json"
        routing_path.parent.mkdir(parents=True, exist_ok=True)
        routing_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "routes": {
                        str(chain_id): {
                            "rpc_env_vars": ["RPC_URL"],
                            "signer_role": "AIRDROP_CLAIMANT",
                            "allowed_contracts": [deployed],
                            "max_gas": 600000,
                            "max_value_wei": 0,
                        }
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        demo_db = root / "external_commerce_data" / "airdrop_claim_demo.sqlite"
        os.environ["RPC_URL"] = rpc_url
        os.environ["AIRDROP_CLAIM_ROUTING_JSON"] = str(routing_path)
        os.environ["AIRDROP_CLAIM_QUEUE_DB"] = str(demo_db)
        os.environ["AIRDROP_CLAIM_EXECUTION_ENABLED"] = "1"
        os.environ["AIRDROP_CLAIMANT_PRIVATE_KEY"] = pk

        st = ClaimQueueStore()
        cid = st.add_pending(spec, meta={"demo": "anvil"})
        print(f"Queued claim id: {cid}")
        st.update_status(cid, ClaimStatus.approved, approved_by="local-demo")
        print("Approved (auto). Executing on-chain...")

        out = execute_claim(cid, dry_run=False)
        txh = out.get("tx_hash")
        print(json.dumps(out, indent=2))
        if txh:
            rcpt = w3.eth.wait_for_transaction_receipt(txh)
            print(f"Receipt status: {rcpt.get('status')} (1=success)")
            dist = w3.eth.contract(
                address=deployed,
                abi=json.loads(ARTIFACT.read_text(encoding="utf-8"))["abi"],
            )
            bal = dist.functions.claimed(acct.address).call()
            print(f"Mock claimed[{acct.address}] = {bal} (expected {args.amount})")
        return 0
    finally:
        if anvil_proc is not None:
            anvil_proc.terminate()
            try:
                anvil_proc.wait(timeout=5)
            except Exception:
                anvil_proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
