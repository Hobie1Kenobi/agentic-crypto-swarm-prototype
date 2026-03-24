"""
Celo-native 402 buyer — pays via fulfillQuery on AgentRevenueService.
Uses ROOT_STRATEGIST_PRIVATE_KEY from .env.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


CELO_SEPOLIA_CHAIN_ID = 11142220


def _get_celo_key() -> str:
    return _env("ROOT_STRATEGIST_PRIVATE_KEY", _env("DEPLOYER_PRIVATE_KEY", _env("PRIVATE_KEY", "")))


def invoke_celo_native_402(
    resource_url: str,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    method: str = "GET",
    timeout: float = 60,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """
    Call Celo-native 402 API (api_402 style). On 402, pay via fulfillQuery, retry with X-Payment-Tx-Hash.
    Returns (status_code, response_json, error).
    """
    session = requests.Session()
    start = time.time()
    try:
        if method.upper() == "GET":
            r = session.get(resource_url, params=params or {}, timeout=timeout)
        else:
            r = session.post(resource_url, json=json_body or {}, timeout=timeout)
        if r.status_code != 402:
            data = r.json() if "application/json" in (r.headers.get("content-type") or "") else {"raw": r.text[:500]}
            return r.status_code, data, None
        body = r.json() if r.content else {}
        payment = body.get("payment") or {}
        contract = payment.get("contract") or body.get("X-Payment-Contract")
        amount_wei = payment.get("amount_wei") or body.get("X-Payment-Amount-Wei")
        metadata = payment.get("result_metadata") or body.get("X-Payment-Metadata") or "x402:query"
        chain_id = int(payment.get("chain_id") or body.get("X-Payment-Chain-Id") or CELO_SEPOLIA_CHAIN_ID)
        if chain_id != CELO_SEPOLIA_CHAIN_ID:
            return 402, None, f"unsupported_chain:{chain_id}_we_use_celo_sepolia"
        pk = _get_celo_key()
        if not pk or "0x" not in pk:
            return 402, None, "no_celo_key_set"
        wei = int(amount_wei) if amount_wei else 1_000_000_000_000_000
        tx_hash = _pay_fulfill_query(contract, metadata, wei, pk, chain_id)
        if not tx_hash:
            return 402, None, "payment_tx_failed"
        headers = {"X-Payment-Tx-Hash": tx_hash}
        if method.upper() == "GET":
            r2 = session.get(resource_url, params=params or {}, headers=headers, timeout=timeout)
        else:
            r2 = session.post(resource_url, json=json_body or {}, headers=headers, timeout=timeout)
        data = r2.json() if "application/json" in (r2.headers.get("content-type") or "") else {"raw": r2.text[:500]}
        return r2.status_code, data, None
    except requests.RequestException as e:
        return 0, None, str(e)
    except Exception as e:
        return 0, None, str(e)


def _pay_fulfill_query(contract_addr: str, metadata: str, value_wei: int, private_key: str, chain_id: int) -> str | None:
    try:
        from web3 import Web3
        from config.chains import get_rpc
        from services.agent_executor import get_default_executor
        from services.payment import REVENUE_ABI
    except ImportError:
        return None
    rpc = get_rpc()
    if not rpc:
        return None
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        return None
    executor = get_default_executor(w3, chain_id)
    c = w3.eth.contract(address=Web3.to_checksum_address(contract_addr), abi=REVENUE_ABI)
    from_addr = executor.get_sender_address("ROOT_STRATEGIST")
    gas_bump = 1.0
    for attempt in range(4):
        nonce = w3.eth.get_transaction_count(from_addr, "pending")
        gas_price = int((w3.eth.gas_price or 1_000_000_000) * gas_bump)
        tx = c.functions.fulfillQuery(metadata).build_transaction({
            "from": from_addr,
            "value": value_wei,
            "chainId": chain_id,
            "nonce": nonce,
            "gasPrice": gas_price,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)
        try:
            h = executor.send_transaction(
                "ROOT_STRATEGIST",
                to=tx["to"],
                value=tx["value"],
                data=tx["data"],
                gas=tx["gas"],
                nonce=tx["nonce"],
                chain_id=chain_id,
                gas_price=gas_price,
            )
            receipt = w3.eth.wait_for_transaction_receipt(h, timeout=60)
            return receipt["transactionHash"].hex()
        except Exception as e:
            err = str(e).lower()
            if "nonce" in err or "underpriced" in err or "replacement" in err:
                gas_bump = min(gas_bump * 1.15, 2.0)
                time.sleep(2 * (attempt + 1))
                continue
            return None
    return None
