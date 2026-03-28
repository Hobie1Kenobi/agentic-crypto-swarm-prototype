"""
T54 XRPL reconciliation records — machine-readable payment attempt artifacts.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERIFICATION_STATUSES = (
    "real_t54_xrpl_payment",
    "simulated_t54_xrpl_testnet",
    "testnet_facilitator_unavailable",
    "payment_failed_pre_submit",
    "facilitator_verify_failed",
    "facilitator_settle_failed",
    "local_dev_only",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_attempts_path() -> Path:
    return _repo_root() / "external_commerce_data" / "t54-xrpl-payment-attempts.jsonl"


class T54ReconciliationRecord:
    def __init__(
        self,
        payment_attempt_id: str = "",
        mode: str = "",
        facilitator_url: str = "",
        network: str = "",
        wallet_address: str = "",
        receiver_address: str = "",
        quote_id: str = "",
        invoice_id: str = "",
        destination_tag: int | None = None,
        memo_ref: str = "",
        amount_xrp: str = "",
        amount_drops: str = "",
        signed_blob_present: bool = False,
        submit_status: str = "",
        verify_status: str = "",
        settle_status: str = "",
        xrpl_tx_hash: str | None = None,
        ledger_index: int | None = None,
        validated: bool = False,
        error_type: str = "",
        error_message: str = "",
        created_at: str = "",
        completed_at: str = "",
        verification_status: str = "",
        reason: str = "",
        facilitator_response: str = "",
    ):
        self.payment_attempt_id = payment_attempt_id or str(uuid.uuid4().hex[:16])
        self.mode = mode
        self.facilitator_url = facilitator_url
        self.network = network
        self.wallet_address = wallet_address
        self.receiver_address = receiver_address
        self.quote_id = quote_id
        self.invoice_id = invoice_id
        self.destination_tag = destination_tag
        self.memo_ref = memo_ref
        self.amount_xrp = amount_xrp
        self.amount_drops = amount_drops
        self.signed_blob_present = signed_blob_present
        self.submit_status = submit_status
        self.verify_status = verify_status
        self.settle_status = settle_status
        self.xrpl_tx_hash = xrpl_tx_hash
        self.ledger_index = ledger_index
        self.validated = validated
        self.error_type = error_type
        self.error_message = error_message
        self.created_at = created_at or _ts()
        self.completed_at = completed_at or _ts()
        self.verification_status = verification_status
        self.reason = reason
        self.facilitator_response = facilitator_response

    def to_dict(self) -> dict[str, Any]:
        return {
            "payment_attempt_id": self.payment_attempt_id,
            "mode": self.mode,
            "facilitator_url": self.facilitator_url,
            "network": self.network,
            "wallet_address": self.wallet_address,
            "receiver_address": self.receiver_address,
            "quote_id": self.quote_id,
            "invoice_id": self.invoice_id,
            "destination_tag": self.destination_tag,
            "memo_ref": self.memo_ref,
            "amount_xrp": self.amount_xrp,
            "amount_drops": self.amount_drops,
            "signed_blob_present": self.signed_blob_present,
            "submit_status": self.submit_status,
            "verify_status": self.verify_status,
            "settle_status": self.settle_status,
            "xrpl_tx_hash": self.xrpl_tx_hash,
            "ledger_index": self.ledger_index,
            "validated": self.validated,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "verification_status": self.verification_status,
            "reason": self.reason,
            "facilitator_response": self.facilitator_response,
        }


class T54ReconciliationStore:
    def __init__(self, path: Path | None = None):
        self._path = path or _default_attempts_path()

    def append(self, record: T54ReconciliationRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)

    def load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        out = []
        for line in self._path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return out
