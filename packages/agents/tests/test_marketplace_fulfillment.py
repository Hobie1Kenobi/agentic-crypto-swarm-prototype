from decimal import Decimal

from integrations.marketplace.config import MarketplaceConfig
from integrations.marketplace.fulfillment import finalize_pending_order, load_fulfilled
from integrations.marketplace.orders import write_pending_order


def test_finalize_moves_pending_to_fulfilled(tmp_path):
    cfg = MarketplaceConfig(
        http_enabled=True,
        orders_dir=tmp_path,
        dashboard_bundle_price_usd=Decimal("49.00"),
        webhook_secret="whsec_test",
        bundle_zip_path=None,
        public_base_url="",
    )
    write_pending_order(
        cfg,
        payment_intent_id="pi_fulfill_1",
        amount_cents=4900,
        currency="usd",
        pay_to_address="0x1",
        network="tempo",
        product_id="x402_strategy_dashboard_bundle",
    )
    out = finalize_pending_order(cfg, "pi_fulfill_1")
    assert out is not None
    assert out["status"] == "fulfilled"
    assert "download_token" in out
    assert not (tmp_path / "pending-pi_fulfill_1.json").exists()
    assert (tmp_path / "fulfilled-pi_fulfill_1.json").exists()
    same = load_fulfilled(cfg, "pi_fulfill_1")
    assert same and same["download_token"] == out["download_token"]


def test_finalize_idempotent_second_call(tmp_path):
    cfg = MarketplaceConfig(
        http_enabled=True,
        orders_dir=tmp_path,
        dashboard_bundle_price_usd=Decimal("49.00"),
        webhook_secret=None,
        bundle_zip_path=None,
        public_base_url="",
    )
    write_pending_order(
        cfg,
        payment_intent_id="pi_fulfill_2",
        amount_cents=100,
        currency="usd",
        pay_to_address="0x1",
        network="tempo",
        product_id="x402_strategy_dashboard_bundle",
    )
    a = finalize_pending_order(cfg, "pi_fulfill_2")
    b = finalize_pending_order(cfg, "pi_fulfill_2")
    assert a is not None and b is not None
    assert a["download_token"] == b["download_token"]
