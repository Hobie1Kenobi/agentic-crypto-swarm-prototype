"""
Validate XRPL classic addresses and discovery hit records (no secrets).
"""
from __future__ import annotations

import re
from typing import Any

try:
    from xrpl.core import addresscodec

    def is_valid_classic_address(addr: str) -> bool:
        s = (addr or "").strip()
        if not s:
            return False
        try:
            return bool(addresscodec.is_valid_classic_address(s))
        except Exception:
            return False

except Exception:

    def is_valid_classic_address(addr: str) -> bool:
        s = (addr or "").strip()
        return bool(re.match(r"^r[1-9A-HJ-NP-Za-km-z]{25,34}$", s))


def validate_discovery_hit(record: dict[str, Any]) -> list[str]:
    """Return list of human-readable issues; empty means OK for downstream use."""
    errs: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a dict"]
    res = record.get("resource")
    if not res or not isinstance(res, str):
        errs.append("missing resource URL")
    for key in ("wallet_hint", "pay_to"):
        v = record.get(key)
        if v and isinstance(v, str) and v.startswith("r") and not is_valid_classic_address(v):
            errs.append(f"invalid classic address in {key}")
    return errs


def validate_env_wallet_hint(addr: str | None) -> tuple[bool, str]:
    """Optional: validate XRPL_RECEIVER_ADDRESS / T54 address from env."""
    if not addr or not str(addr).strip():
        return True, ""
    a = str(addr).strip()
    if a.startswith("r"):
        ok = is_valid_classic_address(a)
        return (ok, "" if ok else "invalid XRPL classic address")
    return True, ""
