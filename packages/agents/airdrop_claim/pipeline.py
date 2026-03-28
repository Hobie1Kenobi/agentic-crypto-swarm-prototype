from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from eth_account import Account
from web3 import Web3


def wait_rpc(url: str, timeout: float = 45.0) -> Web3:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            w3 = Web3(Web3.HTTPProvider(url))
            if w3.is_connected():
                _ = w3.eth.block_number
                return w3
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"Could not connect to RPC within {timeout}s: {url}")


def forge_build(root: Path, contract_glob: str = "contracts/MockClaimDistributor.sol") -> None:
    r = subprocess.run(
        ["forge", "build", "--contracts", contract_glob],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise RuntimeError(f"forge build failed:\n{r.stderr or r.stdout}")


def deploy_mock_distributor(w3: Web3, pk: str, chain_id: int, artifact_path: Path) -> str:
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Missing {artifact_path}. Run forge build.")
    art = json.loads(artifact_path.read_text(encoding="utf-8"))
    abi = art["abi"]
    bytecode = art["bytecode"]["object"]
    if not bytecode or bytecode == "0x":
        raise RuntimeError("Empty bytecode in artifact; run forge build")
    acct = Account.from_key(pk)
    C = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = C.constructor().build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gasPrice": w3.eth.gas_price,
            "chainId": chain_id,
        }
    )
    tx["gas"] = w3.eth.estimate_gas(tx)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(h)
    addr = rcpt.get("contractAddress")
    if not addr:
        raise RuntimeError("Deploy failed: no contract address in receipt")
    return Web3.to_checksum_address(addr)


def merge_routing_allowlist(
    base_routes_path: Path,
    chain_id: int,
    deployed_contract: str,
) -> dict:
    from .routing import ChainRoute, RoutingConfig

    data = json.loads(base_routes_path.read_text(encoding="utf-8"))
    routes_raw = data.get("routes") or {}
    key = str(chain_id)
    if key not in routes_raw:
        raise RuntimeError(f"No route for chain_id {chain_id} in {base_routes_path}")
    route = ChainRoute.model_validate(routes_raw[key])
    dumped = route.model_dump()
    dumped["allowed_contracts"] = [Web3.to_checksum_address(deployed_contract)]
    return {"version": data.get("version", 1), "description": data.get("description", ""), "routes": {key: dumped}}
