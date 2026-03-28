from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import MarketplaceConfig


def finalize_pending_order(
    cfg: MarketplaceConfig,
    payment_intent_id: str,
) -> dict[str, Any] | None:
    """
    Move pending-{pi}.json to fulfilled-{pi}.json with a download_token.
    Returns the fulfilled payload, or None if this order was never tracked.
    If already fulfilled (idempotent webhook), returns the existing record.
    """
    pending = cfg.orders_dir / f"pending-{payment_intent_id}.json"
    fulfilled_path = cfg.orders_dir / f"fulfilled-{payment_intent_id}.json"
    if fulfilled_path.exists():
        return json.loads(fulfilled_path.read_text(encoding="utf-8"))
    if not pending.exists():
        return None

    raw = json.loads(pending.read_text(encoding="utf-8"))
    token = secrets.token_urlsafe(32)
    out = dict(raw)
    out["status"] = "fulfilled"
    out["fulfilled_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    out["download_token"] = token
    fulfilled_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    pending.unlink()
    return out


def load_fulfilled(cfg: MarketplaceConfig, payment_intent_id: str) -> dict[str, Any] | None:
    p = cfg.orders_dir / f"fulfilled-{payment_intent_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def find_fulfillment_by_token(
    cfg: MarketplaceConfig, download_token: str
) -> dict[str, Any] | None:
    for p in cfg.orders_dir.glob("fulfilled-*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("download_token") == download_token:
            return d
    return None


def parse_stripe_webhook_event(
    payload: bytes, sig_header: str | None, webhook_secret: str
) -> Any:
    try:
        import stripe
    except ImportError as e:
        raise ImportError("pip install stripe") from e
    if not sig_header:
        raise ValueError("Missing Stripe-Signature header")
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
