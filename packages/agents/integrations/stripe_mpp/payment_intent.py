"""Create Stripe PaymentIntents with crypto deposit (Tempo) — mirrors Stripe MPP Node samples."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CryptoDepositDetails:
    payment_intent_id: str
    pay_to_address: str
    network: str
    amount_cents: int
    currency: str


def _pi_to_dict(pi: Any) -> dict[str, Any]:
    if hasattr(pi, "to_dict"):
        return pi.to_dict()
    if isinstance(pi, dict):
        return pi
    raise TypeError("Unexpected PaymentIntent type")


def extract_tempo_deposit_address(payment_intent: Any) -> str:
    d = _pi_to_dict(payment_intent)
    na = d.get("next_action") or {}
    cdd = na.get("crypto_display_details") or {}
    dep = cdd.get("deposit_addresses") or {}
    tempo = dep.get("tempo") or {}
    addr = tempo.get("address")
    if not addr or not isinstance(addr, str):
        raise ValueError(
            "PaymentIntent missing next_action.crypto_display_details.deposit_addresses.tempo.address"
        )
    return addr


# Stripe minimum for many USD charges is $0.50; MPP samples often use $1.00 for stablecoin math.
_MIN_USD_CRYPTO_DEPOSIT = Decimal("0.50")


def create_crypto_deposit_payment_intent(
    *,
    amount_usd: Decimal | str | float,
    secret_key: str,
    api_version: str = "2026-03-04.preview",
    testnet: bool = True,
    metadata: dict[str, str] | None = None,
) -> CryptoDepositDetails:
    try:
        import stripe
    except ImportError as e:
        raise ImportError(
            "Stripe MPP PaymentIntent helpers require the `stripe` package. "
            "Install with: pip install stripe"
        ) from e

    amt = Decimal(str(amount_usd))
    if amt < _MIN_USD_CRYPTO_DEPOSIT:
        raise ValueError(
            f"amount_usd must be at least {_MIN_USD_CRYPTO_DEPOSIT} USD for Stripe PaymentIntents "
            f"(got {amt})."
        )
    cents = int((amt * 100).to_integral_value())

    # Explicit crypto + deposit mode (same as Stripe MPP Node samples). Do not pass
    # payment_method_configuration here: Stripe rejects nested crypto deposit_options
    # when a PMC is set, and deposit addresses are not created via PMC-only creates.
    params: dict[str, Any] = {
        "amount": cents,
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
    if metadata:
        clean: dict[str, str] = {}
        for k, v in metadata.items():
            ks = str(k).strip()
            if not ks or len(ks) > 40:
                continue
            clean[ks] = str(v)[:500]
        if clean:
            params["metadata"] = clean

    client = stripe.StripeClient(
        secret_key,
        stripe_version=api_version,
    )
    pi = client.v1.payment_intents.create(params=params)
    addr = extract_tempo_deposit_address(pi)
    return CryptoDepositDetails(
        payment_intent_id=pi.id if hasattr(pi, "id") else str(pi["id"]),
        pay_to_address=addr,
        network="tempo",
        amount_cents=cents,
        currency="usd",
    )
