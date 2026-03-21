"""
Shared soak-test runner for continuous multi-rail loops.

Supports 6h and 24h runs at 15-minute intervals.
- Archives communication traces per cycle
- Produces metrics summary
- Olas intake: explicitly mocked
"""
from __future__ import annotations

import json
import os
import sys
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

root = Path(__file__).resolve().parents[1]
sys_path_inserted = False


def _ensure_path() -> None:
    global sys_path_inserted
    if not sys_path_inserted:
        sys.path.insert(0, str(root / "packages" / "agents"))
        sys_path_inserted = True


TASK_TEMPLATES = [
    "Summarize in one sentence: What is one ethical use of AI?",
    "Classify: Is sustainable compute usage beneficial? Answer yes or no.",
    "Short answer: What is agentic commerce in one phrase?",
]

WORKER_METADATAS = ["swarm-worker-1", "swarm-worker-2"]

INTERVAL_MINUTES = 15
INTERVAL_SECONDS = INTERVAL_MINUTES * 60

OLAS_BOUNDARY = "mocked_external_replay"

CRITICAL_ENV_KEYS = [
    "COMPUTE_MARKETPLACE_ADDRESS",
    "PRIVATE_MARKETPLACE_ADDRESS",
    "PRIVATE_RPC_URL",
    "RPC_URL",
    "CHAIN_ID",
    "PRIVATE_CHAIN_ID",
    "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
    "TREASURY_PRIVATE_KEY",
    "XRPL_WALLET_SEED",
    "XRPL_RECEIVER_ADDRESS",
    "XRPL_RPC_URL",
]


def snapshot_config() -> dict[str, str]:
    """Load .env once and snapshot critical vars. Use for entire soak run to avoid mid-run config drift."""
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=True)
    return {k: (os.getenv(k) or "").strip() for k in CRITICAL_ENV_KEYS if os.getenv(k)}


def apply_locked_config(locked: dict[str, str]) -> None:
    """Re-apply locked config to os.environ so cycles use consistent values."""
    for k, v in locked.items():
        if v:
            os.environ[k] = v


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cycle(
    cycle_num: int,
    out_dir: Path,
    trace_archive_dir: Path,
    locked_config: dict[str, str] | None = None,
) -> dict:
    _ensure_path()
    if locked_config:
        apply_locked_config(locked_config)
    else:
        from dotenv import load_dotenv
        load_dotenv(root / ".env", override=True)

    os.environ["PAYMENT_RAIL_MODE"] = "hybrid_public_request_xrpl_payment_private_celo_settlement"
    os.environ["XRPL_ENABLED"] = "1"
    os.environ["XRPL_PAYMENT_MODE"] = "live"
    os.environ["MARKET_MODE"] = "hybrid"

    prompt = TASK_TEMPLATES[cycle_num % len(TASK_TEMPLATES)]
    worker = WORKER_METADATAS[cycle_num % len(WORKER_METADATAS)]
    os.environ["COMPUTE_WORKER_METADATA"] = worker
    os.environ["COMPUTE_MINER_METADATA"] = worker

    start_time = ts()
    start_ts = time.time()
    record: dict = {
        "cycle": cycle_num,
        "start_time": start_time,
        "task_template": prompt,
        "worker_metadata": worker,
        "worker_payout_address": None,
        "payment_rail": "xrpl",
        "olas_boundary": OLAS_BOUNDARY,
        "status": "unknown",
        "xrpl_tx_hash": None,
        "xrpl_amount": None,
        "xrpl_verification": None,
        "internal_task_id": None,
        "celo_tx_hashes": [],
        "task_final_status": None,
        "settlement": {},
        "elapsed_seconds": None,
        "errors": [],
        "warnings": [],
    }

    try:
        from services.multi_rail_hybrid import run_multi_rail_hybrid_demo

        result = run_multi_rail_hybrid_demo(prompt, force_hybrid=True)
        end_ts = time.time()
        record["end_time"] = ts()
        record["elapsed_seconds"] = round(end_ts - start_ts, 2)

        xrpl = result.get("xrpl_payment") or {}
        private = result.get("private_market_report") or {}
        task = private.get("task") or {}
        settlement = task.get("settlement") or {}
        by_cat = settlement.get("by_category") or {}

        record["xrpl_tx_hash"] = xrpl.get("tx_hash") or xrpl.get("external_payment_id")
        record["xrpl_amount"] = xrpl.get("amount", "1")
        record["xrpl_verification"] = xrpl.get("verification_boundary", "")
        record["internal_task_id"] = task.get("task_id")
        record["celo_tx_hashes"] = [t.get("tx_hash") for t in private.get("tx_hashes") or [] if t.get("tx_hash")]
        record["task_final_status"] = (task.get("task_status") or {}).get("name", "")
        record["settlement"] = {
            cat: {"address": d.get("address"), "expected_wei": d.get("expected_wei")}
            for cat, d in by_cat.items()
        }
        wp = by_cat.get("worker_payout", {})
        record["worker_payout_address"] = wp.get("address")

        ok = result.get("ok") and private.get("ok")
        payment_boundary = result.get("payment_boundary", "")
        if payment_boundary != "real_xrpl_payment":
            record["warnings"].append(f"XRPL boundary was {payment_boundary}, not real_xrpl_payment")
        if not ok:
            record["errors"].append(
                str(private.get("errors") or result.get("public_response", {}).get("notes") or "unknown")
            )
        record["status"] = "completed" if ok else "failed"

        trace_archive_dir.mkdir(parents=True, exist_ok=True)
        for name in ["communication_trace.json", "communication_trace.md"]:
            src = out_dir / name
            if src.exists():
                dst = trace_archive_dir / f"cycle_{cycle_num:04d}_{name}"
                shutil.copy2(src, dst)

        return record
    except Exception as e:
        record["end_time"] = ts()
        record["elapsed_seconds"] = round(time.time() - start_ts, 2)
        record["errors"].append(str(e))
        record["status"] = "failed"
        return record


