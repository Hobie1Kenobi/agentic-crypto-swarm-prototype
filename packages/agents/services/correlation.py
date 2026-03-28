from __future__ import annotations

import hashlib


def external_payment_ref(
    xrpl_tx_hash: str,
    destination_tag: int | None = None,
    delivered_amount: str = "",
    quote_id: str = "",
) -> str:
    parts = [
        (xrpl_tx_hash or "").strip().lower(),
        str(destination_tag or ""),
        str(delivered_amount or ""),
        (quote_id or "").strip(),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode()).hexdigest()
