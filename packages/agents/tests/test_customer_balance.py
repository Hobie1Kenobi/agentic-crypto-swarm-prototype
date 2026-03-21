from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    monkeypatch.setenv("CUSTOMER_BALANCE_DB_PATH", path)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


def test_credit_and_get_balance(temp_db):
    from services.customer_balance import credit, get_balance
    credit("cust1", 1000, "XRP", "xrpl", "tx1")
    assert get_balance("cust1") == 1000


def test_debit_success(temp_db):
    from services.customer_balance import credit, debit, get_balance
    credit("cust1", 1000)
    assert debit("cust1", 400) is True
    assert get_balance("cust1") == 600


def test_debit_insufficient(temp_db):
    from services.customer_balance import credit, debit, get_balance
    credit("cust1", 100)
    assert debit("cust1", 200) is False
    assert get_balance("cust1") == 100


def test_budget_enforcement_check(temp_db, monkeypatch):
    monkeypatch.setenv("CUSTOMER_BALANCE_ENABLED", "1")
    from services.customer_balance import credit, budget_enforcement_check
    credit("cust1", 5000)
    assert budget_enforcement_check("cust1", 3000) is True
    assert budget_enforcement_check("cust1", 6000) is False


def test_credit_from_xrpl_receipt_persists(temp_db, monkeypatch):
    monkeypatch.setenv("CUSTOMER_BALANCE_ENABLED", "1")
    monkeypatch.setenv("PRICING_XRP_TO_ETH", "0.01")
    from services.customer_balance import credit_from_xrpl_receipt, get_balance
    receipt = {"verified": True, "amount": "1", "payment_asset": "XRP", "tx_hash": "0xabc"}
    cred = credit_from_xrpl_receipt(receipt, customer_id="cust1")
    assert cred is not None
    assert get_balance("cust1") > 0