def compute_summary(cycles: list[dict]) -> dict:
    completed = [c for c in cycles if c.get("status") == "completed"]
    failed = [c for c in cycles if c.get("status") == "failed"]
    xrpl_verified = [c for c in completed if c.get("xrpl_verification") == "real_xrpl_payment"]
    total_xrp = sum(float(c.get("xrpl_amount") or 0) for c in completed if c.get("xrpl_amount"))
    total_celo_txs = sum(len(c.get("celo_tx_hashes") or []) for c in completed)
    elapsed_list = [c.get("elapsed_seconds") for c in completed if c.get("elapsed_seconds") is not None]
    avg_duration = sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0

    protocol_fee = 0
    finance_fee = 0
    worker_payout = 0
    requester_refund = 0
    worker_payout_by_address: dict[str, int] = {}
    for c in completed:
        s = c.get("settlement") or {}
        for cat, d in s.items():
            w = d.get("expected_wei") or 0
            if cat == "protocol_fee":
                protocol_fee += w
            elif cat == "finance_fee":
                finance_fee += w
            elif cat == "worker_payout":
                worker_payout += w
                addr = d.get("address") or c.get("worker_payout_address") or "unknown"
                worker_payout_by_address[addr] = worker_payout_by_address.get(addr, 0) + w
            elif cat == "requester_refund":
                requester_refund += w

    failure_causes: dict[str, int] = {}
    for f in failed:
        err = "; ".join(f.get("errors") or ["unknown"])
        failure_causes[err[:80]] = failure_causes.get(err[:80], 0) + 1

    return {
        "total_xrpl_txs": len(xrpl_verified),
        "total_celo_txs": total_celo_txs,
        "total_xrpl_tx_count": len(xrpl_verified),
        "total_celo_tx_count": total_celo_txs,
        "total_cycles_attempted": len(cycles),
        "total_cycles_completed": len(completed),
        "total_cycles_failed": len(failed),
        "success_rate": round(len(completed) / len(cycles) * 100, 1) if cycles else 0,
        "average_cycle_duration_seconds": round(avg_duration, 2),
        "average_settlement_seconds": round(avg_duration, 2),
        "total_protocol_fee_wei": protocol_fee,
        "total_finance_fee_wei": finance_fee,
        "total_worker_payout_wei": worker_payout,
        "total_requester_refund_wei": requester_refund,
        "total_refunds_wei": requester_refund,
        "total_xrp_paid": round(total_xrp, 6),
        "total_xrpl_payments_verified": len(xrpl_verified),
        "total_celo_tasks_finalized": len(completed),
        "failure_count_by_category": failure_causes,
        "worker_payout_by_address": worker_payout_by_address,
    }


def write_metrics_summary(summary: dict, path: Path, run_label: str) -> None:
    lines = [
        "# Continuous Multi-Rail Metrics Summary",
        "",
        f"Run: {run_label} | Generated: {ts()}",
        "",
        "## Core Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total XRPL txs | {summary.get('total_xrpl_txs', 0)} |",
        f"| Total Celo txs | {summary.get('total_celo_txs', 0)} |",
        f"| Total cycles attempted | {summary.get('total_cycles_attempted', 0)} |",
        f"| Total cycles completed | {summary.get('total_cycles_completed', 0)} |",
        f"| Success rate | {summary.get('success_rate', 0)}% |",
        f"| Average cycle duration | {summary.get('average_cycle_duration_seconds', 0)}s |",
        "",
        "## Settlement Totals (wei)",
        "",
        "| Category | Total |",
        "|----------|-------|",
        f"| Protocol fee | {summary.get('total_protocol_fee_wei', 0)} |",
        f"| Finance fee | {summary.get('total_finance_fee_wei', 0)} |",
        f"| Worker payout | {summary.get('total_worker_payout_wei', 0)} |",
        f"| Requester refund | {summary.get('total_requester_refund_wei', 0)} |",
        "",
        f"| Total XRP paid | {summary.get('total_xrp_paid', 0)} |",
        "",
        "## Worker Payout by Address",
        "",
    ]
    for addr, wei in (summary.get("worker_payout_by_address") or {}).items():
        lines.append(f"- `{addr}`: {wei} wei")
    if not (summary.get("worker_payout_by_address")):
        lines.append("- (single worker identity)")
    lines.extend(["", "## Olas Intake", "", f"Boundary: `{OLAS_BOUNDARY}` (mocked)", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
