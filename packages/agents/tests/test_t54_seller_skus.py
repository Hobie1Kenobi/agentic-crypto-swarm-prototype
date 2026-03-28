"""T54 multi-SKU catalog and structured models."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

AGENTS = Path(__file__).resolve().parents[1]


def test_load_t54_seller_skus(monkeypatch):
    monkeypatch.setenv("T54_SELLER_SKUS_JSON", str(AGENTS / "config" / "t54_seller_skus.json"))
    from t54_seller_catalog import load_t54_seller_skus

    skus = load_t54_seller_skus()
    assert len(skus) >= 5
    paths = {s["path"] for s in skus}
    assert "/x402/v1/query" in paths
    assert "/x402/v1/research-brief" in paths


def test_models_json_schema():
    from t54_seller_models import StructuredQueryResponse

    s = StructuredQueryResponse.model_json_schema()
    assert "properties" in s
    assert "answer" in s["properties"]


def test_handlers_dry_run():
    os.environ.setdefault("LLM_DRY_RUN", "1")
    from t54_seller_handlers import run_agent_commerce_data, run_hello, run_structured_query

    h = run_hello("/hello")
    assert h.message == "paid"
    q = run_structured_query("test")
    assert "answer" in q.model_dump()
    bundle = run_agent_commerce_data("standard")
    d = bundle.model_dump()
    assert d["sku_id"] == "agent-commerce-data"
    assert "generated_at" in d
    assert isinstance(d.get("included_artifacts"), list)
    assert "celo_sepolia" in d
    assert isinstance(d.get("celo_sepolia"), dict)


def test_discovery_t54_base_from_legacy_url(monkeypatch):
    from external_commerce.discovery import _apply_env_overrides, _t54_public_base_url

    monkeypatch.delenv("T54_SELLER_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("T54_SELLER_PUBLIC_URL", "https://example.com/x402/v1/query")
    assert _t54_public_base_url() == "https://example.com"

    raw = {
        "provider_id": "t54-xrpl-research-brief",
        "metadata": {"t54_path": "/x402/v1/research-brief"},
        "resource_url": "",
    }
    out = _apply_env_overrides(raw)
    assert out["resource_url"] == "https://example.com/x402/v1/research-brief"


def test_discovery_portal_metadata_on_swarm_providers():
    from external_commerce.discovery import Discovery

    d = Discovery()
    providers = d.discover_from_config()
    by_id = {p.provider_id: p for p in providers}
    p = by_id.get("swarm-seller-facilitator")
    assert p is not None
    assert "portal_url" in (p.metadata or {})
    assert "github.io" in (p.metadata or {}).get("portal_url", "")


def test_discovery_swarm_seller_celo_data_url(monkeypatch):
    from external_commerce.discovery import _apply_env_overrides

    monkeypatch.delenv("X402_SELLER_DATA_PUBLIC_URL", raising=False)
    monkeypatch.setenv("X402_SELLER_PUBLIC_URL", "https://example.com/x402/v1/query")
    raw = {
        "provider_id": "swarm-seller-celo-data",
        "resource_url": "http://127.0.0.1:8043/x402/v1/celo-agent-data",
    }
    out = _apply_env_overrides(raw)
    assert out["resource_url"] == "https://example.com/x402/v1/celo-agent-data"

    monkeypatch.setenv("X402_SELLER_DATA_PUBLIC_URL", "https://override.example/celo-agent-data")
    out2 = _apply_env_overrides(raw)
    assert out2["resource_url"] == "https://override.example/celo-agent-data"
