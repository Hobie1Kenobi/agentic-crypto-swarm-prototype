#!/usr/bin/env python3
"""
List Payment Method Configurations (pmc_...) for the Stripe account.

Use this to pick a valid ID if you had "No such payment_method_configuration".
Deposit-intent flow does not use PMC (see documentation/marketplace-stripe/STRIPE_MPP_INTEGRATION.md).
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
        print("Set STRIPE_SECRET_KEY in .env.", file=sys.stderr)
        return 1

    client = stripe.StripeClient(
        cfg.secret_key,
        stripe_version=cfg.api_version,
    )
    lst = client.v1.payment_method_configurations.list(params={"limit": 100})
    rows = lst.data or []
    if not rows:
        print("No payment_method_configurations found.")
        return 0
    print("id\tname\tactive\tcrypto.available")
    for x in rows:
        o = client.v1.payment_method_configurations.retrieve(x.id)
        d = o.to_dict() if hasattr(o, "to_dict") else {}
        cr = d.get("crypto") or {}
        avail = cr.get("available")
        print(
            f"{x.id}\t{getattr(x, 'name', '')}\t{getattr(x, 'active', '')}\t{avail}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
