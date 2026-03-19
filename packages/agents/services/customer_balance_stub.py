from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CustomerBalanceCredit:
    customer_id: str
    amount_wei: int
    asset: str
    source: str
    external_ref: str | None


def credit_from_xrpl_receipt(receipt: dict[str, Any], customer_id: str = "default") -> CustomerBalanceCredit | None:
    if not receipt or not receipt.get("verified"):
        return None
    amount = receipt.get("amount", "0")
    try:
        amount_wei = int(float(amount) * 1e6) if isinstance(amount, str) else int(amount)
    except (ValueError, TypeError):
        amount_wei = 0
    return CustomerBalanceCredit(
        customer_id=customer_id,
        amount_wei=amount_wei,
        asset=receipt.get("payment_asset", "XRP"),
        source="xrpl",
        external_ref=receipt.get("tx_hash") or receipt.get("external_payment_id"),
    )


def pricing_catalog_lookup(service: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return {"amount": "1", "asset": "XRP", "service": service}


def budget_enforcement_check(customer_id: str, amount_wei: int) -> bool:
    return True


def metering_record(service: str, customer_id: str, amount: int, metadata: dict[str, Any] | None = None) -> None:
    pass
