from decimal import Decimal


def test_marketplace_config_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD", "29.50")
    monkeypatch.setenv("MARKETPLACE_ORDERS_DIR", str(tmp_path / "ord"))
    monkeypatch.setenv("MARKETPLACE_HTTP_ENABLED", "1")
    from integrations.marketplace.config import MarketplaceConfig

    c = MarketplaceConfig.from_env()
    assert c.dashboard_bundle_price_usd == Decimal("29.50")
    assert c.orders_dir == tmp_path / "ord"
    assert c.http_enabled is True


def test_write_pending_order(tmp_path):
    from integrations.marketplace.config import MarketplaceConfig
    from integrations.marketplace.orders import write_pending_order

    cfg = MarketplaceConfig(
        http_enabled=False,
        orders_dir=tmp_path,
        dashboard_bundle_price_usd=Decimal("49.00"),
        webhook_secret=None,
        bundle_zip_path=None,
        public_base_url="",
    )
    path, ref = write_pending_order(
        cfg,
        payment_intent_id="pi_test_123",
        amount_cents=4900,
        currency="usd",
        pay_to_address="0xabc",
        network="tempo",
        product_id="x402_strategy_dashboard_bundle",
    )
    assert path.name == "pending-pi_test_123.json"
    assert len(ref) == 36
    data = path.read_text(encoding="utf-8")
    assert "pi_test_123" in data
    assert ref in data


def test_create_crypto_deposit_includes_metadata(monkeypatch):
    import stripe

    captured: dict = {}

    class FakePI:
        id = "pi_meta_test"

    class FakePaymentIntents:
        @staticmethod
        def create(params):
            captured["params"] = params
            return FakePI()

    class FakeV1:
        payment_intents = FakePaymentIntents()

    class FakeStripeClient:
        def __init__(self, *a, **k):
            self.v1 = FakeV1()

    monkeypatch.setattr(stripe, "StripeClient", FakeStripeClient)
    from integrations.stripe_mpp import payment_intent as pi_mod

    monkeypatch.setattr(pi_mod, "extract_tempo_deposit_address", lambda _: "0xdeadbeef")

    d = pi_mod.create_crypto_deposit_payment_intent(
        amount_usd="1.00",
        secret_key="sk_test_xxx",
        metadata={"product_id": "x402_strategy_dashboard_bundle", "sku": "v1"},
    )
    assert d.pay_to_address == "0xdeadbeef"
    assert captured["params"]["metadata"]["product_id"] == "x402_strategy_dashboard_bundle"
    assert captured["params"]["metadata"]["sku"] == "v1"
