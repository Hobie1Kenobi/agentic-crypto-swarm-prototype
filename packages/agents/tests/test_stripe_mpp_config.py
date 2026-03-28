def test_stripe_mpp_config_defaults(monkeypatch):
    monkeypatch.delenv("STRIPE_MPP_ENABLED", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_MPP_TESTNET", raising=False)
    monkeypatch.delenv("STRIPE_API_VERSION", raising=False)
    monkeypatch.delenv("STRIPE_PAYMENT_METHOD_CONFIGURATION", raising=False)

    from integrations.stripe_mpp.config import StripeMppConfig

    c = StripeMppConfig.from_env()
    assert c.enabled is False
    assert c.secret_key is None
    assert c.testnet is True
    assert c.api_version == "2026-03-04.preview"
    assert c.payment_method_configuration is None


def test_stripe_mpp_config_enabled(monkeypatch):
    monkeypatch.setenv("STRIPE_MPP_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_MPP_TESTNET", "0")
    monkeypatch.setenv("STRIPE_PAYMENT_METHOD_CONFIGURATION", "pmc_test_123")

    from integrations.stripe_mpp.config import StripeMppConfig

    c = StripeMppConfig.from_env()
    assert c.enabled is True
    assert c.secret_key == "sk_test_xxx"
    assert c.testnet is False
    assert c.payment_method_configuration == "pmc_test_123"


def test_create_crypto_deposit_rejects_below_minimum(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    from integrations.stripe_mpp.payment_intent import create_crypto_deposit_payment_intent

    try:
        create_crypto_deposit_payment_intent(
            amount_usd="0.10",
            secret_key="sk_test_xxx",
        )
    except ValueError as e:
        assert "0.50" in str(e) or "at least" in str(e).lower()
    else:
        raise AssertionError("expected ValueError")


def test_extract_tempo_deposit_address_from_dict():
    from integrations.stripe_mpp.payment_intent import extract_tempo_deposit_address

    fake_pi = {
        "id": "pi_123",
        "next_action": {
            "type": "crypto_display_details",
            "crypto_display_details": {
                "deposit_addresses": {
                    "tempo": {"address": "0xabc123"},
                }
            },
        },
    }
    assert extract_tempo_deposit_address(fake_pi) == "0xabc123"
