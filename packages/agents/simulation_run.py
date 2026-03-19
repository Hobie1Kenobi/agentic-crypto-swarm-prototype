#!/usr/bin/env python3
"""
Phase 4: End-to-end simulation. 10 synthetic users pay 0.001 ETH each for an AI query.
Logs tx hashes and profit; optionally distributes 60% to beneficiary when threshold met.
"""
import os
import sys
import time
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

from config.chains import get_rpc as _get_rpc_config, get_chain_id as _get_chain_id_config
from services.payment import get_min_payment_wei, REVENUE_ABI

NUM_USERS = int(os.getenv("SIMULATION_NUM_USERS", "10"))
PAYMENT_ETH = 0.001
PROFIT_THRESHOLD_ETH = float(os.getenv("SIMULATION_PROFIT_THRESHOLD_ETH", "0.005"))
BENEFICIARY_SHARE_BPS = 6000


def get_rpc():
    return _get_rpc_config()


def generate_response_metadata(user_id: int) -> str:
    from swarm.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    CONSTITUTION = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation."
    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content=CONSTITUTION),
        HumanMessage(content=f"One-sentence ethical AI query response for simulated user {user_id} (pay-per-query service). Output only the sentence."),
    ])
    return resp.content.strip() or f"simulated_response_user_{user_id}"


def run_simulation():
    from web3 import Web3
    from services.agent_executor import get_default_executor

    rpc = get_rpc()
    revenue_addr = os.getenv("REVENUE_SERVICE_ADDRESS")
    payer_key = os.getenv("ROOT_STRATEGIST_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
    beneficiary = os.getenv("BENEFICIARY_ADDRESS")
    finance_addr = os.getenv("FINANCE_DISTRIBUTOR_ADDRESS")

    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        print("RPC not connected; running in dry-run (log only).")
        revenue_addr = None
        payer_key = None
    else:
        executor = get_default_executor(w3)

    log_lines = []
    tx_hashes = []
    total_paid = 0
    start = time.time()

    log_lines.append("=== Agentic Crypto Swarm — E2E Simulation ===")
    chain_id = _get_chain_id_config()
    log_lines.append(f"Chain ID: {chain_id} | RPC: {rpc[:50]}...")
    log_lines.append(f"Users: {NUM_USERS} x {PAYMENT_ETH} ETH = {NUM_USERS * PAYMENT_ETH} ETH total payment")
    log_lines.append(f"Profit threshold: {PROFIT_THRESHOLD_ETH} ETH")
    log_lines.append("")

    if not revenue_addr:
        log_lines.append("REVENUE_SERVICE_ADDRESS not set — simulating (no on-chain txs).")
        log_lines.append("Set REVENUE_SERVICE_ADDRESS and a funded PRIVATE_KEY or ROOT_STRATEGIST_PRIVATE_KEY for live run.")
        log_lines.append("")

    for i in range(NUM_USERS):
        metadata = generate_response_metadata(i + 1)
        log_lines.append(f"[User {i+1}/{NUM_USERS}] metadata: {metadata[:60]}...")

        if revenue_addr and payer_key:
            try:
                chain_id = _get_chain_id_config()
                from_addr = executor.get_sender_address("ROOT_STRATEGIST")
                min_payment_wei = get_min_payment_wei()
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(revenue_addr),
                    abi=REVENUE_ABI,
                )
                tx = contract.functions.fulfillQuery(metadata).build_transaction({
                    "from": from_addr,
                    "value": min_payment_wei,
                    "gas": 150_000,
                    "chainId": chain_id,
                    "nonce": w3.eth.get_transaction_count(from_addr),
                })
                tx["gas"] = w3.eth.estimate_gas(tx)
                kw = {"gas_price": tx["gasPrice"]} if "gasPrice" in tx else {}
                tx_hash = executor.send_transaction(
                    "ROOT_STRATEGIST",
                    to=tx["to"],
                    value=tx["value"],
                    data=tx["data"],
                    gas=tx["gas"],
                    nonce=tx["nonce"],
                    chain_id=chain_id,
                    **kw,
                )
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                tx_hashes.append(receipt["transactionHash"].hex())
                total_paid += PAYMENT_ETH
                log_lines.append(f"  tx: {receipt['transactionHash'].hex()}")
            except Exception as e:
                log_lines.append(f"  error: {e}")
        else:
            total_paid += PAYMENT_ETH
            log_lines.append("  (simulated)")

    protocol_fee_total = total_paid * 0.10
    distributable_total = total_paid * 0.50
    log_lines.append("")
    log_lines.append("--- Revenue summary ---")
    log_lines.append(f"Total paid: {total_paid} ETH")
    log_lines.append(f"Protocol fee (10%): {protocol_fee_total} ETH")
    log_lines.append(f"Distributable (50%): {distributable_total} ETH")
    log_lines.append(f"Tx hashes: {len(tx_hashes)}")

    if finance_addr and beneficiary:
        try:
            bal_wei = w3.eth.get_balance(Web3.to_checksum_address(finance_addr))
            bal_eth = bal_wei / 1e18
            threshold_wei = int(PROFIT_THRESHOLD_ETH * 1e18)
            log_lines.append(f"Finance distributor balance: {bal_eth:.6f} ETH")
            if bal_wei >= threshold_wei:
                to_beneficiary_wei = bal_wei * BENEFICIARY_SHARE_BPS // 10000
                to_reinvest_wei = bal_wei - to_beneficiary_wei
                log_lines.append(f"Threshold met. Would send 60% to beneficiary: {to_beneficiary_wei/1e18:.6f} ETH, 40% reinvest: {to_reinvest_wei/1e18:.6f} ETH")
                dist_key = os.getenv("FINANCE_DISTRIBUTOR_PRIVATE_KEY")
                if dist_key and to_beneficiary_wei > 0:
                    chain_id = _get_chain_id_config()
                    from_addr = executor.get_sender_address("FINANCE_DISTRIBUTOR")
                    tx = {"to": Web3.to_checksum_address(beneficiary), "value": to_beneficiary_wei, "gas": 21_000, "chainId": chain_id, "nonce": w3.eth.get_transaction_count(from_addr)}
                    tx["gas"] = w3.eth.estimate_gas(tx)
                    kw = {}
                    if chain_id == 31337:
                        kw["gas_price"] = w3.eth.gas_price
                    h = executor.send_transaction(
                        "FINANCE_DISTRIBUTOR",
                        to=tx["to"],
                        value=tx["value"],
                        gas=tx["gas"],
                        nonce=tx["nonce"],
                        chain_id=chain_id,
                        **kw,
                    )
                    w3.eth.wait_for_transaction_receipt(h)
                    log_lines.append(f"Distribution tx: {h}")
            else:
                log_lines.append(f"Below threshold {PROFIT_THRESHOLD_ETH} ETH; no distribution.")
        except Exception as e:
            log_lines.append(f"Distribution check error: {e}")

    elapsed = time.time() - start
    log_lines.append("")
    log_lines.append(f"Simulation finished in {elapsed:.1f}s")
    log_lines.append("=== End simulation ===")

    for line in log_lines:
        print(line)

    log_path = root / "simulation_log.txt"
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nLog saved to {log_path}")


if __name__ == "__main__":
    run_simulation()
