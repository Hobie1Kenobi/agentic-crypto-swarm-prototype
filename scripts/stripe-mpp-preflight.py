#!/usr/bin/env python3
"""
Verify Stripe API key + preview version, and whether the account can create crypto PaymentIntents.

Does not start a server. Safe to run alongside other processes.

If crypto is not enabled in the Dashboard, you will see an actionable error before wiring MPP.
"""

from __future__ import annotations

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
    try:
        import stripe
    except ImportError:
        print("Install: pip install stripe", file=sys.stderr)
        return 1

    from integrations.stripe_mpp.config import StripeMppConfig

    cfg = StripeMppConfig.from_env()
    if not cfg.secret_key:
        print("Set STRIPE_SECRET_KEY in .env (repo root).", file=sys.stderr)
        return 1

    client = stripe.StripeClient(
        cfg.secret_key,
        stripe_version=cfg.api_version,
    )

    try:
        bal = client.v1.balance.retrieve()
    except stripe.error.AuthenticationError:
        print(
            "Stripe rejected the API key. Check STRIPE_SECRET_KEY in .env.",
            file=sys.stderr,
        )
        return 1
    except stripe.error.StripeError as e:
        print(f"Stripe error (balance): {e}", file=sys.stderr)
        return 1

    avail = getattr(bal, "available", None) or []
    print("stripe: ok (balance retrieved)")
    if avail:
        print("  available balances:", len(avail), "currency bucket(s)")

    probe_params = {
        "amount": 50,
        "currency": "usd",
        "payment_method_types": ["crypto"],
        "confirm": False,
    }

    try:
        client.v1.payment_intents.create(params=probe_params)
    except stripe.error.StripeError as e:
        msg = str(e)
        if "crypto" in msg.lower() and (
            "invalid" in msg.lower() or "activated" in msg.lower()
        ):
            print()
            print("Crypto PaymentIntents are not enabled for this Stripe account yet.")
            print("1) Dashboard -> Settings -> Payment methods -> request Stablecoins and Crypto")
            print("   https://dashboard.stripe.com/settings/payment_methods")
            print("2) Deposit mode / MPP also requires crypto payins enabled per Stripe:")
            print("   https://support.stripe.com/questions/get-started-with-pay-with-crypto")
            print("3) Deposit mode doc: https://docs.stripe.com/payments/deposit-mode-stablecoin-payments")
            print()
            print("Underlying error:", msg)
            return 2
        print(f"Stripe error (payment_intents probe): {e}", file=sys.stderr)
        return 1

    print("crypto PaymentIntent: unexpected success on minimal create (check Dashboard)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
