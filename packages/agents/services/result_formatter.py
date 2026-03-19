from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PublicAdapterResponse:
    ok: bool
    external_request_id: str | None
    internal_task_id: int | None
    result_text: str
    tx_hashes: list[str]
    boundary: str
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "external_request_id": self.external_request_id,
            "internal_task_id": self.internal_task_id,
            "result_text": self.result_text,
            "tx_hashes": self.tx_hashes,
            "boundary": self.boundary,
            "notes": self.notes,
        }


def format_hybrid_result(private_market_report: dict[str, Any], external_request_id: str | None) -> PublicAdapterResponse:
    task = private_market_report.get("task", {}) if isinstance(private_market_report, dict) else {}
    tx_hashes = [e.get("tx_hash") for e in private_market_report.get("tx_hashes", []) if e.get("tx_hash")] if isinstance(private_market_report, dict) else []
    ok = bool(private_market_report.get("ok")) if isinstance(private_market_report, dict) else False

    result_text = str(task.get("result_metadata") or task.get("query") or "")
    internal_task_id = task.get("task_id")
    try:
        internal_task_id = int(internal_task_id) if internal_task_id is not None else None
    except Exception:
        internal_task_id = None

    return PublicAdapterResponse(
        ok=ok,
        external_request_id=external_request_id,
        internal_task_id=internal_task_id,
        result_text=result_text or "No result.",
        tx_hashes=[str(h) for h in tx_hashes if h],
        boundary="hybrid:public_intake->private_onchain_settlement",
    )

