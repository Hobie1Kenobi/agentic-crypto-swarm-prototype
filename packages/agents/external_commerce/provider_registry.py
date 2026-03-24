"""
Provider registry — CRUD and normalization for external providers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import ExternalProvider


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_registry_path() -> Path:
    return _repo_root() / "external_commerce_data" / "providers.json"


def _normalize_provider(raw: dict[str, Any]) -> ExternalProvider:
    meta = dict(raw.get("metadata") or {})
    if raw.get("payment_flow"):
        meta["payment_flow"] = raw["payment_flow"]
    return ExternalProvider(
        provider_id=str(raw.get("provider_id", "")).strip() or raw.get("id", "unknown"),
        provider_name=str(raw.get("provider_name", raw.get("name", ""))).strip(),
        source_type=str(raw.get("source_type", "config")).strip() or "config",
        discovery_source=str(raw.get("discovery_source", "")).strip(),
        protocol_type=str(raw.get("protocol_type", "x402")).strip() or "x402",
        network=str(raw.get("network", "")).strip(),
        facilitator_url=raw.get("facilitator_url") or None,
        resource_url=str(raw.get("resource_url", raw.get("url", ""))).strip(),
        supported_assets=raw.get("supported_assets") or raw.get("assets") or [],
        pricing_model=str(raw.get("pricing_model", "")).strip(),
        categories=raw.get("categories") or raw.get("capabilities") or [],
        trust_score=float(raw.get("trust_score", 0)),
        health_status=str(raw.get("health_status", "unknown")).strip() or "unknown",
        last_seen_at=raw.get("last_seen_at"),
        metadata=meta,
    )


class ProviderRegistry:
    def __init__(self, registry_path: Path | None = None):
        self._path = registry_path or _default_registry_path()
        self._providers: dict[str, ExternalProvider] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for p in data.get("providers", []) if isinstance(data, dict) else data:
                    if isinstance(p, dict):
                        prov = _normalize_provider(p)
                        self._providers[prov.provider_id] = prov
            except Exception:
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "providers": [
                {
                    "provider_id": p.provider_id,
                    "provider_name": p.provider_name,
                    "source_type": p.source_type,
                    "resource_url": p.resource_url,
                    "network": p.network,
                    "facilitator_url": p.facilitator_url,
                    "trust_score": p.trust_score,
                    "health_status": p.health_status,
                }
                for p in self._providers.values()
            ]
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, provider: ExternalProvider | dict[str, Any]) -> ExternalProvider:
        if isinstance(provider, dict):
            provider = _normalize_provider(provider)
        self._providers[provider.provider_id] = provider
        return provider

    def get(self, provider_id: str) -> ExternalProvider | None:
        return self._providers.get(provider_id)

    def list_all(self) -> list[ExternalProvider]:
        return list(self._providers.values())

    def list_by_network(self, network: str) -> list[ExternalProvider]:
        return [p for p in self._providers.values() if p.network == network]

    def list_healthy(self, min_trust: float = 0) -> list[ExternalProvider]:
        return [
            p for p in self._providers.values()
            if p.health_status == "ok" and p.trust_score >= min_trust
        ]
