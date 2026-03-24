"""
Seller-side x402 scaffolding — expose our swarm capabilities as x402-paid endpoints.

Phase 3 scaffold: structure for declaring priced endpoints, 402 responses,
verification via facilitator, and fulfillment after payment.
"""
from __future__ import annotations

from typing import Any, Callable


def declare_priced_endpoint(
    path: str,
    price_usd: str,
    network: str = "eip155:84532",
    pay_to: str = "",
) -> dict[str, Any]:
    """
    Declare a priced endpoint for x402 seller mode.
    Returns config dict for middleware/facilitator.
    """
    return {
        "path": path,
        "price_usd": price_usd,
        "network": network,
        "pay_to": pay_to,
        "scheme": "exact",
    }


def build_402_response(config: dict[str, Any], metadata: str = "") -> dict[str, Any]:
    """
    Build 402 Payment Required response payload.
    To be used with PAYMENT-REQUIRED header or JSON body.
    """
    return {
        "message": "Payment Required",
        "payment": {
            "scheme": config.get("scheme", "exact"),
            "network": config.get("network"),
            "pay_to": config.get("pay_to"),
            "price": config.get("price_usd"),
            "metadata": metadata,
        },
    }


def verify_and_fulfill(
    payment_payload: bytes | str,
    requirements: dict[str, Any],
    fulfill_fn: Callable[[], Any],
    facilitator_url: str = "",
) -> tuple[bool, Any | None]:
    """
    Verify payment via facilitator, then call fulfill_fn and return result.
    Returns (verified, result).
    """
    try:
        from x402 import x402ResourceServerSync
        from x402.http import HTTPFacilitatorClientSync
    except ImportError:
        return False, None
    if not facilitator_url:
        return False, None
    try:
        facilitator = HTTPFacilitatorClientSync(url=facilitator_url)
        server = x402ResourceServerSync(facilitator)
        server.initialize()
        result = server.verify_payment(payment_payload, requirements)
        if result and getattr(result, "is_valid", False):
            return True, fulfill_fn()
        return False, None
    except Exception:
        return False, None
