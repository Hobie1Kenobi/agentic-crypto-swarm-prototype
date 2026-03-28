import os

import pytest


def test_xrpl_provider_quote_payment(monkeypatch):
    monkeypatch.setenv("XRPL_SETTLEMENT_ASSET", "XRP")
    monkeypatch.setenv("XRPL_RECEIVER_ADDRESS", "rReceiver123")
    from services.xrpl_payment_provider import XRPLPaymentProvider

    provider = XRPLPaymentProvider()
    quote = provider.quote_payment({"query": "test"})
    assert quote is not None
    assert quote.asset == "XRP"
    assert quote.receiver == "rReceiver123"
    assert quote.chain_or_ledger == "xrpl"


def test_create_mock_xrpl_receipt(monkeypatch):
    monkeypatch.setenv("XRPL_SETTLEMENT_ASSET", "RLUSD")
    from services.xrpl_payment_provider import create_mock_xrpl_receipt

    receipt = create_mock_xrpl_receipt({"query": "x"})
    assert receipt.payment_rail == "xrpl"
    assert receipt.payment_asset == "RLUSD"
    assert receipt.verified is False
    assert receipt.verification_boundary == "mock_xrpl_payment"
    assert receipt.tx_hash is not None
    assert receipt.external_payment_id is not None


def test_create_replay_xrpl_receipt():
    from services.xrpl_payment_provider import create_replay_xrpl_receipt

    replay = {
        "tx_hash": "0xabc123",
        "external_payment_id": "replay-1",
        "payer_address": "rPayer",
        "receiver_address": "rRecv",
        "amount": "10",
        "verified": True,
    }
    receipt = create_replay_xrpl_receipt(replay)
    assert receipt.payment_rail == "xrpl"
    assert receipt.tx_hash == "0xabc123"
    assert receipt.external_payment_id == "replay-1"
    assert receipt.verification_boundary == "replayed_xrpl_payment"


def test_get_xrpl_payment_receipt_mock(monkeypatch):
    monkeypatch.setenv("XRPL_PAYMENT_MODE", "mock")
    from services.xrpl_payment_provider import get_xrpl_payment_receipt

    receipt, boundary = get_xrpl_payment_receipt("mock", task_request={"query": "q"})
    assert receipt is not None
    assert boundary == "mock_xrpl_payment"
    assert receipt.verified is False


def test_get_xrpl_payment_receipt_replay(monkeypatch):
    monkeypatch.setenv("XRPL_PAYMENT_MODE", "replay")
    from services.xrpl_payment_provider import get_xrpl_payment_receipt

    replay = {"tx_hash": "replay_tx_1", "amount": "5", "verified": True}
    receipt, boundary = get_xrpl_payment_receipt("replay", replay_payload=replay)
    assert receipt is not None
    assert boundary == "replayed_xrpl_payment"
    assert receipt.tx_hash == "replay_tx_1"


def test_xrpl_provider_normalize_payment_result():
    from services.xrpl_payment_provider import XRPLPaymentProvider

    provider = XRPLPaymentProvider()
    raw = {
        "payment_rail": "xrpl",
        "payment_asset": "XRP",
        "tx_hash": "0x123",
        "verified": True,
        "verification_boundary": "mock",
    }
    receipt = provider.normalize_payment_result(raw)
    assert receipt is not None
    assert receipt.payment_rail == "xrpl"
    assert receipt.tx_hash == "0x123"
    assert receipt.verified is True


def test_xrpl_provider_normalize_none():
    from services.xrpl_payment_provider import XRPLPaymentProvider

    provider = XRPLPaymentProvider()
    assert provider.normalize_payment_result(None) is None
