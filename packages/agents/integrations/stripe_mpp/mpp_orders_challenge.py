"""HTTP 402 MPP challenge for POST /v1/orders with an empty body (discovery / agent probes)."""

from __future__ import annotations

import os
import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from integrations.marketplace.config import MarketplaceConfig
    from integrations.stripe_mpp.config import StripeMppConfig

_fallback_secret: str | None = None


def _mpp_secret_key() -> str:
    global _fallback_secret
    for k in ("MARKETPLACE_MPP_SECRET_KEY", "MPP_SECRET_KEY"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    if _fallback_secret is None:
        _fallback_secret = secrets.token_hex(32)
    return _fallback_secret


def _problem_payment_required(detail: str, **extra: object) -> dict:
    body: dict = {
        "type": "https://paymentauth.org/problems/payment-required",
        "title": "Payment Required",
        "status": 402,
        "detail": detail,
    }
    body.update({k: v for k, v in extra.items() if v is not None})
    return body


async def maybe_mpp_empty_orders_challenge(
    request: Request,
    *,
    cfg: "MarketplaceConfig",
    mpp_cfg: "StripeMppConfig",
    raw_body: bytes,
) -> JSONResponse | None:
    """
    If the client sends an empty POST (no JSON body), return MPP 402 with WWW-Authenticate
    when pympp[tempo] is available; otherwise a problem+json 402 with deposit hints from Stripe PI.

    Non-empty bodies return None so the caller runs the normal order-creation path.
    """
    stripped = raw_body.strip()
    if len(stripped) == 0 and (os.getenv("MARKETPLACE_MPP_EMPTY_POST_DISABLE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return None
    probe_json = (os.getenv("MARKETPLACE_MPP_PROBE_EMPTY_JSON") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    is_probe = len(stripped) == 0 or (probe_json and stripped == b"{}")
    if not is_probe:
        return None

    if not cfg.http_enabled:
        raise HTTPException(status_code=503, detail="MARKETPLACE_HTTP_ENABLED is not 1")

    if not mpp_cfg.secret_key:
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not set")

    from integrations.marketplace.config import product_dashboard_bundle
    from integrations.stripe_mpp import create_crypto_deposit_payment_intent

    prod = product_dashboard_bundle()
    amount = cfg.dashboard_bundle_price_usd
    if amount < prod.price_usd_min:
        raise HTTPException(
            status_code=500,
            detail=f"MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD must be >= {prod.price_usd_min}",
        )

    meta = {"product_id": prod.product_id, "product_name": prod.name[:500]}
    try:
        details = create_crypto_deposit_payment_intent(
            amount_usd=amount,
            secret_key=mpp_cfg.secret_key,
            api_version=mpp_cfg.api_version,
            testnet=mpp_cfg.testnet,
            metadata=meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    pay_to = details.pay_to_address.strip()

    try:
        from mpp import Challenge
        from mpp.methods.tempo import ChargeIntent, tempo
        from mpp.methods.tempo._defaults import CHAIN_ID, TESTNET_CHAIN_ID
        from mpp.server import Mpp
    except ImportError:
        return JSONResponse(
            status_code=402,
            content=_problem_payment_required(
                "Payment required. Install pympp[tempo] for full WWW-Authenticate (pip install 'pympp[tempo]').",
                pay_to_address=details.pay_to_address,
                amount_cents=details.amount_cents,
                currency=details.currency,
                payment_intent_id=details.payment_intent_id,
            ),
        )

    chain_id = TESTNET_CHAIN_ID if mpp_cfg.testnet else CHAIN_ID
    method = tempo(
        recipient=pay_to,
        intents={"charge": ChargeIntent()},
        chain_id=chain_id,
    )
    handler = Mpp.create(method=method, secret_key=_mpp_secret_key())
    result = await handler.charge(
        request.headers.get("authorization"),
        amount=str(amount),
    )
    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content=_problem_payment_required(
                "Payment is required to create an order.",
                challenge_hint="Retry with Authorization: Payment after funding the Tempo deposit address.",
                pay_to_address=details.pay_to_address,
                payment_intent_id=details.payment_intent_id,
            ),
            headers={"WWW-Authenticate": result.to_www_authenticate(handler.realm)},
        )

    return JSONResponse(
        status_code=402,
        content=_problem_payment_required(
            "Unexpected MPP state after challenge handler (expected Challenge).",
            pay_to_address=details.pay_to_address,
        ),
    )
