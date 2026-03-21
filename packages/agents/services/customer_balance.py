from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from services.customer_balance_stub import CustomerBalanceCredit


def _db_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    p = os.getenv("CUSTOMER_BALANCE_DB_PATH", "").strip()
    if p:
        path = Path(p)
        return path if path.is_absolute() else root / p
    return root / "customer_balances.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customer_balances (
            customer_id TEXT PRIMARY KEY,
            balance_wei INTEGER NOT NULL DEFAULT 0,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS balance_credits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            amount_wei INTEGER NOT NULL,
            asset TEXT NOT NULL,
            source TEXT NOT NULL,
            external_ref TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customer_balances(customer_id)
        );
        CREATE TABLE IF NOT EXISTS balance_debits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            amount_wei INTEGER NOT NULL,
            service TEXT NOT NULL,
            task_id INTEGER,
            created_at REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customer_balances(customer_id)
        );
        CREATE TABLE IF NOT EXISTS metering (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            amount_wei INTEGER NOT NULL,
            metadata_json TEXT,
            created_at REAL NOT NULL
        );
    """)
    conn.commit()
    return conn


def get_balance(customer_id: str) -> int:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT balance_wei FROM customer_balances WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def credit(
    customer_id: str,
    amount_wei: int,
    asset: str = "XRP",
    source: str = "xrpl",
    external_ref: str | None = None,
) -> bool:
    if amount_wei <= 0:
        return False
    conn = _connect()
    try:
        now = time.time()
        conn.execute(
            """
            INSERT INTO customer_balances (customer_id, balance_wei, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                balance_wei = balance_wei + excluded.balance_wei,
                updated_at = excluded.updated_at
            """,
            (customer_id, amount_wei, now),
        )
        conn.execute(
            "INSERT INTO balance_credits (customer_id, amount_wei, asset, source, external_ref, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (customer_id, amount_wei, asset, source, external_ref or "", now),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def debit(customer_id: str, amount_wei: int, service: str = "task_execution", task_id: int | None = None) -> bool:
    if amount_wei <= 0:
        return False
    conn = _connect()
    try:
        row = conn.execute("SELECT balance_wei FROM customer_balances WHERE customer_id = ?", (customer_id,)).fetchone()
        current = int(row[0]) if row else 0
        if current < amount_wei:
            return False
        now = time.time()
        conn.execute(
            "UPDATE customer_balances SET balance_wei = balance_wei - ?, updated_at = ? WHERE customer_id = ?",
            (amount_wei, now, customer_id),
        )
        conn.execute(
            "INSERT INTO balance_debits (customer_id, amount_wei, service, task_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (customer_id, amount_wei, service, task_id, now),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def credit_from_xrpl_receipt(
    receipt: dict[str, Any],
    customer_id: str = "default",
    xrp_to_wei: int | None = None,
) -> CustomerBalanceCredit | None:
    from services.customer_balance_stub import credit_from_xrpl_receipt as stub_credit
    cred = stub_credit(receipt, customer_id)
    if cred is None:
        return None
    raw_amount = receipt.get("amount", "0")
    try:
        amount_val = float(raw_amount) if isinstance(raw_amount, str) else float(raw_amount)
    except (ValueError, TypeError):
        return cred
    asset = (receipt.get("payment_asset") or cred.asset or "XRP").strip().upper()
    if xrp_to_wei is None:
        xrp_to_wei = _xrp_to_wei()
    if asset == "RLUSD":
        amount_wei = _rlusd_to_wei(amount_val)
    else:
        amount_wei = int(amount_val * xrp_to_wei)
    if amount_wei <= 0:
        return cred
    credit(customer_id, amount_wei, asset, cred.source, cred.external_ref)
    return cred


def _xrp_to_wei() -> int:
    val = os.getenv("PRICING_XRP_TO_WEI", "").strip()
    if val.isdigit():
        return int(val)
    eth_per_xrp = float(os.getenv("PRICING_XRP_TO_ETH", "0.01"))
    return int(eth_per_xrp * 1e18)


def _rlusd_to_wei(amount: Any) -> int:
    val = os.getenv("PRICING_RLUSD_TO_WEI", "").strip()
    if val.isdigit():
        raw = float(amount) if isinstance(amount, str) else float(amount)
        return int(raw * 1e6 * int(val) / 1e6)
    eth_per_rlusd = float(os.getenv("PRICING_RLUSD_TO_ETH", "0.01"))
    raw = float(amount) if isinstance(amount, str) else float(amount)
    return int(raw * 1e6 * eth_per_rlusd * 1e18 / 1e6)


def budget_enforcement_check(customer_id: str, amount_wei: int) -> bool:
    return get_balance(customer_id) >= amount_wei


def metering_record(service: str, customer_id: str, amount: int, metadata: dict[str, Any] | None = None) -> None:
    import json
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO metering (service, customer_id, amount_wei, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (service, customer_id, amount, json.dumps(metadata or {}), time.time()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()
