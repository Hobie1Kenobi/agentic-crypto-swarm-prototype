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
    try:
        from services.pricing import pricing_catalog_lookup as _lookup
        return _lookup(service, params)
    except ImportError:
        return {"amount": "1", "asset": "XRP", "service": service, "amount_wei": int(0.01 * 1e18)}


def budget_enforcement_check(customer_id: str, amount_wei: int) -> bool:
    import os
    if (os.getenv("CUSTOMER_BALANCE_ENABLED", "").strip().lower() not in {"1", "true", "yes", "on"}):
        return True
    try:
        from services.customer_balance import budget_enforcement_check as _check
        return _check(customer_id, amount_wei)
    except ImportError:
        return True


def metering_record(service: str, customer_id: str, amount: int, metadata: dict[str, Any] | None = None) -> None:
    try:
        from services.customer_balance import metering_record as _record
        _record(service, customer_id, amount, metadata)
    except ImportError:
        pass
