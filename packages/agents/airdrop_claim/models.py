from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ClaimStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"


class ClaimSpec(BaseModel):
    """Executable EVM call. You (or tooling) must supply correct calldata for the distributor contract."""

    chain_id: int = Field(..., description="EIP-155 chain id")
    to: str = Field(..., description="Contract to call (checksum or hex)")
    data: str = Field(..., description="0x-prefixed calldata")
    value_wei: int = Field(0, ge=0)
    signer_role: str = Field("AIRDROP_CLAIMANT", description="Role name for SimpleSignerAgentExecutor / env *_PRIVATE_KEY")
    label: str = ""
    source_url: str = ""
    notes: str = ""
    gas_limit: int | None = Field(None, description="Optional cap; otherwise estimate with route max_gas")

    @field_validator("to")
    @classmethod
    def _addr(cls, v: str) -> str:
        s = (v or "").strip()
        if not s.startswith("0x") or len(s) != 42:
            raise ValueError("to must be a 0x-prefixed 20-byte address")
        return s

    @field_validator("data")
    @classmethod
    def _data(cls, v: str) -> str:
        s = (v or "").strip()
        if not s.startswith("0x"):
            raise ValueError("data must be 0x-prefixed hex")
        return s


class ClaimRecord(BaseModel):
    id: str
    status: ClaimStatus
    spec: ClaimSpec
    created_at: str
    updated_at: str
    approved_at: str | None = None
    approved_by: str | None = None
    rejected_reason: str | None = None
    tx_hash: str | None = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
