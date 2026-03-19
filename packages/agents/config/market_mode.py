from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

MarketMode = Literal["private_celo", "public_olas", "hybrid"]


def get_market_mode() -> MarketMode:
    mode = (os.getenv("MARKET_MODE", "") or "private_celo").strip().lower()
    if mode in {"private", "privatecelo", "celo", "private_celo"}:
        return "private_celo"
    if mode in {"public", "olas", "public_olas"}:
        return "public_olas"
    if mode in {"hybrid"}:
        return "hybrid"
    return "private_celo"


@dataclass(frozen=True)
class MarketFeatures:
    # Whether external/public adapter intake is enabled.
    adapter_enabled: bool
    # Whether the adapter is expected to be live (vs replay/mock).
    olas_live_enabled: bool
    # Whether we expect onchain private settlement via ComputeMarketplace in this mode.
    private_onchain_settlement_enabled: bool


def get_market_features(mode: MarketMode | None = None) -> MarketFeatures:
    mode = mode or get_market_mode()
    # Explicit env override to force "live" attempts (still must be supported by deps/creds).
    olas_live = (os.getenv("OLAS_ENABLED", "") or "").strip().lower() in {"1", "true", "yes", "on"}

    if mode == "private_celo":
        return MarketFeatures(
            adapter_enabled=False,
            olas_live_enabled=False,
            private_onchain_settlement_enabled=True,
        )
    if mode == "public_olas":
        return MarketFeatures(
            adapter_enabled=True,
            olas_live_enabled=olas_live,
            private_onchain_settlement_enabled=False,
        )
    # hybrid
    return MarketFeatures(
        adapter_enabled=True,
        olas_live_enabled=olas_live,
        private_onchain_settlement_enabled=True,
    )

