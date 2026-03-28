from __future__ import annotations

import json
import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class ChainRoute(BaseModel):
    rpc_env_vars: list[str] = Field(
        default_factory=lambda: ["RPC_URL"],
        description="Try each env name in order until a non-empty RPC URL is found",
    )
    signer_role: str = "AIRDROP_CLAIMANT"
    expected_signer_env: str | None = Field(
        None,
        description="If set, must match the signer address derived from the role key (e.g. AIRDROP_CLAIM_WALLET_ADDRESS)",
    )
    explorer_url: str | None = Field(
        None,
        description="Block explorer base URL for this chain (tx link = explorer + /tx/ + hash)",
    )
    allowed_contracts: list[str] = Field(
        default_factory=list,
        description="If non-empty, `to` must be in this list (lowercase). If empty, execution is blocked unless AIRDROP_CLAIM_ALLOW_UNLISTED=1",
    )
    max_gas: int = 600_000
    max_value_wei: int = 0

    model_config = {"extra": "ignore"}

    @field_validator("max_value_wei", mode="before")
    @classmethod
    def _coerce_max_val(cls, v: object) -> int:
        if isinstance(v, bool):
            raise ValueError("max_value_wei must be an integer")
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return 0
            if s.isdigit():
                return int(s)
        return int(v)  # type: ignore[arg-type]


class RoutingConfig(BaseModel):
    version: int = 1
    routes: dict[str, ChainRoute] = Field(default_factory=dict)

    def route_for_chain(self, chain_id: int) -> ChainRoute | None:
        key = str(chain_id)
        return self.routes.get(key)


def _root() -> Path:
    p = Path(__file__).resolve().parents[3]
    for _ in range(6):
        if (p / "foundry.toml").exists() or (p / ".env.example").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[3]


def default_routing_path() -> Path:
    return _root() / "packages" / "agents" / "config" / "airdrop_claim_routing.json"


def load_routing(path: Path | None = None) -> RoutingConfig:
    env_p = os.getenv("AIRDROP_CLAIM_ROUTING_JSON", "").strip()
    if path is not None:
        pp = Path(path)
    elif env_p:
        pp = Path(env_p)
    else:
        pp = default_routing_path()
    if not pp.is_file():
        return RoutingConfig()
    data = json.loads(pp.read_text(encoding="utf-8"))
    routes_raw = data.get("routes") or {}
    norm: dict[str, ChainRoute] = {}
    for k, v in routes_raw.items():
        if isinstance(v, dict):
            norm[str(k)] = ChainRoute.model_validate(v)
    return RoutingConfig(version=int(data.get("version", 1)), routes=norm)


def resolve_rpc_url(route: ChainRoute) -> str:
    for key in route.rpc_env_vars:
        val = os.getenv(key, "").strip()
        if val and "your_" not in val.lower():
            return val
    return ""


def execution_enabled() -> bool:
    return os.getenv("AIRDROP_CLAIM_EXECUTION_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def allow_unlisted_contracts() -> bool:
    return os.getenv("AIRDROP_CLAIM_ALLOW_UNLISTED", "").strip().lower() in {"1", "true", "yes", "on"}


def contract_allowed(route: ChainRoute, to_addr: str) -> bool:
    from web3 import Web3

    to_l = Web3.to_checksum_address(to_addr).lower()
    allowed = [Web3.to_checksum_address(a).lower() for a in (route.allowed_contracts or [])]
    if allowed:
        return to_l in allowed
    return allow_unlisted_contracts()
