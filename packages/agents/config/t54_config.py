"""
T54 XRPL x402 adapter config — env-driven mainnet/testnet/local mode.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

T54Mode = Literal["mainnet", "testnet", "local"]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class T54XRPLConfig:
    enabled: bool
    mode: T54Mode
    facilitator_url: str
    network: str
    network_passphrase: str
    require_validated: bool
    wallet_seed: str
    wallet_address: str
    receiver_address: str
    allow_simulated_testnet: bool
    default_currency: str
    timeout_ms: int
    dry_run: bool


def get_t54_xrpl_config() -> T54XRPLConfig:
    mode_raw = _env("T54_XRPL_MODE", "testnet").strip().lower()
    if mode_raw not in {"mainnet", "testnet", "local"}:
        mode_raw = "testnet"
    mode: T54Mode = mode_raw

    facilitator = _env("T54_XRPL_FACILITATOR_URL", "")
    if mode == "mainnet" and not facilitator:
        facilitator = "https://xrpl-facilitator-mainnet.t54.ai"

    network_raw = _env("T54_XRPL_NETWORK", mode if mode != "local" else "testnet").strip().lower()
    network = "mainnet" if network_raw == "mainnet" else "testnet"

    passphrase = _env(
        "T54_XRPL_NETWORK_PASSPHRASE",
        "XRP Ledger Testnet; December 2019" if network == "testnet" else "XRP Ledger Main Network",
    )

    timeout_s = _env("T54_XRPL_TIMEOUT_MS", "30000")
    try:
        timeout_ms = int(timeout_s) if timeout_s else 30000
    except ValueError:
        timeout_ms = 30000

    return T54XRPLConfig(
        enabled=_truthy(_env("T54_XRPL_ENABLED")),
        mode=mode,
        facilitator_url=facilitator,
        network=network,
        network_passphrase=passphrase,
        require_validated=_truthy(_env("T54_XRPL_REQUIRE_VALIDATED")),
        wallet_seed=_env("T54_XRPL_WALLET_SEED", _env("XRPL_WALLET_SEED", "")),
        wallet_address=_env("T54_XRPL_WALLET_ADDRESS", ""),
        receiver_address=_env("T54_XRPL_RECEIVER_ADDRESS", _env("XRPL_RECEIVER_ADDRESS", "")),
        allow_simulated_testnet=_truthy(_env("T54_XRPL_ALLOW_SIMULATED_TESTNET")),
        default_currency=_env("T54_XRPL_DEFAULT_CURRENCY", "XRP").strip().upper(),
        timeout_ms=timeout_ms,
        dry_run=_truthy(_env("T54_XRPL_DRY_RUN")),
    )


def t54_testnet_blocked_reason(cfg: T54XRPLConfig) -> str | None:
    if cfg.mode != "testnet":
        return None
    if not cfg.facilitator_url:
        return "testnet_facilitator_unavailable"
    if "mainnet" in cfg.facilitator_url.lower() and "testnet" not in cfg.facilitator_url.lower():
        return "testnet_mode_but_mainnet_facilitator_configured"
    if "testnet" in cfg.facilitator_url.lower():
        return None
    return None
