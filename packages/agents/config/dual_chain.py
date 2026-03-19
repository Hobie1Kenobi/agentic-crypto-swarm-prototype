from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from config.chains import get_chain_id, get_explorer_url, get_native_symbol, get_rpc


@dataclass(frozen=True)
class ChainConfig:
    chain_name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    native_symbol: str


_PUBLIC_CHAIN_ID_BY_OLAS_CONFIG: Final[dict[str, int]] = {
    "gnosis": 100,
    "base": 8453,
    "polygon": 137,
    "optimism": 10,
}

_PUBLIC_CHAIN_EXPLORER_BY_OLAS_CONFIG: Final[dict[str, str]] = {
    "gnosis": "https://gnosisscan.io",
    "base": "https://basescan.org",
    "polygon": "https://polygonscan.com",
    "optimism": "https://optimistic.etherscan.io",
}

_PUBLIC_CHAIN_NATIVE_SYMBOL_BY_OLAS_CONFIG: Final[dict[str, str]] = {
    "gnosis": "xDAI",
    "base": "ETH",
    "polygon": "MATIC",
    "optimism": "ETH",
}


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def get_private_chain_config() -> ChainConfig:
    chain_name = _env("PRIVATE_CHAIN_NAME", _env("CHAIN_NAME", "celo-sepolia")).lower()
    chain_id_raw = _env("PRIVATE_CHAIN_ID") or _env("CHAIN_ID")
    chain_id = int(chain_id_raw) if chain_id_raw else get_chain_id()

    rpc_url = _env("PRIVATE_RPC_URL") or _env("RPC_URL") or get_rpc()
    explorer_url = _env("PRIVATE_EXPLORER_URL") or get_explorer_url()
    native_symbol = _env("PRIVATE_NATIVE_SYMBOL") or get_native_symbol()

    return ChainConfig(
        chain_name=chain_name,
        chain_id=chain_id,
        rpc_url=rpc_url,
        explorer_url=explorer_url,
        native_symbol=native_symbol,
    )


def get_public_olas_chain_config() -> ChainConfig:
    # Olas chain selection is driven by `OLAS_CHAIN_CONFIG` (mech-client uses this).
    olas_chain_cfg = _env("OLAS_CHAIN_CONFIG", "gnosis").lower()
    chain_id = int(_env("PUBLIC_OLAS_CHAIN_ID", str(_PUBLIC_CHAIN_ID_BY_OLAS_CONFIG.get(olas_chain_cfg, 0))) or 0)
    if chain_id <= 0:
        # Fall back to known mapping for reporting; if it still can't be determined, keep 0.
        chain_id = _PUBLIC_CHAIN_ID_BY_OLAS_CONFIG.get(olas_chain_cfg, 0)

    explorer_url = _env("PUBLIC_OLAS_EXPLORER_URL") or _PUBLIC_CHAIN_EXPLORER_BY_OLAS_CONFIG.get(olas_chain_cfg, "")
    rpc_url = _env("PUBLIC_OLAS_RPC_URL") or ""
    native_symbol = _env("PUBLIC_OLAS_NATIVE_SYMBOL") or _PUBLIC_CHAIN_NATIVE_SYMBOL_BY_OLAS_CONFIG.get(olas_chain_cfg, "ETH")

    return ChainConfig(
        chain_name=_env("PUBLIC_OLAS_CHAIN_NAME", olas_chain_cfg).lower(),
        chain_id=chain_id,
        rpc_url=rpc_url,
        explorer_url=explorer_url,
        native_symbol=native_symbol,
    )


def get_private_marketplace_address() -> str:
    addr = _env("PRIVATE_MARKETPLACE_ADDRESS") or _env("COMPUTE_MARKETPLACE_ADDRESS")
    return addr


def get_private_revenue_service_address() -> str:
    addr = _env("PRIVATE_REVENUE_SERVICE_ADDRESS") or _env("REVENUE_SERVICE_ADDRESS")
    return addr


def apply_private_chain_env_aliases() -> None:
    """
    Best-effort: keep legacy modules working by mapping PRIVATE_* -> CHAIN_*.
    This repo uses many existing helpers that read CHAIN_ID/RPC_URL globals.
    """
    cfg = get_private_chain_config()
    os.environ.setdefault("CHAIN_NAME", cfg.chain_name)
    os.environ.setdefault("CHAIN_ID", str(cfg.chain_id))
    os.environ.setdefault("RPC_URL", cfg.rpc_url)

