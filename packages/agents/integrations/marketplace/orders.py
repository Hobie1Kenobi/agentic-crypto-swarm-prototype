from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import MarketplaceConfig


def write_pending_order(
    cfg: MarketplaceConfig,
    *,
    payment_intent_id: str,
    amount_cents: int,
    currency: str,
    pay_to_address: str,
    network: str,
    product_id: str,
    extra: dict[str, Any] | None = None,
) -> tuple[Path, str]:
    cfg.orders_dir.mkdir(parents=True, exist_ok=True)
    order_ref = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "order_reference": order_ref,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "payment_intent_id": payment_intent_id,
        "amount_cents": amount_cents,
        "currency": currency,
        "pay_to_address": pay_to_address,
        "network": network,
        "product_id": product_id,
        "status": "awaiting_payment",
    }
    if extra:
        payload["extra"] = extra
    path = cfg.orders_dir / f"pending-{payment_intent_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path, order_ref
