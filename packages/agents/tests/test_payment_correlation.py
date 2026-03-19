from services.payment_correlation import map_payment_to_task, PaymentTaskCorrelation


def test_map_payment_to_task():
    receipt = {
        "external_payment_id": "ext-1",
        "tx_hash": "0xabc",
        "payment_rail": "xrpl",
        "payment_asset": "XRP",
        "verified": True,
        "verification_boundary": "mock_xrpl_payment",
    }
    corr = map_payment_to_task(receipt, internal_task_id=42, celo_tx_hashes=[{"name": "createTask", "tx_hash": "0xcelo1"}])
    assert isinstance(corr, PaymentTaskCorrelation)
    assert corr.external_payment_id == "ext-1"
    assert corr.xrpl_tx_hash == "0xabc"
    assert corr.internal_task_id == 42
    assert len(corr.celo_tx_hashes) == 1
    assert corr.payment_rail == "xrpl"
    assert corr.verified is True


def test_map_payment_to_task_xrpl_tx_hash_alias():
    receipt = {"xrpl_tx_hash": "0xdef", "payment_rail": "xrpl", "verified": False}
    corr = map_payment_to_task(receipt, internal_task_id=None, celo_tx_hashes=[])
    assert corr.xrpl_tx_hash == "0xdef"
