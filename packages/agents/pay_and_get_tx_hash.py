#!/usr/bin/env python3
"""Send one fulfillQuery(metadata) tx and print the tx hash for X-Payment-Tx-Hash."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
root = Path(__file__).resolve().parents[2]
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
from config.chains import get_rpc as _get_rpc_config, get_chain_id as _get_chain_id_config
from services.agent_executor import get_default_executor
from services.payment import get_min_payment_wei, REVENUE_ABI

metadata = sys.argv[1] if len(sys.argv) > 1 else "x402:test"
from web3 import Web3

w3 = Web3(Web3.HTTPProvider(_get_rpc_config()))
chain_id = _get_chain_id_config()
executor = get_default_executor(w3, chain_id)
from_addr = executor.get_sender_address("ROOT_STRATEGIST")
c = w3.eth.contract(address=Web3.to_checksum_address(os.getenv("REVENUE_SERVICE_ADDRESS")), abi=REVENUE_ABI)
tx = c.functions.fulfillQuery(metadata).build_transaction({
    "from": from_addr, "value": get_min_payment_wei(),
    "chainId": chain_id,
    "nonce": w3.eth.get_transaction_count(from_addr),
})
tx["gas"] = w3.eth.estimate_gas(tx)
kw = {"gas_price": tx["gasPrice"]} if "gasPrice" in tx else {}
h = executor.send_transaction(
    "ROOT_STRATEGIST",
    to=tx["to"],
    value=tx["value"],
    data=tx["data"],
    gas=tx["gas"],
    nonce=tx["nonce"],
    chain_id=chain_id,
    **kw,
)
receipt = w3.eth.wait_for_transaction_receipt(h)
print(receipt["transactionHash"].hex())
