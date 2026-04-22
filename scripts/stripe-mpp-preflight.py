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
    print(f"  Stripe-Version (from STRIPE_API_VERSION): {cfg.api_version!r}")
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
        print(f"Stripe error (payment_intents minimal probe): {e}", file=sys.stderr)
        return 1

    print("crypto PaymentIntent (minimal create, confirm=false): ok")

    deposit_params = {
        "amount": 50,
        "currency": "usd",
        "payment_method_types": ["crypto"],
        "payment_method_data": {"type": "crypto"},
        "payment_method_options": {
            "crypto": {
                "mode": "deposit",
                "deposit_options": {"networks": ["tempo"]},
            }
        },
        "confirm": True,
    }

    try:
        pi = client.v1.payment_intents.create(params=deposit_params)
    except stripe.error.InvalidRequestError as e:
        msg = str(e)
        if "unknown parameter" in msg.lower() and "mode" in msg.lower():
            print()
            print("Deposit mode is NOT active on this Stripe account for the API version above.")
            print("Your Dashboard can show Stablecoins and Crypto + a Connect PMC (pmc_...) as enabled,")
            print("but deposit addresses need a separate Stripe entitlement (per their docs).")
            print()
            print("1) Confirm STRIPE_API_VERSION is exactly a preview that supports deposit, e.g.:")
            print("   2026-03-04.preview  (see https://docs.stripe.com/payments/deposit-mode-stablecoin-payments)")
            print("2) Email machine-payments@stripe.com to request deposit / machine-payments access.")
            print("3) This repo does NOT pass payment_method_configuration (pmc_) on deposit intents —")
            print("   Connect > Payment methods PMCs are separate from server-side PaymentIntent.create.")
            print()
            print("Underlying error:", msg)
            return 3
        print(f"Stripe error (deposit PaymentIntent): {e}", file=sys.stderr)
        return 1
    except stripe.error.StripeError as e:
        print(f"Stripe error (deposit PaymentIntent): {e}", file=sys.stderr)
        return 1

    pi_id = pi.id if hasattr(pi, "id") else pi.get("id")
    print(f"deposit mode PaymentIntent: ok (created {pi_id})")
    print("  (If this succeeded, POST /v1/orders empty-body MPP probe should work too.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
