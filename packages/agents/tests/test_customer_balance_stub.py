from services.customer_balance_stub import credit_from_xrpl_receipt, pricing_catalog_lookup, budget_enforcement_check


def test_credit_from_xrpl_receipt():
    receipt = {"verified": True, "amount": "1", "payment_asset": "XRP", "tx_hash": "0x123"}
    credit = credit_from_xrpl_receipt(receipt, customer_id="cust1")
    assert credit is not None
    assert credit.customer_id == "cust1"
    assert credit.asset == "XRP"
    assert credit.source == "xrpl"
    assert credit.external_ref == "0x123"


def test_credit_from_xrpl_receipt_unverified():
    receipt = {"verified": False, "amount": "1"}
    assert credit_from_xrpl_receipt(receipt) is None


def test_credit_from_xrpl_receipt_empty():
    assert credit_from_xrpl_receipt(None) is None
    assert credit_from_xrpl_receipt({}) is None


def test_pricing_catalog_lookup():
    r = pricing_catalog_lookup("task_execution")
    assert r is not None
    assert r.get("asset") == "XRP"
    assert "amount" in r


def test_budget_enforcement_check():
    assert budget_enforcement_check("cust1", 1000) is True
