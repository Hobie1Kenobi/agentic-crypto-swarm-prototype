from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


@dataclass
class XRPLQuote:
    job_id: str
    quote_id: str
    destination_tag: int
    destination: str
    memo_ref: str
    expected_asset: str
    expected_amount: str
    amount_tolerance_pct: float
    expiry_at: float
    x_address: str | None
    metadata: dict[str, Any]


def _next_destination_tag() -> int:
    base = int(_env("XRPL_DESTINATION_TAG_BASE", "100000"))
    seed = int(time.time() * 1000) % 1_000_000
    return base + seed


def create_quote(
    task_request: dict[str, Any],
    receiver: str | None = None,
    amount: str | None = None,
    asset: str | None = None,
    validity_seconds: int | None = None,
) -> XRPLQuote:
    job_id = str(task_request.get("job_id") or uuid.uuid4().hex[:16])
    quote_id = str(uuid.uuid4().hex[:16])
    receiver = receiver or _env("XRPL_RECEIVER_ADDRESS", "rN7n7otQDd6FczFgLdlqtyMVrn3e1DjxvV")
    asset = asset or _env("XRPL_SETTLEMENT_ASSET", "XRP").strip().upper()
    validity = validity_seconds or int(_env("XRPL_QUOTE_VALIDITY_SECONDS", "300"))
    expiry_at = time.time() + validity

    if amount is None:
        try:
            from services.pricing import pricing_catalog_lookup
            catalog = pricing_catalog_lookup("task_execution", task_request)
            if catalog and asset == "RLUSD":
                amount = str(catalog.get("amount_rlusd", "1"))
            elif catalog:
                amount = str(catalog.get("amount_xrp", catalog.get("amount", "1")))
            else:
                amount = "1"
        except ImportError:
            amount = "1"

    destination_tag = _next_destination_tag()
    memo_ref = str(task_request.get("query", task_request.get("prompt", job_id)))[:64]
    tolerance = float(_env("XRPL_AMOUNT_TOLERANCE_PCT", "0.1"))

    x_address = None
    if _env("XRPL_USE_X_ADDRESS", "0").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            from xrpl.core.addresscodec import classic_address_to_xaddress
            is_test = (_env("XRPL_NETWORK", "testnet").strip().lower() == "testnet")
            x_address = classic_address_to_xaddress(receiver, destination_tag, is_test)
        except ImportError:
            pass

    return XRPLQuote(
        job_id=job_id,
        quote_id=quote_id,
        destination_tag=destination_tag,
        destination=receiver,
        memo_ref=memo_ref,
        expected_asset=asset,
        expected_amount=str(amount),
        amount_tolerance_pct=tolerance,
        expiry_at=expiry_at,
        x_address=x_address,
        metadata={"task_request": task_request},
    )


XRP_DROPS = 1_000_000


def amount_within_tolerance(delivered: str, expected: str, tolerance_pct: float) -> bool:
    try:
        d = float(delivered)
        e = float(expected)
        if e <= 0:
            return d >= 0
        if d >= XRP_DROPS and e < 100:
            d = d / XRP_DROPS
        elif d < 100 and e >= XRP_DROPS:
            e = e / XRP_DROPS
        elif e < 100 and d >= 100:
            d = d / XRP_DROPS
        elif d < 100 and e >= 100:
            e = e / XRP_DROPS
        diff_pct = abs(d - e) / e * 100
        return diff_pct <= tolerance_pct
    except (ValueError, TypeError):
        return delivered == expected
