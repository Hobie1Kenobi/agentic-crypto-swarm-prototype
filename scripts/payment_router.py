#!/usr/bin/env python3
"""
Smart hybrid settlement for x402 swarm. Routes:
- Testnet: Faucet path (no bridge); optionally try Celo facilitator first
- Mainnet: Celo facilitator first (pay from Celo USDC); fallback to LI.FI bridge
Uses only Celo + XRPL wallets from .env.
"""
from __future__ import annotations

import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if (root / ".env").exists():
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=True)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def get_celo_facilitator(is_testnet: bool) -> str:
    if is_testnet:
        return _env("X402_FACILITATOR_TESTNET", "https://x402.org/facilitator")
    return _env("X402_FACILITATOR_MAINNET", "https://facilitator.ultravioletadao.xyz")


def get_celo_network(is_testnet: bool) -> str:
    return "eip155:11142220" if is_testnet else "eip155:42220"


def has_celo_facilitator_support(provider_id: str, providers_config: list | None = None) -> bool:
    if not providers_config:
        return False
    for p in providers_config:
        pid = p.get("provider_id", p.get("id", ""))
        if pid == provider_id:
            meta = p.get("metadata", {}) or {}
            return meta.get("settlement_chain") == "celo" or meta.get("celo_native") is True
    return False


def route_payment(
    provider_id: str,
    is_testnet: bool,
    amount: float = 0.05,
    facilitator_first: bool = True,
) -> dict:
    """
    Route payment for x402 provider. Testnet -> faucet; mainnet -> Celo facilitator or bridge.
    Returns {path, facilitator_url?, network?, bridged?, error?}.
    """
    use_facilitator = _truthy(_env("X402_USE_FACILITATOR", "1"))
    bridge_enabled = _truthy(_env("X402_BRIDGE_ENABLED", "1"))
    dry_run = _truthy(_env("X402_DRY_RUN"))

    if dry_run:
        return {"path": "dry_run", "skipped": True}

    if is_testnet:
        sys_path = str(root / "scripts")
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        try:
            from bridge_utils import ensure_base_sepolia_test_usdc
            r = ensure_base_sepolia_test_usdc(min_usdc=amount)
            fac = get_celo_facilitator(True)
            net = get_celo_network(True)
            return {
                "path": "faucet",
                "facilitator_url": fac,
                "network": get_celo_network(True),
                "faucet_result": r,
            }
        except ImportError:
            return {"path": "faucet", "error": "bridge_utils not found", "facilitator_url": get_celo_facilitator(True), "network": get_celo_network(True)}

    if facilitator_first and use_facilitator:
        fac = get_celo_facilitator(False)
        net = get_celo_network(False)
        return {"path": "celo_facilitator", "facilitator_url": fac, "network": net}

    if bridge_enabled:
        sys_path = str(root / "scripts")
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        try:
            from bridge_utils import ensure_base_usdc_for_x402
            br = ensure_base_usdc_for_x402(is_testnet=False, min_usdc=amount)
            return {
                "path": "bridge",
                "bridged": br.get("ok"),
                "bridge_result": br,
                "facilitator_url": get_celo_facilitator(False),
                "network": "eip155:8453",
            }
        except ImportError:
            pass

    return {"path": "direct", "facilitator_url": get_celo_facilitator(False), "network": "eip155:8453"}
