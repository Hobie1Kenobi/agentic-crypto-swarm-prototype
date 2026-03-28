def test_network_to_caip2_base():
    from external_commerce.x402scout_catalog import network_to_caip2

    assert network_to_caip2("base") == "eip155:8453"
    assert network_to_caip2("base-sepolia") == "eip155:84532"


def test_scout_service_to_provider_https():
    from external_commerce.x402scout_catalog import scout_service_to_provider_dict

    prov = scout_service_to_provider_dict(
        {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "name": "Test API",
            "url": "https://api.example.com/x402",
            "network": "base",
            "trust_score": 90,
            "health_status": "verified_up",
            "agent_callable": True,
            "recommended_facilitator": "https://x402.org/facilitator",
            "price_usd": 0.01,
        }
    )
    assert prov is not None
    assert prov["provider_id"].startswith("scout-")
    assert prov["resource_url"] == "https://api.example.com/x402"
    assert prov["trust_score"] == 90.0


def test_scout_service_skips_non_https():
    from external_commerce.x402scout_catalog import scout_service_to_provider_dict

    assert scout_service_to_provider_dict({"id": "x", "url": "http://insecure.com"}) is None


def test_load_slim_empty_when_missing(tmp_path):
    from external_commerce.x402scout_catalog import load_slim_provider_dicts

    assert load_slim_provider_dicts(tmp_path / "nope.json") == []


def test_discovery_discover_all_respects_scout_flag(monkeypatch, tmp_path):
    monkeypatch.delenv("X402_SCOUT_CATALOG_ENABLED", raising=False)
    monkeypatch.delenv("X402_DISCOVERY_ENABLED", raising=False)
    cfg = tmp_path / "prov.json"
    cfg.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("X402_PROVIDERS_JSON", str(cfg))
    from external_commerce.discovery import Discovery
    from external_commerce.provider_registry import ProviderRegistry

    reg = ProviderRegistry(registry_path=tmp_path / "reg.json")
    d = Discovery(registry=reg)
    out = d.discover_all(include_remote=False, include_scout_catalog=False)
    assert isinstance(out, list)
