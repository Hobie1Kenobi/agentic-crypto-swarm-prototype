import os
import pytest


def test_min_payment_wei_constant():
    from services.payment import MIN_PAYMENT_WEI
    assert MIN_PAYMENT_WEI == int(0.001 * 1e18)


def test_get_min_payment_wei_default(monkeypatch):
    monkeypatch.delenv("PAYMENT_WEI", raising=False)
    from services.payment import get_min_payment_wei
    assert get_min_payment_wei() == int(0.001 * 1e18)


def test_get_min_payment_wei_override(monkeypatch):
    monkeypatch.setenv("PAYMENT_WEI", "2000000000000000")
    import importlib
    import services.payment as payment_mod
    importlib.reload(payment_mod)
    assert payment_mod.get_min_payment_wei() == 2000000000000000


def test_revenue_abi_has_fulfill_query():
    from services.payment import REVENUE_ABI
    assert len(REVENUE_ABI) >= 1
    fn = REVENUE_ABI[0]
    assert fn.get("name") == "fulfillQuery"
    assert fn.get("stateMutability") == "payable"
    assert "inputs" in fn and len(fn["inputs"]) == 1
    assert fn["inputs"][0].get("name") == "resultMetadata"


def test_verify_payment_tx_invalid_hash(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "11142220")
    monkeypatch.setenv("RPC_URL", "https://rpc.ankr.com/celo_sepolia")
    from services.payment import verify_payment_tx
    result = verify_payment_tx("0x0000000000000000000000000000000000000000000000000000000000000000", "0x0000000000000000000000000000000000000001", "x")
    assert result is False


def test_verify_payment_tx_bad_address_format(monkeypatch):
    from services.payment import verify_payment_tx
    result = verify_payment_tx("0x" + "1" * 64, "not-an-address", "meta")
    assert result is False
