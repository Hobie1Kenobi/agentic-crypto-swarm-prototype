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
    assert len(skus) >= 4
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
    from t54_seller_handlers import run_hello, run_structured_query

    h = run_hello("/hello")
    assert h.message == "paid"
    q = run_structured_query("test")
    assert "answer" in q.model_dump()


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
