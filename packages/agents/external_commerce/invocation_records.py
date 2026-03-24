"""
External invocation records — append-only evidence of paid external calls.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from .schemas import ExternalInvocationRecord


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_path() -> Path:
    return _repo_root() / "external_commerce_data" / "external-invocations.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class InvocationRecords:
    def __init__(self, path: Path | None = None):
        self._path = path or _default_path()

    def append(self, record: ExternalInvocationRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        import json
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)

    def create_record(
        self,
        provider_id: str,
        resource_id: str,
        adapter_type: str,
        task_id: str | None,
        request_summary: str,
        price_requested: str | None = None,
        price_paid: str | None = None,
        asset: str | None = None,
        network: str = "",
        facilitator_used: str | None = None,
        payment_status: str = "pending",
        response_status: int = 0,
        latency_ms: float = 0,
        result_summary: str = "",
        error_type: str | None = None,
        retry_count: int = 0,
        completed_at: str | None = None,
    ) -> ExternalInvocationRecord:
        now = _ts()
        inv = ExternalInvocationRecord(
            invocation_id=str(uuid.uuid4().hex[:16]),
            provider_id=provider_id,
            resource_id=resource_id,
            adapter_type=adapter_type,
            task_id=task_id,
            request_summary=request_summary[:500],
            price_requested=price_requested,
            price_paid=price_paid,
            asset=asset,
            network=network,
            facilitator_used=facilitator_used,
            payment_status=payment_status,
            response_status=response_status,
            latency_ms=latency_ms,
            result_summary=result_summary[:500],
            error_type=error_type,
            retry_count=retry_count,
            created_at=now,
            completed_at=completed_at or now,
        )
        return inv
