#!/usr/bin/env python3
"""
Optional: create a Stripe PaymentIntent with crypto deposit (Tempo) — MPP-related.

Requires: pip install stripe, STRIPE_SECRET_KEY in environment.

Does not start a server; safe next to other long-running seller/soak processes.

Usage:
  python scripts/stripe-mpp-deposit-intent.py --amount 1.00
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_AGENTS = _REPO / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

try:
    from dotenv import load_dotenv

    # Prefer values from repo .env over stale shell STRIPE_* (common when testing).
    load_dotenv(_REPO / ".env", override=True)
except ImportError:
    pass


def main() -> int:
    p = argparse.ArgumentParser(description="Stripe MPP-style crypto deposit PaymentIntent")
    p.add_argument(
        "--amount",
        default="1.00",
        help="USD amount (default 1.00; Stripe requires at least 0.50 for typical USD charges)",
    )
    args = p.parse_args()

    from integrations.stripe_mpp.config import StripeMppConfig

    cfg = StripeMppConfig.from_env()
    if not cfg.secret_key:
        print("Set STRIPE_SECRET_KEY (and optionally STRIPE_MPP_ENABLED=1).", file=sys.stderr)
        return 1

    try:
        import stripe
    except ImportError:
        print("Install: pip install stripe", file=sys.stderr)
        return 1

    from integrations.stripe_mpp import create_crypto_deposit_payment_intent

    try:
        details = create_crypto_deposit_payment_intent(
            amount_usd=args.amount,
            secret_key=cfg.secret_key,
            api_version=cfg.api_version,
            testnet=cfg.testnet,
        )
    except stripe.error.AuthenticationError:
        print(
            "Stripe rejected the API key. Check STRIPE_SECRET_KEY in .env (repo root).",
            file=sys.stderr,
        )
        return 1
    except stripe.error.StripeError as e:
        msg = str(e)
        if "payment_method_options[crypto]" in msg and "unknown" in msg.lower():
            print(
                "Stripe does not accept deposit-mode crypto options on this key yet. Enable "
                "crypto payins / deposit mode (preview) for the account, or try a test secret key:",
                file=sys.stderr,
            )
            print(
                "  https://support.stripe.com/questions/get-started-with-pay-with-crypto",
                file=sys.stderr,
            )
            print(
                "  https://docs.stripe.com/payments/deposit-mode-stablecoin-payments",
                file=sys.stderr,
            )
        elif "crypto" in msg.lower() and (
            "invalid" in msg.lower() or "activated" in msg.lower()
        ):
            print(
                "Enable Stablecoins and Crypto in the Stripe Dashboard, then retry:",
                file=sys.stderr,
            )
            print(
                "  https://dashboard.stripe.com/settings/payment_methods",
                file=sys.stderr,
            )
        print(f"Stripe error: {e}", file=sys.stderr)
        return 1
    print("payment_intent_id:", details.payment_intent_id)
    print("pay_to_address:", details.pay_to_address)
    print("network:", details.network)
    print("amount_cents:", details.amount_cents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
