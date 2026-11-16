from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_lock = threading.Lock()


def _db_path() -> Path:
    raw = (os.getenv("CONTRACT_MONITOR_DB") or "").strip()
    if raw:
        return Path(raw)
    root = Path(__file__).resolve().parents[2]
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    return data / "contract_monitor.sqlite3"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_db_path()), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                addresses_json TEXT NOT NULL,
                webhook_url TEXT NOT NULL,
                thresholds_json TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        c.commit()


@dataclass
class Subscription:
    id: str
    addresses: list[str]
    webhook_url: str
    thresholds: dict[str, Any]
    expires_at: float
    status: str


def create_subscription(
    addresses: list[str],
    webhook_url: str,
    thresholds: dict[str, Any] | None,
    duration_days: int,
) -> Subscription:
    init_db()
    sid = str(uuid.uuid4())
    now = time.time()
    dur = max(1, min(int(duration_days or 30), 365))
    expires = now + dur * 86400
    thr = thresholds or {}
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO subscriptions (id, addresses_json, webhook_url, thresholds_json, expires_at, created_at, status) VALUES (?,?,?,?,?,?,?)",
                (
                    sid,
                    json.dumps(addresses[:10]),
                    webhook_url[:2048],
                    json.dumps(thr),
                    expires,
                    now,
                    "active",
                ),
            )
            c.commit()
    return Subscription(
        id=sid,
        addresses=addresses[:10],
        webhook_url=webhook_url,
        thresholds=thr,
        expires_at=expires,
        status="active",
    )


def list_active() -> list[Subscription]:
    init_db()
    now = time.time()
    with _lock:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM subscriptions WHERE status = 'active' AND expires_at > ?",
                (now,),
            ).fetchall()
    out: list[Subscription] = []
    for r in rows:
        out.append(
            Subscription(
                id=r["id"],
                addresses=json.loads(r["addresses_json"]),
                webhook_url=r["webhook_url"],
                thresholds=json.loads(r["thresholds_json"]),
                expires_at=r["expires_at"],
                status=r["status"],
            )
        )
    return out
