from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

PaymentRailMode = Literal["mock_payment", "xrpl_x402_payment", "direct_onchain_celo_payment", "hybrid_public_request_xrpl_payment_private_celo_settlement"]
XRPLPaymentMode = Literal["live", "mock", "replay"]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GeneralConfig:
    market_mode: str
    payment_rail_mode: str
    report_output_dir: str


@dataclass(frozen=True)
class CeloPrivateConfig:
    chain_name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    marketplace_address: str
    revenue_service_address: str


@dataclass(frozen=True)
class XRPLConfig:
    enabled: bool
    network: str
    rpc_url: str
    receiver_address: str
    settlement_asset: str
    x402_enabled: bool
    x402_facilitator_url: str
    payment_mode: XRPLPaymentMode


@dataclass(frozen=True)
class OlasConfig:
    enabled: bool
    chain_config: str
    priority_mech_address: str
    tool: str
    mechx_path: str


def get_market_mode() -> str:
    return _env("MARKET_MODE", "private_celo").strip().lower() or "private_celo"


def get_payment_rail_mode() -> str:
    return _env("PAYMENT_RAIL_MODE", "").strip().lower() or "direct_onchain_celo_payment"


def get_report_output_dir() -> str:
    return _env("REPORT_OUTPUT_DIR", "").strip()


def get_general_config() -> GeneralConfig:
    return GeneralConfig(
        market_mode=get_market_mode(),
        payment_rail_mode=get_payment_rail_mode(),
        report_output_dir=get_report_output_dir(),
    )


def get_celo_private_config() -> CeloPrivateConfig:
    from config.dual_chain import get_private_chain_config, get_private_marketplace_address, get_private_revenue_service_address
    cfg = get_private_chain_config()
    return CeloPrivateConfig(
        chain_name=cfg.chain_name,
        chain_id=cfg.chain_id,
        rpc_url=cfg.rpc_url or "",
        explorer_url=cfg.explorer_url or "",
        marketplace_address=get_private_marketplace_address() or "",
        revenue_service_address=get_private_revenue_service_address() or "",
    )


def get_xrpl_config() -> XRPLConfig:
    mode = _env("XRPL_PAYMENT_MODE", "mock").strip().lower()
    if mode not in {"live", "mock", "replay"}:
        mode = "mock"
    return XRPLConfig(
        enabled=_truthy(_env("XRPL_ENABLED")),
        network=_env("XRPL_NETWORK", "testnet"),
        rpc_url=_env("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234"),
        receiver_address=_env("XRPL_RECEIVER_ADDRESS", ""),
        settlement_asset=_env("XRPL_SETTLEMENT_ASSET", "XRP"),
        x402_enabled=_truthy(_env("XRPL_X402_ENABLED")),
        x402_facilitator_url=_env("XRPL_X402_FACILITATOR_URL", ""),
        payment_mode=mode,
    )


def get_olas_config() -> OlasConfig:
    return OlasConfig(
        enabled=_truthy(_env("OLAS_ENABLED")),
        chain_config=_env("OLAS_CHAIN_CONFIG", "gnosis"),
        priority_mech_address=_env("OLAS_PRIORITY_MECH_ADDRESS", ""),
        tool=_env("OLAS_TOOL", "openai-gpt-4o-2024-05-13"),
        mechx_path=_env("OLAS_MECHX_PATH", ""),
    )
