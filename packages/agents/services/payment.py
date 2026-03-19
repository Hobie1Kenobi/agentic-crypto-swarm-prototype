from __future__ import annotations

MIN_PAYMENT_WEI = int(0.001 * 1e18)

REVENUE_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "resultMetadata", "type": "string"}],
        "name": "fulfillQuery",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    }
]


def get_min_payment_wei() -> int:
    import os
    val = os.getenv("PAYMENT_WEI", "").strip()
    if val.isdigit():
        return int(val)
    return MIN_PAYMENT_WEI


def verify_payment_tx(tx_hash: str, revenue_address: str, expected_metadata: str) -> bool:
    from web3 import Web3
    from config.chains import get_rpc
    w3 = Web3(Web3.HTTPProvider(get_rpc()))
    if not w3.is_connected():
        return False
    min_wei = get_min_payment_wei()
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if not tx or tx.get("to") is None:
            return False
        if w3.to_checksum_address(tx["to"]) != w3.to_checksum_address(revenue_address):
            return False
        if tx.get("value", 0) < min_wei:
            return False
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if not receipt or receipt.get("status") != 1:
            return False
        contract = w3.eth.contract(address=w3.to_checksum_address(revenue_address), abi=REVENUE_ABI)
        try:
            _, params = contract.decode_function_input(tx["input"])
            decoded_metadata = params.get("resultMetadata", "")
            if decoded_metadata.strip() != expected_metadata.strip():
                return False
        except Exception:
            return False
        return True
    except Exception:
        return False
