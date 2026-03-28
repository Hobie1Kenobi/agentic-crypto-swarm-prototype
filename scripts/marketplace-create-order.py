#!/usr/bin/env python3
"""
Create a Stripe MPP crypto-deposit PaymentIntent for the sellable dashboard bundle.

Writes marketplace/orders/pending-<pi_id>.json for operator fulfillment.
Requires STRIPE_SECRET_KEY; optional STRIPE_MPP_ENABLED=1 for documentation only.

Usage:
  python scripts/marketplace-create-order.py
  python scripts/marketplace-create-order.py --amount 49.00 --buyer-ref buyer@example.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_AGENTS = _REPO / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO / ".env", override=True)
except ImportError:
    pass


def main() -> int:
    p = argparse.ArgumentParser(description="Marketplace order (Stripe MPP deposit)")
    p.add_argument(
        "--amount",
        default=None,
        help="Override USD price (default: MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD or 49.00)",
    )
    p.add_argument(
        "--buyer-ref",
        default="",
        help="Optional email or opaque id stored in Stripe metadata + order file",
    )
    args = p.parse_args()

    from integrations.marketplace.config import (
        MarketplaceConfig,
        product_dashboard_bundle,
    )
    from integrations.marketplace.orders import write_pending_order
    from integrations.stripe_mpp.config import StripeMppConfig
    from integrations.stripe_mpp import create_crypto_deposit_payment_intent

    mpp = StripeMppConfig.from_env()
    if not mpp.secret_key:
        print("Set STRIPE_SECRET_KEY in .env", file=sys.stderr)
        return 1

    cfg = MarketplaceConfig.from_env()
    prod = product_dashboard_bundle()
    if args.amount is not None:
        from decimal import Decimal

        amount = Decimal(str(args.amount))
    else:
        amount = cfg.dashboard_bundle_price_usd
    if amount < prod.price_usd_min:
        print(
            f"Amount must be >= {prod.price_usd_min} USD (Stripe PaymentIntent minimum).",
            file=sys.stderr,
        )
        return 1

    try:
        import stripe
    except ImportError:
        print("pip install stripe", file=sys.stderr)
        return 1

    meta = {
        "product_id": prod.product_id,
        "product_name": prod.name[:500],
    }
    if args.buyer_ref.strip():
        meta["buyer_ref"] = args.buyer_ref.strip()[:500]

    try:
        details = create_crypto_deposit_payment_intent(
            amount_usd=amount,
            secret_key=mpp.secret_key,
            api_version=mpp.api_version,
            testnet=mpp.testnet,
            metadata=meta,
        )
    except stripe.error.AuthenticationError:
        print("Stripe rejected STRIPE_SECRET_KEY.", file=sys.stderr)
        return 1
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}", file=sys.stderr)
        return 1

    path, order_ref = write_pending_order(
        cfg,
        payment_intent_id=details.payment_intent_id,
        amount_cents=details.amount_cents,
        currency=details.currency,
        pay_to_address=details.pay_to_address,
        network=details.network,
        product_id=prod.product_id,
        extra={"buyer_ref": args.buyer_ref.strip()} if args.buyer_ref.strip() else None,
    )

    print("order_reference:", order_ref)
    print("payment_intent_id:", details.payment_intent_id)
    print("amount_cents:", details.amount_cents)
    print("currency:", details.currency)
    print("pay_to_address:", details.pay_to_address)
    print("network:", details.network)
    print("pending_order_file:", path)
    print()
    print("Next: buyer sends funds to pay_to_address on Tempo; then run:")
    print(f"  python scripts/marketplace-verify-order.py --pi {details.payment_intent_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
