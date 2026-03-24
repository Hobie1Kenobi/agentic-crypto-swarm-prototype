"""
Provider relationship memory — persistent trust and performance state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import ProviderRelationship


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_path() -> Path:
    return _repo_root() / "external_commerce_data" / "provider_relationships.json"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RelationshipMemory:
    def __init__(self, path: Path | None = None):
        self._path = path or _default_path()
        self._relationships: dict[str, ProviderRelationship] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for k, v in (data.get("relationships", {}) or {}).items():
                    if isinstance(v, dict):
                        self._relationships[k] = ProviderRelationship(
                            provider_id=v.get("provider_id", k),
                            first_seen_at=v.get("first_seen_at", _ts()),
                            last_invoked_at=v.get("last_invoked_at", _ts()),
                            successful_calls=int(v.get("successful_calls", 0)),
                            failed_calls=int(v.get("failed_calls", 0)),
                            avg_latency_ms=float(v.get("avg_latency_ms", 0)),
                            avg_cost=v.get("avg_cost"),
                            last_price_seen=v.get("last_price_seen"),
                            quality_score=float(v.get("quality_score", 0)),
                            trust_score=float(v.get("trust_score", 0)),
                            preferred_for_task_types=v.get("preferred_for_task_types") or [],
                            cooldown_until=v.get("cooldown_until"),
                            blacklist_reason=v.get("blacklist_reason"),
                            notes=v.get("notes", ""),
                        )
            except Exception:
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "relationships": {
                pid: {
                    "provider_id": r.provider_id,
                    "first_seen_at": r.first_seen_at,
                    "last_invoked_at": r.last_invoked_at,
                    "successful_calls": r.successful_calls,
                    "failed_calls": r.failed_calls,
                    "avg_latency_ms": r.avg_latency_ms,
                    "avg_cost": r.avg_cost,
                    "last_price_seen": r.last_price_seen,
                    "quality_score": r.quality_score,
                    "trust_score": r.trust_score,
                    "preferred_for_task_types": r.preferred_for_task_types,
                    "cooldown_until": r.cooldown_until,
                    "blacklist_reason": r.blacklist_reason,
                    "notes": r.notes,
                }
                for pid, r in self._relationships.items()
            }
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get(self, provider_id: str) -> ProviderRelationship | None:
        return self._relationships.get(provider_id)

    def get_or_create(self, provider_id: str) -> ProviderRelationship:
        if provider_id in self._relationships:
            return self._relationships[provider_id]
        now = _ts()
        r = ProviderRelationship(
            provider_id=provider_id,
            first_seen_at=now,
            last_invoked_at=now,
            successful_calls=0,
            failed_calls=0,
            avg_latency_ms=0.0,
            avg_cost=None,
            last_price_seen=None,
            quality_score=0.0,
            trust_score=0.5,
        )
        self._relationships[provider_id] = r
        return r

    def record_success(
        self,
        provider_id: str,
        latency_ms: float,
        price_paid: str | None = None,
    ) -> None:
        r = self.get_or_create(provider_id)
        total = r.successful_calls + r.failed_calls
        new_total = total + 1
        new_avg = (r.avg_latency_ms * total + latency_ms) / new_total if new_total else latency_ms
        self._relationships[provider_id] = ProviderRelationship(
            provider_id=r.provider_id,
            first_seen_at=r.first_seen_at,
            last_invoked_at=_ts(),
            successful_calls=r.successful_calls + 1,
            failed_calls=r.failed_calls,
            avg_latency_ms=new_avg,
            avg_cost=price_paid or r.avg_cost,
            last_price_seen=price_paid or r.last_price_seen,
            quality_score=min(1.0, r.quality_score + 0.1),
            trust_score=min(1.0, r.trust_score + 0.05),
            preferred_for_task_types=r.preferred_for_task_types,
            cooldown_until=r.cooldown_until,
            blacklist_reason=r.blacklist_reason,
            notes=r.notes,
        )
        self.save()

    def record_failure(self, provider_id: str, reason: str | None = None) -> None:
        r = self.get_or_create(provider_id)
        self._relationships[provider_id] = ProviderRelationship(
            provider_id=r.provider_id,
            first_seen_at=r.first_seen_at,
            last_invoked_at=_ts(),
            successful_calls=r.successful_calls,
            failed_calls=r.failed_calls + 1,
            avg_latency_ms=r.avg_latency_ms,
            avg_cost=r.avg_cost,
            last_price_seen=r.last_price_seen,
            quality_score=max(0, r.quality_score - 0.2),
            trust_score=max(0, r.trust_score - 0.1),
            preferred_for_task_types=r.preferred_for_task_types,
            cooldown_until=r.cooldown_until,
            blacklist_reason=reason or r.blacklist_reason,
            notes=r.notes,
        )
        self.save()
