from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ClaimRecord, ClaimSpec, ClaimStatus


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_db_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    for _ in range(6):
        if (root / "foundry.toml").exists() or (root / ".env.example").exists():
            break
        root = root.parent
    return root / "external_commerce_data" / "airdrop_claim_queue.sqlite"


def get_db_path() -> Path:
    env = os.getenv("AIRDROP_CLAIM_QUEUE_DB", "").strip()
    return Path(env) if env else default_db_path()


class ClaimQueueStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or get_db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, isolation_level=None)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_by TEXT,
                    rejected_reason TEXT,
                    tx_hash TEXT,
                    error TEXT,
                    meta_json TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status)")

    def add_pending(self, spec: ClaimSpec, meta: dict[str, Any] | None = None) -> str:
        cid = str(uuid.uuid4())
        now = _utc_now()
        row = ClaimRecord(
            id=cid,
            status=ClaimStatus.pending_approval,
            spec=spec,
            created_at=now,
            updated_at=now,
            meta=meta or {},
        )
        self._insert(row)
        return cid

    def _insert(self, row: ClaimRecord) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO claims (id, status, spec_json, created_at, updated_at, approved_at, approved_by,
                    rejected_reason, tx_hash, error, meta_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.id,
                    row.status.value,
                    row.spec.model_dump_json(),
                    row.created_at,
                    row.updated_at,
                    row.approved_at,
                    row.approved_by,
                    row.rejected_reason,
                    row.tx_hash,
                    row.error,
                    json.dumps(row.meta, ensure_ascii=False),
                ),
            )

    def get(self, claim_id: str) -> ClaimRecord | None:
        with self._conn() as c:
            cur = c.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
            r = cur.fetchone()
            if not r:
                return None
            desc = cur.description
        return self._row_to_record(r, desc)

    def _row_to_record(self, r: tuple[Any, ...], description: Any) -> ClaimRecord:
        cols = [d[0] for d in (description or [])]
        d = dict(zip(cols, r))
        spec = ClaimSpec.model_validate_json(d["spec_json"])
        meta = json.loads(d["meta_json"] or "{}")
        return ClaimRecord(
            id=d["id"],
            status=ClaimStatus(d["status"]),
            spec=spec,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            approved_at=d.get("approved_at"),
            approved_by=d.get("approved_by"),
            rejected_reason=d.get("rejected_reason"),
            tx_hash=d.get("tx_hash"),
            error=d.get("error"),
            meta=meta if isinstance(meta, dict) else {},
        )

    def list_by_status(self, status: ClaimStatus | None = None, limit: int = 200) -> list[ClaimRecord]:
        with self._conn() as c:
            if status:
                cur = c.execute(
                    "SELECT * FROM claims WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cur = c.execute("SELECT * FROM claims ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            desc = cur.description
        out: list[ClaimRecord] = []
        for r in rows:
            out.append(self._row_to_record(r, desc))
        return out

    def update_status(
        self,
        claim_id: str,
        status: ClaimStatus,
        *,
        approved_by: str | None = None,
        rejected_reason: str | None = None,
        tx_hash: str | None = None,
        error: str | None = None,
    ) -> None:
        row = self.get(claim_id)
        if not row:
            raise KeyError(claim_id)
        now = _utc_now()
        row.status = status
        row.updated_at = now
        if status == ClaimStatus.approved and row.approved_at is None:
            row.approved_at = now
        if approved_by is not None:
            row.approved_by = approved_by
        if rejected_reason is not None:
            row.rejected_reason = rejected_reason
        if tx_hash is not None:
            row.tx_hash = tx_hash
        if error is not None:
            row.error = error
        if status == ClaimStatus.completed:
            row.error = None
        self.set_row(row)

    def set_row(self, row: ClaimRecord) -> None:
        with self._conn() as c:
            c.execute(
                """
                UPDATE claims SET status = ?, updated_at = ?, spec_json = ?, approved_at = ?, approved_by = ?,
                    rejected_reason = ?, tx_hash = ?, error = ?, meta_json = ?
                WHERE id = ?
                """,
                (
                    row.status.value,
                    row.updated_at,
                    row.spec.model_dump_json(),
                    row.approved_at,
                    row.approved_by,
                    row.rejected_reason,
                    row.tx_hash,
                    row.error,
                    json.dumps(row.meta, ensure_ascii=False),
                    row.id,
                ),
            )
