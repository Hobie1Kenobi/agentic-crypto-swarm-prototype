"""
Task-to-provider routing policy.
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Any

from .schemas import ExternalProvider
from .relationship_memory import RelationshipMemory


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


class RoutingMode(str, Enum):
    INTERNAL_ONLY = "internal_only"
    EXTERNAL_ONLY = "external_only"
    HYBRID = "hybrid"
    FALLBACK_TO_EXTERNAL = "fallback_to_external"
    FALLBACK_TO_INTERNAL = "fallback_to_internal"
    MULTI_PROVIDER = "multi_provider"


class RoutingPolicy:
    def __init__(
        self,
        mode: str | None = None,
        min_trust_score: float = 0,
        relationship_memory: RelationshipMemory | None = None,
    ):
        self._mode = (mode or _env("EXTERNAL_MARKETPLACE_MODE", "internal_only")).strip().lower()
        self._min_trust = min_trust_score or float(_env("X402_MIN_TRUST_SCORE", "0"))
        self._relationships = relationship_memory or RelationshipMemory()

    def should_use_external(self, task_type: str = "", urgency: str = "") -> bool:
        if self._mode == RoutingMode.INTERNAL_ONLY.value:
            return False
        if self._mode == RoutingMode.EXTERNAL_ONLY.value:
            return True
        if self._mode == RoutingMode.HYBRID.value:
            return True
        if self._mode == RoutingMode.FALLBACK_TO_EXTERNAL.value:
            return False
        if self._mode == RoutingMode.FALLBACK_TO_INTERNAL.value:
            return True
        if self._mode == RoutingMode.MULTI_PROVIDER.value:
            return True
        return False

    def select_provider(
        self,
        providers: list[ExternalProvider],
        task_type: str = "",
        max_spend: str | None = None,
    ) -> ExternalProvider | None:
        if not providers:
            return None
        eligible = [p for p in providers if p.trust_score >= self._min_trust and p.health_status != "blacklist"]
        if not eligible:
            return providers[0] if providers else None
        rels = {p.provider_id: self._relationships.get(p.provider_id) for p in eligible}
        scored = []
        for p in eligible:
            r = rels.get(p.provider_id)
            score = p.trust_score
            if r:
                score = 0.5 * score + 0.5 * r.trust_score
            if task_type and r and task_type in r.preferred_for_task_types:
                score += 0.2
            scored.append((score, p))
        scored.sort(key=lambda x: -x[0])
        return scored[0][1] if scored else None
