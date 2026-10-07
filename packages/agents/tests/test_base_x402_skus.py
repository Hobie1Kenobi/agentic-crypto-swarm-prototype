from __future__ import annotations

from config.base_x402_skus import (
    load_base_x402_skus,
    recommended_next_actions_for,
)
from well_known_discovery import build_x402_manifest


def test_base_sku_catalog_covers_live_routes():
    skus = load_base_x402_skus()
    paths = {s.route_key for s in skus}
    expected = {
        "GET /x402/v1/query",
        "GET /x402/v1/research-brief",
        "GET /x402/v1/constitution-audit",
        "GET /x402/v1/agent-commerce-data",
        "GET /x402/v1/ecosystem-pulse",
        "GET /x402/v1/airdrop-intelligence",
        "GET /x402/v1/contract-triage",
        "GET /x402/v1/contract-audit",
        "POST /x402/v1/contract-monitor",
        "GET /x402/v1/celo-agent-data",
        "GET /x402/v1/intake-resale",
        "GET /x402/v1/commerce/product-search",
        "GET /x402/v1/commerce/product-evidence",
        "GET /x402/v1/commerce/supplier-trust",
        "GET /x402/v1/commerce/compatibility-check",
        "GET /x402/v1/commerce/quote-comparison",
        "GET /x402/v1/commerce/compliance-check",
        "GET /x402/v1/commerce/purchase-readiness",
        "POST /x402/v1/procurement-readiness",
        "POST /x402/v1/specification-normalizer",
        "POST /x402/v1/quote-completeness-audit",
        "POST /x402/v1/rfp-requirement-extractor",
        "POST /x402/v1/bid-fit-score",
        "POST /x402/v1/bom-risk-audit",
        "POST /x402/v1/purchase-readiness-package",
    }
    assert expected <= paths
    assert len(skus) == 25


def test_manifest_includes_all_base_skus_and_schemas():
    pay_to = "0x408f39B19266022FeC03076091e59D1f4f163658"
    manifest = build_x402_manifest(pay_to)
    resources = [r for r in manifest["resources"] if str(r["path"]).startswith("/x402/")]
    assert len(resources) == 25
    assert manifest["seller"]["payTo"] == pay_to
    assert "cdp.coinbase.com" in manifest["seller"]["facilitator"]
    auth = manifest["seller"]["paymentAuthorization"]
    assert auth["table"] == "who_authorized_pay"
    assert auth["known_principals"]["operator_ignition_eoa"].startswith("0xEBd956")
    for r in resources:
        assert r.get("input_schema")
        assert r.get("output_schema")
        assert r.get("example_response")
        assert r.get("sku_id")
        assert r.get("description")


def test_recommendation_links_resolve():
    by_id = {s.id: s for s in load_base_x402_skus()}
    for action in recommended_next_actions_for("ecosystem-pulse"):
        target = by_id[action["sku"]]
        assert action["resource"].endswith(target.path)
        assert action["price_usd"] == target.price_usd
        assert action["when_to_use"]


def test_sku_by_path_maps_head_and_get_on_post_skus():
    from config.base_x402_skus import sku_by_path

    q = sku_by_path("/x402/v1/query", "GET")
    assert q is not None and q.id == "structured-query"
    assert sku_by_path("/x402/v1/query", "HEAD").id == "structured-query"
    lcg = sku_by_path("/x402/v1/procurement-readiness", "POST")
    assert lcg is not None and lcg.id == "procurement-readiness"
    assert sku_by_path("/x402/v1/procurement-readiness", "GET").id == "procurement-readiness"
    assert sku_by_path("/x402/v1/procurement-readiness", "HEAD").id == "procurement-readiness"


def test_manifest_advertises_accepted_methods():
    resources = build_x402_manifest("0x408f39B19266022FeC03076091e59D1f4f163658")["resources"]
    by_id = {r["sku_id"]: r for r in resources if r.get("sku_id")}
    assert by_id["structured-query"]["accepted_methods"] == ["GET", "HEAD"]
    assert "GET" in by_id["procurement-readiness"]["accepted_methods"]
    assert "POST" in by_id["procurement-readiness"]["accepted_methods"]


def test_pulse_recommendations_point_to_higher_value():
    actions = recommended_next_actions_for("ecosystem-pulse")
    assert {a["sku"] for a in actions} >= {"agent-commerce-data", "contract-triage"}


def test_base_sku_prices_are_unique(monkeypatch):
    import os

    for key in list(os.environ):
        if key.startswith("X402_") and "PRICE" in key:
            monkeypatch.delenv(key, raising=False)
    skus = load_base_x402_skus()
    prices = [round(s.price_usd, 6) for s in skus]
    assert len(prices) == len(set(prices)), prices
    by_id = {s.id: s.price_usd for s in skus}
    assert by_id["structured-query"] == 0.012
    assert by_id["agent-commerce-data"] == 0.07
    assert by_id["structured-query"] != by_id["contract-triage"]
