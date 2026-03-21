from __future__ import annotations

import os
from typing import Any


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def get_task_escrow_wei() -> int:
    eth = _env("TASK_ESCROW_ETH", "0.01")
    try:
        return int(float(eth) * 1e18)
    except (ValueError, TypeError):
        return int(0.01 * 1e18)


def pricing_catalog_lookup(service: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if service == "task_execution":
        wei = get_task_escrow_wei()
        asset = _env("XRPL_SETTLEMENT_ASSET", "XRP").strip().upper()
        xrp_amount = _env("PRICING_TASK_XRP", "1")
        rlusd_amount = _env("PRICING_TASK_RLUSD", "1")
        return {
            "amount_wei": wei,
            "amount": str(wei),
            "asset": asset,
            "service": service,
            "amount_xrp": xrp_amount,
            "amount_rlusd": rlusd_amount,
        }
    wei = get_task_escrow_wei()
    return {"amount_wei": wei, "amount": str(wei), "asset": "XRP", "service": service}
