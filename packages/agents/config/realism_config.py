from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RUN_MODE_BASELINE = "baseline"
RUN_MODE_REALISM = "realism"


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass
class ActorSpec:
    id: str
    role_type: str
    funding_address: str | None
    payout_address: str
    refund_address: str | None


def is_realism_mode() -> bool:
    return _env("RUN_MODE", RUN_MODE_BASELINE).strip().lower() == RUN_MODE_REALISM


def get_realism_seed() -> int | None:
    s = _env("REALISM_SEED", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _load_actor_config() -> list[dict[str, Any]]:
    path = _env("REALISM_ACTORS_JSON", "")
    if path:
        p = Path(path)
        if p.is_absolute() and p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        pr = _root() / path
        if pr.exists():
            return json.loads(pr.read_text(encoding="utf-8"))
    default = _root() / "packages" / "agents" / "config" / "realism_actors.json"
    if default.exists():
        return json.loads(default.read_text(encoding="utf-8"))
    return []


AGENT_ENV_KEYS = {
    "ROOT_STRATEGIST": "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR": "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER": "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR": "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
    "TREASURY": "TREASURY_PRIVATE_KEY",
}


def _role_addr(role: str) -> str:
    key = f"{role}_ADDRESS"
    addr = _env(key, "")
    if addr:
        return addr
    key_priv = AGENT_ENV_KEYS.get(role, f"{role}_PRIVATE_KEY")
    from eth_account import Account
    pk = os.getenv(key_priv) or (os.getenv("WORKER_PRIVATE_KEY") if role == "IP_GENERATOR" else None) or (os.getenv("VALIDATOR_PRIVATE_KEY") if role == "DEPLOYER" else None) or os.getenv("PRIVATE_KEY")
    if pk:
        return Account.from_key(pk).address
    return ""


def get_actors_from_env() -> dict[str, list[ActorSpec]]:
    requesters: list[ActorSpec] = []
    workers: list[ActorSpec] = []
    validators: list[ActorSpec] = []
    roles = ["ROOT_STRATEGIST", "IP_GENERATOR", "DEPLOYER", "FINANCE_DISTRIBUTOR", "TREASURY"]
    for i, r in enumerate(roles):
        addr = _role_addr(r)
        if not addr:
            continue
        if r in ("ROOT_STRATEGIST", "IP_GENERATOR", "DEPLOYER"):
            requesters.append(ActorSpec(f"requester-{i+1}", "requester", addr, addr, addr))
        if r in ("IP_GENERATOR", "DEPLOYER", "FINANCE_DISTRIBUTOR", "TREASURY"):
            workers.append(ActorSpec(f"worker-{i+1}", "worker", None, addr, None))
        if r in ("DEPLOYER", "FINANCE_DISTRIBUTOR"):
            validators.append(ActorSpec(f"validator-{i+1}", "validator", None, addr, None))
    return {
        "requesters": requesters[:3] or [ActorSpec("requester-1", "requester", "0x0", "0x0", "0x0")],
        "workers": workers[:4] or [ActorSpec("worker-1", "worker", None, "0x0", None)],
        "validators": validators[:2] or [ActorSpec("validator-1", "validator", None, "0x0", None)],
    }
