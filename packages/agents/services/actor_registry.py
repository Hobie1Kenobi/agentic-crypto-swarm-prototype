from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

AGENT_ENV_KEYS = {
    "ROOT_STRATEGIST": "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR": "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER": "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR": "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
    "TREASURY": "TREASURY_PRIVATE_KEY",
}

REQUESTER_ROLES = ["ROOT_STRATEGIST", "IP_GENERATOR", "DEPLOYER"]
WORKER_ROLES = ["IP_GENERATOR", "DEPLOYER", "FINANCE_DISTRIBUTOR", "TREASURY"]
VALIDATOR_ROLES = ["DEPLOYER", "FINANCE_DISTRIBUTOR"]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _role_has_key(role: str) -> bool:
    env_key = AGENT_ENV_KEYS.get(role) or f"{role}_PRIVATE_KEY"
    key = _env(env_key)
    if key:
        return True
    if role == "IP_GENERATOR":
        return bool(_env("WORKER_PRIVATE_KEY"))
    if role == "DEPLOYER":
        return bool(_env("VALIDATOR_PRIVATE_KEY"))
    return bool(_env("PRIVATE_KEY"))


def get_requester_roles() -> list[str]:
    custom = _env("REALISM_REQUESTER_ROLES", "").strip()
    if custom:
        return [r.strip() for r in custom.split(",") if r.strip() and _role_has_key(r.strip())]
    return [r for r in REQUESTER_ROLES if _role_has_key(r)]


def get_worker_roles() -> list[str]:
    custom = _env("REALISM_WORKER_ROLES", "").strip()
    if custom:
        return [r.strip() for r in custom.split(",") if r.strip() and _role_has_key(r.strip())]
    return [r for r in WORKER_ROLES if _role_has_key(r)]


def get_validator_roles() -> list[str]:
    custom = _env("REALISM_VALIDATOR_ROLES", "").strip()
    if custom:
        return [r.strip() for r in custom.split(",") if r.strip() and _role_has_key(r.strip())]
    return [r for r in VALIDATOR_ROLES if _role_has_key(r)]


def select_requester(cycle_index: int) -> str:
    roles = get_requester_roles()
    if not roles:
        return "ROOT_STRATEGIST"
    return roles[cycle_index % len(roles)]


def select_worker(cycle_index: int) -> str:
    roles = get_worker_roles()
    if not roles:
        return "IP_GENERATOR"
    return roles[cycle_index % len(roles)]


def select_validator(cycle_index: int) -> str:
    roles = get_validator_roles()
    if not roles:
        return "DEPLOYER"
    return roles[cycle_index % len(roles)]
