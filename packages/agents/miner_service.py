#!/usr/bin/env python3
"""
Compute marketplace miner: register on-chain, run HTTP server that accepts tasks and returns LLM responses.
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


def register_miner(metadata: str) -> bool:
    from web3 import Web3
    from config.chains import get_chain_id
    from services.agent_executor import get_default_executor

    addr = os.getenv("COMPUTE_MARKETPLACE_ADDRESS")
    key = os.getenv("ROOT_STRATEGIST_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    if not addr or not key:
        return False
    w3 = Web3(Web3.HTTPProvider(get_rpc()))
    if not w3.is_connected():
        return False
    chain_id = get_chain_id()
    executor = get_default_executor(w3, chain_id)
    from_addr = executor.get_sender_address("ROOT_STRATEGIST")
    abi = [{"inputs":[{"internalType":"string","name":"metadata","type":"string"}],"name":"registerAsMiner","outputs":[],"stateMutability":"nonpayable","type":"function"}]
    contract = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)
    tx = contract.functions.registerAsMiner(metadata).build_transaction({
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
    return True


def task_handler(query: str) -> str:
    from swarm.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    CONSTITUTION = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation."
    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content=CONSTITUTION),
        HumanMessage(content=f"Answer in one or two sentences. Query: {query}. Output only the answer."),
    ])
    return resp.content.strip() or "No response."


def create_app():
    from fastapi import FastAPI, HTTPException

    app = FastAPI(title="Compute Marketplace Miner", version="0.1.0")

    @app.post("/task")
    async def task(body: dict):
        q = body.get("query") or body.get("q") or ""
        if not q.strip():
            raise HTTPException(status_code=400, detail="Missing query")
        response = task_handler(q)
        return {"query": q, "response": response}

    @app.get("/health")
    async def health():
        return {"status": "ok", "role": "miner"}
    return app


def main():
    import uvicorn
    metadata = os.getenv("COMPUTE_MINER_METADATA", "swarm-agent-1")
    marketplace = os.getenv("COMPUTE_MARKETPLACE_ADDRESS")
    if marketplace:
        if register_miner(metadata):
            print(f"Registered as miner: {metadata}")
        else:
            print("Warning: could not register on-chain (check COMPUTE_MARKETPLACE_ADDRESS and RPC)")
    host = os.getenv("COMPUTE_MINER_HOST", "127.0.0.1")
    port = int(os.getenv("COMPUTE_MINER_PORT", "8043"))
    print(f"Miner listening on http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
