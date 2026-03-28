"""Environment-driven config for optional Stripe MPP (Machine Payments Protocol) wiring."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StripeMppConfig:
    enabled: bool
    secret_key: str | None
    testnet: bool
    api_version: str
    payment_method_configuration: str | None

    @classmethod
    def from_env(cls) -> StripeMppConfig:
        enabled = os.getenv("STRIPE_MPP_ENABLED", "0").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        sk = os.getenv("STRIPE_SECRET_KEY", "").strip() or None
        testnet = os.getenv("STRIPE_MPP_TESTNET", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        api_version = os.getenv(
            "STRIPE_API_VERSION", "2026-03-04.preview"
        ).strip()
        pmc = os.getenv("STRIPE_PAYMENT_METHOD_CONFIGURATION", "").strip() or None
        return cls(
            enabled=enabled,
            secret_key=sk,
            testnet=testnet,
            api_version=api_version,
            payment_method_configuration=pmc,
        )
