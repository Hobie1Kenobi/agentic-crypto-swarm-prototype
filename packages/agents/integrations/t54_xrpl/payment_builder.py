"""
Build presigned XRPL Payment transactions for t54 x402.
Invoice binding via MemoData = HEX(UTF-8(invoiceId)).
"""
from __future__ import annotations

import os
from typing import Any

def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _xrpl_address_valid(addr: str) -> bool:
    return bool(addr and isinstance(addr, str) and len(addr) >= 25 and addr.startswith("r"))


def _rpc_url(network: str) -> str:
    if network == "mainnet":
        return _env("T54_XRPL_RPC_URL", _env("XRPL_RPC_URL", "https://xrplcluster.com"))
    return _env("T54_XRPL_TESTNET_RPC_URL", _env("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234"))


def build_presigned_xrpl_payment(
    *,
    wallet_seed: str,
    pay_to: str,
    amount_drops: str,
    invoice_id: str,
    source_tag: int = 804681468,
    destination_tag: int | None = None,
    network: str = "testnet",
) -> tuple[str | None, str | None]:
    """
    Build and sign XRPL Payment. Returns (signed_tx_blob_hex, error).
    """
    if not _xrpl_address_valid(pay_to):
        return None, "invalid_receiver_address"
    try:
        amount_int = int(amount_drops)
        if amount_int <= 0 or str(amount_int) != amount_drops:
            return None, "invalid_amount_not_drops"
    except (ValueError, TypeError):
        return None, "invalid_amount_not_drops"
    if not invoice_id:
        return None, "invoice_id_required"
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import Wallet
        from xrpl.models import Payment
        from xrpl.models.transactions import Memo
        from xrpl.transaction import autofill, sign
    except ImportError as e:
        return None, f"xrpl_py_not_installed:{e}"
    try:
        wallet = Wallet.from_seed(wallet_seed)
    except Exception as e:
        return None, f"invalid_wallet_seed:{e}"
    if not _xrpl_address_valid(wallet.classic_address):
        return None, "invalid_sender_address"
    memo_data_hex = invoice_id.encode("utf-8").hex()
    memo_format_hex = "text/plain".encode("utf-8").hex()
    memos = [Memo(memo_data=memo_data_hex, memo_format=memo_format_hex)]
    payment_kw: dict[str, Any] = {
        "account": wallet.classic_address,
        "amount": amount_drops,
        "destination": pay_to,
        "memos": memos,
        "source_tag": source_tag,
    }
    if destination_tag is not None:
        payment_kw["destination_tag"] = destination_tag
    payment = Payment(**payment_kw)
    rpc = _rpc_url(network)
    try:
        client = JsonRpcClient(rpc)
        payment = autofill(payment, client)
    except Exception as e:
        return None, f"autofill_failed:{e}"
    try:
        signed = sign(payment, wallet)
    except Exception as e:
        return None, f"sign_failed:{e}"
    blob = getattr(signed, "blob", None)
    if not blob:
        return None, "signed_blob_unavailable"
    return str(blob), None
