"""
Stripe Machine Payments Protocol (MPP) — optional helpers.

Official Stripe samples use Node (`mppx/server`, `tempo.charge`). This package provides
Python-side PaymentIntent creation for crypto deposit addresses on Tempo, aligned with
Stripe's preview API. HTTP 402 challenge/response signing remains Node-oriented unless
you add a small sidecar or a compatible Python implementation.
"""

from .config import StripeMppConfig
from .payment_intent import (
    CryptoDepositDetails,
    create_crypto_deposit_payment_intent,
    extract_tempo_deposit_address,
)

__all__ = [
    "StripeMppConfig",
    "CryptoDepositDetails",
    "create_crypto_deposit_payment_intent",
    "extract_tempo_deposit_address",
]
