from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaymentTaskCorrelation:
    external_payment_id: str | None
    xrpl_tx_hash: str | None
    internal_task_id: int | None
    celo_tx_hashes: list[dict[str, Any]]
    payment_rail: str
    payment_asset: str
    verified: bool
    verification_boundary: str


def map_payment_to_task(
    payment_receipt: dict[str, Any],
    internal_task_id: int | None,
    celo_tx_hashes: list[dict[str, Any]],
) -> PaymentTaskCorrelation:
    return PaymentTaskCorrelation(
        external_payment_id=payment_receipt.get("external_payment_id"),
        xrpl_tx_hash=payment_receipt.get("tx_hash") or payment_receipt.get("xrpl_tx_hash"),
        internal_task_id=internal_task_id,
        celo_tx_hashes=celo_tx_hashes or [],
        payment_rail=payment_receipt.get("payment_rail", "unknown"),
        payment_asset=payment_receipt.get("payment_asset", ""),
        verified=bool(payment_receipt.get("verified")),
        verification_boundary=payment_receipt.get("verification_boundary", "unknown"),
    )
