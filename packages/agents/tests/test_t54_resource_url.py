"""402 resource URLs must carry the public /t54 prefix that Caddy strips before the app."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from t54_seller_app import DEFAULT_T54_PUBLIC_BASE_URL, t54_resource_url


def test_default_resource_url_keeps_t54_prefix(monkeypatch):
    monkeypatch.delenv("T54_SELLER_PUBLIC_BASE_URL", raising=False)
    assert t54_resource_url("/hello") == f"{DEFAULT_T54_PUBLIC_BASE_URL}/hello"
    assert t54_resource_url("/hello") == "https://api.agentic-swarm-marketplace.com/t54/hello"


def test_env_base_url_trailing_slash(monkeypatch):
    monkeypatch.setenv("T54_SELLER_PUBLIC_BASE_URL", "https://example.test/t54/")
    assert t54_resource_url("/x402/v1/query") == "https://example.test/t54/x402/v1/query"
