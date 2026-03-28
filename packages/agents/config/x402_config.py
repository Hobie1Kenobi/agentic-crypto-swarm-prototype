"""
x402-specific configuration.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class X402Config:
    enabled: bool
    protocol_version: str
    discovery_enabled: bool
    test_facilitator_url: str
    allowed_networks: list[str]
    max_spend_usd: float
    buyer_base_sepolia_key_env: str
    dry_run: bool


def get_x402_config() -> X402Config:
    networks_raw = _env("X402_ALLOWED_NETWORKS", "eip155:84532")
    return X402Config(
        enabled=_truthy(_env("X402_ENABLED")),
        protocol_version=_env("X402_PROTOCOL_VERSION", "2"),
        discovery_enabled=_truthy(_env("X402_DISCOVERY_ENABLED", "1")),
        test_facilitator_url=_env("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator"),
        allowed_networks=[n.strip() for n in networks_raw.split(",") if n.strip()],
        max_spend_usd=float(_env("X402_MAX_SPEND_USD", "5")),
        buyer_base_sepolia_key_env="X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY",
        dry_run=_truthy(_env("X402_DRY_RUN")),
    )
