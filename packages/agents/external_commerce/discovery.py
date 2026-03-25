"""
Discovery layer — find and normalize external x402 providers.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from .schemas import ExternalProvider
from .provider_registry import ProviderRegistry, _normalize_provider


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _agents_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _t54_public_base_url() -> str:
    base = _env("T54_SELLER_PUBLIC_BASE_URL").rstrip("/")
    if base:
        return base
    legacy = (
        _env("T54_SELLER_PUBLIC_URL")
        or _env("T54_X402_RESOURCE_URL")
        or _env("X402_T54_RESOURCE_URL")
        or _env("T54_SELLER_PROBE_URL")
    )
    if not legacy:
        return ""
    u = urlparse(legacy.strip())
    if u.scheme and u.netloc:
        return f"{u.scheme}://{u.netloc}".rstrip("/")
    return ""


DISCOVERY_URLS = [
    "https://x402-discovery-api.onrender.com/discover",
    "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources",
    "https://facilitator.payai.network/discovery/resources",
]


def _fetch_remote_discovery(timeout: float = 15) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for url in DISCOVERY_URLS:
        try:
            if "discover" in url:
                r = requests.get(url, params={"limit": 50}, timeout=timeout)
            else:
                r = requests.get(url, timeout=timeout)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict) and "results" in data:
                for item in data.get("results", []):
                    if isinstance(item, dict) and item.get("url"):
                        out.append({
                            "provider_id": item.get("id", item.get("url", ""))[:64],
                            "provider_name": item.get("name", item.get("url", ""))[:80],
                            "resource_url": item.get("url", ""),
                            "network": item.get("network", "eip155:84532"),
                            "facilitator_url": item.get("facilitator_url", "https://x402.org/facilitator"),
                            "payment_flow": "facilitator",
                            "source_type": "discovery",
                            "discovery_source": "remote",
                            "metadata": {"price_usd": item.get("price_usd"), "health_status": item.get("health_status")},
                        })
            elif isinstance(data, dict) and "items" in data:
                for item in data.get("items", []):
                    if isinstance(item, dict) and item.get("resource"):
                        acc = item.get("accepts", [])
                        net = acc[0].get("network", "eip155:84532") if acc else "eip155:84532"
                        out.append({
                            "provider_id": (item.get("resource", "") or "")[:64].replace("/", "_"),
                            "provider_name": (item.get("resource", "") or "")[:80],
                            "resource_url": item.get("resource", ""),
                            "network": net,
                            "facilitator_url": "https://x402.org/facilitator",
                            "payment_flow": "facilitator",
                            "source_type": "discovery",
                            "discovery_source": "bazaar",
                        })
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and (item.get("resource") or item.get("url")):
                        url_val = item.get("resource") or item.get("url", "")
                        out.append({
                            "provider_id": url_val[:64].replace("/", "_"),
                            "provider_name": url_val[:80],
                            "resource_url": url_val,
                            "network": "eip155:84532",
                            "facilitator_url": "https://x402.org/facilitator",
                            "payment_flow": "facilitator",
                            "source_type": "discovery",
                            "discovery_source": "remote",
                        })
        except Exception:
            continue
    return out


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    pid = str(raw.get("provider_id", "")).strip()
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    base = _t54_public_base_url()
    t54_path = meta.get("t54_path") if isinstance(meta, dict) else None
    if base and isinstance(t54_path, str) and t54_path.startswith("/"):
        out = dict(raw)
        out["resource_url"] = base + t54_path
        return out
    if pid == "swarm-seller-facilitator":
        url = _env("X402_SELLER_PUBLIC_URL") or _env("X402_SELLER_PROBE_URL")
        net = _env("X402_SELLER_NETWORK")
        fac = _env("X402_TEST_FACILITATOR_URL") or _env("X402_SELLER_FACILITATOR_URL")
        if url or net or fac:
            out = dict(raw)
            if url:
                out["resource_url"] = url.strip()
            if net:
                out["network"] = net
            if fac:
                out["facilitator_url"] = fac
            return out
    if pid == "t54-xrpl-example":
        url = (
            _env("T54_X402_RESOURCE_URL")
            or _env("X402_T54_RESOURCE_URL")
            or _env("T54_SELLER_PUBLIC_URL")
            or _env("T54_SELLER_PROBE_URL")
        )
        if url:
            out = dict(raw)
            out["resource_url"] = url.strip()
            return out
    return raw


def _load_config_providers() -> list[dict[str, Any]]:
    path_env = _env("X402_PROVIDERS_JSON")
    if path_env:
        p = Path(path_env)
        if p.is_absolute() and p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("providers", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        pr = _repo_root() / path_env
        if pr.exists():
            data = json.loads(pr.read_text(encoding="utf-8"))
            return data.get("providers", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    default = _agents_root() / "config" / "x402_providers.json"
    if default.exists():
        data = json.loads(default.read_text(encoding="utf-8"))
        return data.get("providers", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return []


def _default_direct_providers() -> list[dict[str, Any]]:
    facilitator = _env("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator")
    return [
        {
            "provider_id": "x402-test-echo",
            "provider_name": "x402.org Test Echo",
            "source_type": "config",
            "discovery_source": "default",
            "protocol_type": "x402",
            "network": "eip155:84532",
            "facilitator_url": facilitator,
            "resource_url": "https://x402.org/api/v1/echo",
            "supported_assets": ["USDC"],
            "pricing_model": "per_request",
            "categories": ["echo", "test"],
        },
    ]


class Discovery:
    def __init__(self, registry: ProviderRegistry | None = None):
        self._registry = registry or ProviderRegistry()

    def discover_from_config(self) -> list[ExternalProvider]:
        providers = _load_config_providers()
        if not providers:
            providers = _default_direct_providers()
        result = []
        for raw in providers:
            if isinstance(raw, dict):
                raw = _apply_env_overrides(raw)
                p = _normalize_provider(raw)
                self._registry.add(p)
                result.append(p)
        return result

    def discover_from_remote(self, merge: bool = True) -> list[ExternalProvider]:
        remote = _fetch_remote_discovery()
        result = []
        for raw in remote:
            if isinstance(raw, dict) and raw.get("resource_url"):
                p = _normalize_provider(raw)
                if merge:
                    self._registry.add(p)
                result.append(p)
        return result

    def discover_all(self, include_remote: bool = False) -> list[ExternalProvider]:
        discovered = self.discover_from_config()
        if include_remote and _env("X402_DISCOVERY_ENABLED", "0").strip().lower() in {"1", "true", "yes"}:
            self.discover_from_remote(merge=True)
        return list(self._registry.list_all()) if discovered else discovered

    def get_registry(self) -> ProviderRegistry:
        return self._registry
