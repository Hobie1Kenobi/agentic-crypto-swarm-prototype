"""
Load x402scout .well-known catalog exports into ExternalProvider-shaped dicts.

Uses a pre-built slim JSON (see scripts/build-x402scout-providers-slim.py) so runtime
does not parse the multi-MB full catalog unless you opt in.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _agents_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def default_slim_path() -> Path:
    p = _env("X402_SCOUT_SLIM_JSON")
    if p:
        pp = Path(p)
        if pp.is_absolute() and pp.exists():
            return pp
        rp = _repo_root() / p
        if rp.exists():
            return rp
    return _repo_root() / "external_commerce_data" / "x402scout-providers-slim.json"


def network_to_caip2(network: str | None) -> str:
    n = (network or "").strip().lower().replace("-", "_")
    if n in ("base", "base_mainnet"):
        return "eip155:8453"
    if n in ("base_sepolia", "basesepolia"):
        return "eip155:84532"
    if n in ("ethereum", "mainnet", "eth"):
        return "eip155:1"
    if n in ("celo", "celo_mainnet"):
        return "eip155:42220"
    if n in ("celo_sepolia", "celosepolia"):
        return "eip155:11142220"
    return "eip155:84532"


def _https_api_url(url: str) -> bool:
    u = (url or "").strip().lower()
    return u.startswith("https://")


def scout_service_to_provider_dict(svc: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(svc, dict):
        return None
    url = str(svc.get("url") or "").strip()
    if not _https_api_url(url):
        return None
    if svc.get("agent_callable") is False:
        return None
    sid = str(svc.get("id") or svc.get("service_id") or "").strip()
    if not sid:
        return None
    hid = hashlib.sha256(sid.encode("utf-8")).hexdigest()[:16]
    pid = f"scout-{hid}"
    trust = float(svc.get("trust_score") or 0)
    health = str(svc.get("health_status") or "unknown")
    fac = svc.get("recommended_facilitator") or "https://x402.org/facilitator"
    net = network_to_caip2(svc.get("network"))
    price = svc.get("price_usd")
    return {
        "provider_id": pid,
        "provider_name": str(svc.get("name") or url)[:200],
        "source_type": "discovery",
        "discovery_source": "x402scout_catalog",
        "protocol_type": "x402",
        "network": net,
        "facilitator_url": str(fac).strip() if fac else "https://x402.org/facilitator",
        "resource_url": url,
        "supported_assets": ["USDC"] if net.startswith("eip155:84") else [],
        "pricing_model": str(svc.get("pricing_model") or "per_request"),
        "categories": [str(svc.get("category") or "unknown")],
        "trust_score": trust,
        "health_status": health if health else "unknown",
        "metadata": {
            "scout_service_id": sid,
            "price_usd": price,
            "avg_latency_ms": svc.get("avg_latency_ms"),
            "facilitator_compatible": svc.get("facilitator_compatible"),
        },
    }


def load_slim_provider_dicts(
    path: Path | None = None,
) -> list[dict[str, Any]]:
    p = path or default_slim_path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = data.get("providers") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    return [x for x in rows if isinstance(x, dict) and x.get("resource_url")]


def iter_scout_providers_for_registry(
    path: Path | None = None,
) -> Iterator[dict[str, Any]]:
    for raw in load_slim_provider_dicts(path):
        yield raw
