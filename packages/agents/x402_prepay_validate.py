"""Reject missing or invalid paid-SKU input before x402 settlement."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from fastapi.responses import JSONResponse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_EVM_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")
DEMO_PACK_ID = "demo"


def intake_resale_dir() -> Path:
    # packages/agents/x402_prepay_validate.py -> repo root / artifacts / intake_resale
    return Path(__file__).resolve().parents[2] / "artifacts" / "intake_resale"


def evm_address_from_params(params: Any) -> str:
    for key in ("contractAddress", "address", "contract_address"):
        raw = (params.get(key) if params is not None else None) or ""
        val = str(raw).strip()
        if _EVM_ADDR.fullmatch(val):
            return val
    return ""


def pack_file(pack_id: str) -> Path:
    return intake_resale_dir() / f"{pack_id}.json"


def prepay_validate_x402(request) -> JSONResponse | None:
    """Return a free 400/503 JSONResponse, or None to continue to payment middleware."""
    path = request.url.path
    q = request.query_params

    if path == "/x402/v1/intake-resale":
        pid = (q.get("pack_id") or "").strip()
        if not pid:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "pack_id_required",
                    "message": "Missing required query parameter pack_id. This request was not charged.",
                    "hint": "GET /x402/v1/intake-resale?pack_id=<id>",
                    "example": f"/x402/v1/intake-resale?pack_id={DEMO_PACK_ID}",
                },
            )
        path_file = pack_file(pid)
        if not path_file.is_file():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "pack_not_found",
                    "message": f"No intake pack exists for pack_id={pid}. This request was not charged.",
                    "pack_id": pid,
                    "hint": f"Pass a minted pack_id, or use the public demo: ?pack_id={DEMO_PACK_ID}",
                    "example": f"/x402/v1/intake-resale?pack_id={DEMO_PACK_ID}",
                },
            )
        return None

    if path == "/x402/v1/contract-triage":
        addr = evm_address_from_params(q)
        if not addr:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "missing_or_invalid_contractAddress",
                    "message": (
                        "Missing or invalid contract address. Pass ?contractAddress=0x… "
                        "(40 hex chars). Alias: address. This request was not charged."
                    ),
                    "hint": "GET /x402/v1/contract-triage?contractAddress=0x…&chainId=eip155:8453",
                    "example": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                },
            )
        try:
            from marketplace.skus.smart_contract_audit import triage_contract  # noqa: F401
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "triage_engine_unavailable",
                    "message": "Triage engine is unavailable. This request was not charged.",
                    "detail": str(exc)[:200],
                },
            )
        return None

    return None
