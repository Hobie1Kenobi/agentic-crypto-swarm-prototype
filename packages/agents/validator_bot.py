#!/usr/bin/env python3
"""
Compute marketplace validator: register on-chain, fetch miners, POST task to each, score responses, submitScores.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env", override=True)

def _should_load_env_local() -> bool:
    chain_id = os.getenv("CHAIN_ID", "").strip()
    rpc = os.getenv("RPC_URL", "").strip().lower()
    if os.getenv("USE_ENV_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if chain_id == "31337":
        return True
    if rpc.startswith("http://127.0.0.1") or rpc.startswith("http://localhost") or "localhost" in rpc:
        return True
    return False

if _should_load_env_local() and (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)
sys.path.insert(0, str(root / "packages" / "agents"))


def get_rpc() -> str:
    from config.chains import get_rpc as _cfg_rpc
    return _cfg_rpc()


def run_round():
    from web3 import Web3
    import urllib.request
    import json
    from config.chains import get_chain_id
    from services.agent_executor import get_default_executor

    addr = os.getenv("COMPUTE_MARKETPLACE_ADDRESS")
    key = os.getenv("ROOT_STRATEGIST_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    miner_urls = os.getenv("COMPUTE_MINER_URLS", "http://127.0.0.1:8043").strip().split(",")
    if not addr or not key:
        print("Set COMPUTE_MARKETPLACE_ADDRESS and PRIVATE_KEY (or ROOT_STRATEGIST_PRIVATE_KEY)")
        return
    w3 = Web3(Web3.HTTPProvider(get_rpc()))
    if not w3.is_connected():
        print("RPC not connected")
        return

    chain_id = get_chain_id()
    executor = get_default_executor(w3, chain_id)
    from_addr = executor.get_sender_address("ROOT_STRATEGIST")

    abi = [
        {
            "inputs":[{"internalType":"address","name":"validator","type":"address"},{"internalType":"bool","name":"allowed","type":"bool"}],
            "name":"setValidatorAllowlist",
            "outputs":[],
            "stateMutability":"nonpayable",
            "type":"function"
        },
        {"inputs":[],"name":"getMiners","outputs":[{"internalType":"address[]","name":"addrs","type":"address[]"},{"internalType":"string[]","name":"metadatas","type":"string[]"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"address[]","name":"minerAddresses","type":"address[]"},{"internalType":"uint256[]","name":"newScores","type":"uint256[]"}],"name":"submitScores","outputs":[],"stateMutability":"nonpayable","type":"function"},
    ]
    contract = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
    tx = contract.functions.setValidatorAllowlist(from_addr, True).build_transaction({
        "from": from_addr,
        "chainId": chain_id,
        "nonce": w3.eth.get_transaction_count(from_addr),
    })
    tx["gas"] = w3.eth.estimate_gas(tx)
    kw = {"gas_price": tx["gasPrice"]} if "gasPrice" in tx else {}
    executor.send_transaction(
        "ROOT_STRATEGIST",
        to=tx["to"],
        value=tx.get("value", 0),
        data=tx["data"],
        gas=tx["gas"],
        nonce=tx["nonce"],
        chain_id=chain_id,
        **kw,
    )
    print("Registered as validator")

    addrs, metadatas = contract.functions.getMiners().call()
    if not addrs:
        print("No miners registered. Start miner_service.py first.")
        return
    print(f"Miners: {len(addrs)}")

    task_query = os.getenv("COMPUTE_TASK_QUERY", "What is one ethical use of AI?")
    miner_scores = []
    miner_addresses = []
    for i, url in enumerate(miner_urls):
        url = url.strip()
        if i >= len(addrs):
            break
        try:
            req = urllib.request.Request(
                f"{url.rstrip('/')}/task",
                data=json.dumps({"query": task_query}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
                resp = data.get("response", "")
                score = min(100, max(0, len(resp) + (10 if "ethical" in resp.lower() else 0)))
                miner_scores.append((addrs[i], score))
                miner_addresses.append(addrs[i])
                print(f"  {addrs[i][:10]}... -> score {score}")
        except Exception as e:
            print(f"  {addrs[i][:10]}... -> error: {e}")
            miner_scores.append((addrs[i], 1))
            miner_addresses.append(addrs[i])

    if not miner_addresses:
        print("No responses to score")
        return
    addrs_out = list(miner_addresses)
    scores_out = [s for _, s in miner_scores]
    tx = contract.functions.submitScores(addrs_out, scores_out).build_transaction({
        "from": from_addr,
        "chainId": chain_id,
        "nonce": w3.eth.get_transaction_count(from_addr),
    })
    tx["gas"] = w3.eth.estimate_gas(tx)
    kw = {"gas_price": tx["gasPrice"]} if "gasPrice" in tx else {}
    h = executor.send_transaction(
        "ROOT_STRATEGIST",
        to=tx["to"],
        value=tx.get("value", 0),
        data=tx["data"],
        gas=tx["gas"],
        nonce=tx["nonce"],
        chain_id=chain_id,
        **kw,
    )
    w3.eth.wait_for_transaction_receipt(h)
    print(f"Submitted scores. Tx: {h}")


def main():
    run_round()


if __name__ == "__main__":
    main()
