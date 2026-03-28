#!/usr/bin/env python3
"""
Poll Stripe PaymentIntent status for a marketplace order (after crypto deposit).

Usage:
  python scripts/marketplace-verify-order.py --pi pi_xxx
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
    p = argparse.ArgumentParser(description="Verify marketplace PaymentIntent status")
    p.add_argument("--pi", required=True, help="Stripe PaymentIntent id (pi_...)")
    args = p.parse_args()

    from integrations.stripe_mpp.config import StripeMppConfig

    mpp = StripeMppConfig.from_env()
    if not mpp.secret_key:
        print("Set STRIPE_SECRET_KEY", file=sys.stderr)
        return 1

    try:
        import stripe
    except ImportError:
        print("pip install stripe", file=sys.stderr)
        return 1

    try:
        client = stripe.StripeClient(
            mpp.secret_key,
            stripe_version=mpp.api_version,
        )
        pi = client.v1.payment_intents.retrieve(args.pi)
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}", file=sys.stderr)
        return 1

    st = pi.status if hasattr(pi, "status") else pi.get("status")
    print("payment_intent_id:", args.pi)
    print("status:", st)
    if st == "succeeded":
        print("OK: Fulfill the buyer (send bundle ZIP / link).")
        return 0
    print("Payment not yet succeeded; retry after deposit confirms.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
