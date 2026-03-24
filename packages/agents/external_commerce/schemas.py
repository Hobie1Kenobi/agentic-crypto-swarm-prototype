"""
Normalized schemas for external commerce.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from datetime import datetime, timezone


@dataclass
class ExternalProvider:
    provider_id: str
    provider_name: str
    source_type: str  # config, discovery, manual
    discovery_source: str
    protocol_type: str  # x402
    network: str  # CAIP-2 or chain name
    facilitator_url: str | None
    resource_url: str
    supported_assets: list[str] = field(default_factory=list)
    pricing_model: str = ""
    categories: list[str] = field(default_factory=list)
    trust_score: float = 0.0
    health_status: str = "unknown"
    last_seen_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalInvocationRecord:
    invocation_id: str
    provider_id: str
    resource_id: str
    adapter_type: str
    task_id: str | None
    request_summary: str
    price_requested: str | None
    price_paid: str | None
    asset: str | None
    network: str
    facilitator_used: str | None
    payment_status: str  # pending, completed, failed
    response_status: int
    latency_ms: float
    result_summary: str
    error_type: str | None
    retry_count: int
    created_at: str
    completed_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "provider_id": self.provider_id,
            "resource_id": self.resource_id,
            "adapter_type": self.adapter_type,
            "task_id": self.task_id,
            "request_summary": self.request_summary,
            "price_requested": self.price_requested,
            "price_paid": self.price_paid,
            "asset": self.asset,
            "network": self.network,
            "facilitator_used": self.facilitator_used,
            "payment_status": self.payment_status,
            "response_status": self.response_status,
            "latency_ms": self.latency_ms,
            "result_summary": self.result_summary,
            "error_type": self.error_type,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ProviderRelationship:
    provider_id: str
    first_seen_at: str
    last_invoked_at: str
    successful_calls: int
    failed_calls: int
    avg_latency_ms: float
    avg_cost: str | None
    last_price_seen: str | None
    quality_score: float
    trust_score: float
    preferred_for_task_types: list[str] = field(default_factory=list)
    cooldown_until: str | None = None
    blacklist_reason: str | None = None
    notes: str = ""
