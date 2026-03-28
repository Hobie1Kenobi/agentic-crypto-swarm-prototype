from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT_DB = "reconciliation.db"


def _db_path() -> Path:
    p = os.getenv("RECONCILIATION_DB_PATH", "").strip()
    if p:
        return Path(p)
    root = Path(__file__).resolve().parents[3]
    return root / _DEFAULT_DB


@dataclass
class ReconciliationRecord:
    job_id: str
    quote_id: str
    xrpl_tx_hash: str
    destination_tag: int | None
    memo_ref: str | None
    delivered_amount: str
    celo_task_id: int | None
    disposition: str
    celo_tx_hashes: list[dict[str, Any]] = field(default_factory=list)
    payout_refund: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "quote_id": self.quote_id,
            "xrpl_tx_hash": self.xrpl_tx_hash,
            "destination_tag": self.destination_tag,
            "memo_ref": self.memo_ref,
            "delivered_amount": self.delivered_amount,
            "celo_task_id": self.celo_task_id,
            "celo_tx_hashes": self.celo_tx_hashes,
            "payout_refund": self.payout_refund,
            "disposition": self.disposition,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reconciliation (
            xrpl_tx_hash TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            quote_id TEXT NOT NULL,
            destination_tag INTEGER,
            memo_ref TEXT,
            delivered_amount TEXT,
            celo_task_id INTEGER,
            celo_tx_hashes TEXT,
            payout_refund TEXT,
            disposition TEXT NOT NULL,
            created_at REAL,
            updated_at REAL,
            metadata TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_reconciliation_job ON reconciliation(job_id);
        CREATE INDEX IF NOT EXISTS idx_reconciliation_quote ON reconciliation(quote_id);
        CREATE INDEX IF NOT EXISTS idx_reconciliation_celo_task ON reconciliation(celo_task_id);
    """)


def _get_conn() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def external_payment_ref(xrpl_tx_hash: str) -> str:
    return (xrpl_tx_hash or "").strip().lower()


def is_settled(external_ref: str) -> bool:
    ref = external_payment_ref(external_ref)
    if not ref:
        return False
    with _get_conn() as c:
        row = c.execute(
            "SELECT disposition FROM reconciliation WHERE xrpl_tx_hash = ?",
            (ref,),
        ).fetchone()
        if not row:
            return False
        return row["disposition"] in ("settled", "refunded", "cancelled", "expired")


def get_by_external_ref(external_ref: str) -> ReconciliationRecord | None:
    ref = external_payment_ref(external_ref)
    if not ref:
        return None
    with _get_conn() as c:
        row = c.execute("SELECT * FROM reconciliation WHERE xrpl_tx_hash = ?", (ref,)).fetchone()
        if not row:
            return None
        return _row_to_record(row)


def _row_to_record(row: sqlite3.Row) -> ReconciliationRecord:
    celo_tx = row["celo_tx_hashes"]
    payout = row["payout_refund"]
    meta = row["metadata"]
    return ReconciliationRecord(
        job_id=str(row["job_id"] or ""),
        quote_id=str(row["quote_id"] or ""),
        xrpl_tx_hash=str(row["xrpl_tx_hash"] or ""),
        destination_tag=int(row["destination_tag"]) if row["destination_tag"] is not None else None,
        memo_ref=str(row["memo_ref"]) if row["memo_ref"] else None,
        delivered_amount=str(row["delivered_amount"] or ""),
        celo_task_id=int(row["celo_task_id"]) if row["celo_task_id"] is not None else None,
        disposition=str(row["disposition"] or ""),
        celo_tx_hashes=json.loads(celo_tx) if celo_tx else [],
        payout_refund=json.loads(payout) if payout else None,
        created_at=float(row["created_at"] or 0),
        updated_at=float(row["updated_at"] or 0),
        metadata=json.loads(meta) if meta else None,
    )


def record_payment_pending(
    xrpl_tx_hash: str,
    job_id: str,
    quote_id: str,
    destination_tag: int | None = None,
    memo_ref: str | None = None,
    delivered_amount: str = "",
) -> bool:
    ref = external_payment_ref(xrpl_tx_hash)
    if not ref:
        return False
    now = time.time()
    with _get_conn() as c:
        try:
            c.execute(
                """
                INSERT INTO reconciliation (
                    xrpl_tx_hash, job_id, quote_id, destination_tag, memo_ref,
                    delivered_amount, disposition, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (ref, job_id, quote_id, destination_tag, memo_ref, delivered_amount, now, now),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def record_settlement(
    xrpl_tx_hash: str,
    celo_task_id: int,
    celo_tx_hashes: list[dict[str, Any]],
    payout_refund: dict[str, Any] | None = None,
    disposition: str = "settled",
) -> bool:
    ref = external_payment_ref(xrpl_tx_hash)
    if not ref:
        return False
    now = time.time()
    with _get_conn() as c:
        cur = c.execute(
            """
            UPDATE reconciliation
            SET celo_task_id = ?, celo_tx_hashes = ?, payout_refund = ?,
                disposition = ?, updated_at = ?
            WHERE xrpl_tx_hash = ? AND disposition = 'pending'
            """,
            (celo_task_id, json.dumps(celo_tx_hashes), json.dumps(payout_refund or {}), disposition, now, ref),
        )
        return cur.rowcount > 0


def record_failure(
    xrpl_tx_hash: str,
    disposition: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    ref = external_payment_ref(xrpl_tx_hash)
    if not ref:
        return False
    now = time.time()
    with _get_conn() as c:
        cur = c.execute(
            """
            UPDATE reconciliation
            SET disposition = ?, metadata = ?, updated_at = ?
            WHERE xrpl_tx_hash = ? AND disposition = 'pending'
            """,
            (disposition, json.dumps(metadata or {}), now, ref),
        )
        if cur.rowcount > 0:
            return True
        try:
            c.execute(
                """
                INSERT INTO reconciliation (
                    xrpl_tx_hash, job_id, quote_id, disposition, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ref, ref, ref, disposition, now, now, json.dumps(metadata or {})),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def claim_for_settlement(xrpl_tx_hash: str) -> bool:
    ref = external_payment_ref(xrpl_tx_hash)
    if not ref:
        return False
    with _get_conn() as c:
        row = c.execute(
            "SELECT disposition FROM reconciliation WHERE xrpl_tx_hash = ?",
            (ref,),
        ).fetchone()
        if not row:
            return True
        return row["disposition"] == "pending"
