from __future__ import annotations

import os
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    WRONG_DESTINATION_TAG = "wrong_destination_tag"
    EXPIRED_QUOTE = "expired_quote"
    UNDERPAYMENT = "underpayment"
    DUPLICATE_PAYMENT_REF = "duplicate_payment_ref"
    WORKER_TIMEOUT = "worker_timeout"
    INVALID_RESULT_REJECTED = "invalid_result_rejected"
    MANUAL_CANCEL_REFUND = "manual_cancel_refund"
    RPC_DISCONNECT = "rpc_disconnect"
    DELAYED_RECEIPT_RETRY = "delayed_receipt_retry"
    HAPPY_PATH = "happy_path"


@dataclass
class FailureConfig:
    enabled: bool
    weights: dict[str, float]
    flags: dict[str, bool]


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _parse_weights() -> dict[str, float]:
    raw = _env("FAILURE_INJECTION_WEIGHTS", "")
    if not raw:
        return {}
    out: dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            try:
                out[k.strip()] = float(v.strip())
            except ValueError:
                pass
    return out


def _parse_flags() -> dict[str, bool]:
    raw = _env("FAILURE_INJECTION_FLAGS", "")
    if not raw:
        return {}
    out: dict[str, bool] = {}
    for part in raw.split(","):
        part = part.strip()
        if part.startswith("!"):
            out[part[1:].strip()] = False
        else:
            out[part.strip()] = True
    return out


def get_failure_config() -> FailureConfig:
    enabled = _env("FAILURE_INJECTION_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
    return FailureConfig(
        enabled=enabled,
        weights=_parse_weights(),
        flags=_parse_flags(),
    )


def should_inject(config: FailureConfig, failure_type: FailureType) -> bool:
    if not config.enabled:
        return False
    if config.flags.get(str(failure_type), False):
        return True
    if config.flags.get(f"!{failure_type}", False) is False:
        return False
    w = config.weights.get(str(failure_type), 0.0)
    return w > 0 and random.random() < w


def select_failure(config: FailureConfig) -> FailureType | None:
    if not config.enabled or not config.weights:
        return FailureType.HAPPY_PATH
    total = sum(config.weights.values())
    if total <= 0:
        return FailureType.HAPPY_PATH
    r = random.random() * total
    for k, v in config.weights.items():
        r -= v
        if r <= 0:
            try:
                return FailureType(k)
            except ValueError:
                return FailureType.HAPPY_PATH
    return FailureType.HAPPY_PATH
