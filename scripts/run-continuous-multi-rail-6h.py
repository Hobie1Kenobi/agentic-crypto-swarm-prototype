#!/usr/bin/env python3
"""
Continuous 6-hour multi-rail testnet loop.

Runs every 15 minutes for 6 hours (24 cycles):
- XRPL testnet: real machine payment
- Celo Sepolia: real task lifecycle + settlement
- Olas intake: mocked (not live)

Usage:
  python scripts/run-continuous-multi-rail-6h.py

Env (must be set for live XRPL + Celo):
  PAYMENT_RAIL_MODE=hybrid_public_request_xrpl_payment_private_celo_settlement
  XRPL_ENABLED=1
  XRPL_PAYMENT_MODE=live
  MARKET_MODE=hybrid
  XRPL_WALLET_SEED, XRPL_RECEIVER_ADDRESS, Celo keys, etc.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)

os.environ["PAYMENT_RAIL_MODE"] = "hybrid_public_request_xrpl_payment_private_celo_settlement"
os.environ["XRPL_ENABLED"] = "1"
os.environ["XRPL_PAYMENT_MODE"] = "live"
os.environ["MARKET_MODE"] = "hybrid"

TASK_TEMPLATES = [
    "Summarize in one sentence: What is one ethical use of AI?",
    "Classify: Is sustainable compute usage beneficial? Answer yes or no.",
    "Short answer: What is agentic commerce in one phrase?",
]

WORKER_METADATAS = ["swarm-worker-1", "swarm-worker-2"]

DURATION_HOURS = 6
INTERVAL_MINUTES = 15
INTERVAL_SECONDS = INTERVAL_MINUTES * 60
TOTAL_CYCLES = (DURATION_HOURS * 60) // INTERVAL_MINUTES

OUT_DIR = root / "artifacts" / "reports"
CYCLE_LOG_JSON = OUT_DIR / "continuous_multi_rail_cycle_log.json"
CYCLE_LOG_MD = OUT_DIR / "continuous_multi_rail_cycle_log.md"
REPORT_JSON = OUT_DIR / "continuous_multi_rail_6h_report.json"
REPORT_MD = OUT_DIR / "continuous_multi_rail_6h_report.md"
FAILURES_JSON = OUT_DIR / "continuous_multi_rail_failures.json"
CHECKPOINT_2H = OUT_DIR / "continuous_multi_rail_2h_checkpoint.md"
CHECKPOINT_4H = OUT_DIR / "continuous_multi_rail_4h_checkpoint.md"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cycle_log() -> list[dict]:
    if CYCLE_LOG_JSON.exists():
        try:
            return json.loads(CYCLE_LOG_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_cycle_log(cycles: list[dict]) -> None:
    CYCLE_LOG_JSON.write_text(json.dumps(cycles, indent=2), encoding="utf-8")
    lines = [
        "# Continuous Multi-Rail Cycle Log",
        "",
        f"Generated: {_ts()}",
        f"Total cycles: {len(cycles)}",
        "",
        "| Cycle | Start | End | Status | Task | XRPL Tx | Task ID | Celo Txs |",
        "|-------|-------|-----|--------|------|---------|---------|----------|",
    ]
    for c in cycles:
        xrpl_tx = (c.get("xrpl_tx_hash") or "")[:16] + "..." if c.get("xrpl_tx_hash") else "-"
        task_id = c.get("internal_task_id", "-")
        celo_count = len(c.get("celo_tx_hashes") or [])
        lines.append(
            f"| {c.get('cycle', '?')} | {c.get('start_time', '')} | {c.get('end_time', '')} | "
            f"{c.get('status', '')} | {str(c.get('task_template', ''))[:30]}... | {xrpl_tx} | {task_id} | {celo_count} |"
        )
    CYCLE_LOG_MD.write_text("\n".join(lines), encoding="utf-8")


def _load_failures() -> list[dict]:
    if FAILURES_JSON.exists():
        try:
            return json.loads(FAILURES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_failures(failures: list[dict]) -> None:
    FAILURES_JSON.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def _run_one_cycle(cycle_num: int) -> dict:
    prompt = TASK_TEMPLATES[cycle_num % len(TASK_TEMPLATES)]
    worker = WORKER_METADATAS[cycle_num % len(WORKER_METADATAS)]
    os.environ["COMPUTE_WORKER_METADATA"] = worker
    os.environ["COMPUTE_MINER_METADATA"] = worker

    start_time = _ts()
    start_ts = time.time()
    record: dict = {
        "cycle": cycle_num,
        "start_time": start_time,
        "task_template": prompt,
        "worker_metadata": worker,
        "payment_rail": "xrpl",
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
        record["end_time"] = _ts()
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

        ok = result.get("ok") and private.get("ok")
        payment_boundary = result.get("payment_boundary", "")
        if payment_boundary != "real_xrpl_payment":
            record["warnings"].append(f"XRPL boundary was {payment_boundary}, not real_xrpl_payment")
        if not ok:
            record["errors"].append(str(private.get("errors") or result.get("public_response", {}).get("notes") or "unknown"))
        record["status"] = "completed" if ok else "failed"
        return record
    except Exception as e:
        record["end_time"] = _ts()
        record["elapsed_seconds"] = round(time.time() - start_ts, 2)
        record["errors"].append(str(e))
        record["status"] = "failed"
        return record


def _compute_summary(cycles: list[dict]) -> dict:
    completed = [c for c in cycles if c.get("status") == "completed"]
    failed = [c for c in cycles if c.get("status") == "failed"]
    xrpl_verified = [c for c in completed if c.get("xrpl_verification") == "real_xrpl_payment"]
    total_xrp = sum(float(c.get("xrpl_amount") or 0) for c in completed if c.get("xrpl_amount"))
    total_celo_txs = sum(len(c.get("celo_tx_hashes") or []) for c in completed)
    elapsed_list = [c.get("elapsed_seconds") for c in completed if c.get("elapsed_seconds") is not None]
    avg_settlement = sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0

    protocol_fee = 0
    finance_fee = 0
    worker_payout = 0
    requester_refund = 0
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
            elif cat == "requester_refund":
                requester_refund += w

    failure_causes: dict[str, int] = {}
    for f in failed:
        err = "; ".join(f.get("errors") or ["unknown"])
        failure_causes[err[:80]] = failure_causes.get(err[:80], 0) + 1

    return {
        "total_cycles_attempted": len(cycles),
        "total_cycles_completed": len(completed),
        "total_cycles_failed": len(failed),
        "total_xrpl_payments_verified": len(xrpl_verified),
        "total_celo_tasks_finalized": len(completed),
        "total_xrpl_tx_count": len(xrpl_verified),
        "total_celo_tx_count": total_celo_txs,
        "total_xrp_paid": round(total_xrp, 6),
        "total_protocol_fee_wei": protocol_fee,
        "total_finance_fee_wei": finance_fee,
        "total_worker_payout_wei": worker_payout,
        "total_refunds_wei": requester_refund,
        "average_settlement_seconds": round(avg_settlement, 2),
        "failure_count_by_category": failure_causes,
        "success_rate": round(len(completed) / len(cycles) * 100, 1) if cycles else 0,
    }


def _write_checkpoint(summary: dict, cycles: list[dict], path: Path, label: str) -> None:
    lines = [
        f"# Continuous Multi-Rail {label} Checkpoint",
        "",
        f"Generated: {_ts()}",
        "",
        "## Summary",
        "",
        f"- Cycles attempted: {summary.get('total_cycles_attempted', 0)}",
        f"- Cycles completed: {summary.get('total_cycles_completed', 0)}",
        f"- Cycles failed: {summary.get('total_cycles_failed', 0)}",
        f"- Success rate: {summary.get('success_rate', 0)}%",
        f"- XRPL payments verified: {summary.get('total_xrpl_payments_verified', 0)}",
        f"- Celo tasks finalized: {summary.get('total_celo_tasks_finalized', 0)}",
        f"- Total XRP paid: {summary.get('total_xrp_paid', 0)}",
        f"- Average settlement time: {summary.get('average_settlement_seconds', 0)}s",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_final_report(summary: dict, cycles: list[dict]) -> None:
    report = {
        "report_type": "continuous_multi_rail_6h",
        "generated_at": _ts(),
        "duration_hours": DURATION_HOURS,
        "interval_minutes": INTERVAL_MINUTES,
        "expected_cycles": TOTAL_CYCLES,
        "summary": summary,
        "top_failure_causes": dict(
            sorted(
                (summary.get("failure_count_by_category") or {}).items(),
                key=lambda x: -x[1],
            )[:5]
        ),
        "strongest_evidence": [
            {
                "cycle": c.get("cycle"),
                "xrpl_tx_hash": c.get("xrpl_tx_hash"),
                "internal_task_id": c.get("internal_task_id"),
                "celo_tx_count": len(c.get("celo_tx_hashes") or []),
            }
            for c in cycles
            if c.get("status") == "completed" and c.get("xrpl_tx_hash")
        ][-5:],
        "recommendation": "Consider 12h or 24h soak test if stability holds; or increase frequency to 10min if 15min shows no issues.",
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Continuous Multi-Rail 6-Hour Report",
        "",
        f"Generated: {_ts()}",
        "",
        "## Final Output",
        "",
        f"1. Total cycles attempted: {summary.get('total_cycles_attempted', 0)}",
        f"2. Total successful cycles: {summary.get('total_cycles_completed', 0)}",
        f"3. Total failed cycles: {summary.get('total_cycles_failed', 0)}",
        f"4. XRPL tx total: {summary.get('total_xrpl_tx_count', 0)}",
        f"5. Celo tx total: {summary.get('total_celo_tx_count', 0)}",
        f"6. Total value paid on XRPL: {summary.get('total_xrp_paid', 0)} XRP",
        f"7. Total value settled on Celo: protocol={summary.get('total_protocol_fee_wei', 0)} wei, finance={summary.get('total_finance_fee_wei', 0)} wei, worker={summary.get('total_worker_payout_wei', 0)} wei, refund={summary.get('total_refunds_wei', 0)} wei",
        f"8. Average settlement time: {summary.get('average_settlement_seconds', 0)}s",
        f"9. Top failure causes: {report.get('top_failure_causes', {})}",
        f"10. Strongest evidence (last 5): {report.get('strongest_evidence', [])}",
        f"11. Recommendation: {report.get('recommendation', '')}",
        "",
        "## Artifacts",
        "",
        "- artifacts/reports/continuous_multi_rail_cycle_log.json",
        "- artifacts/reports/continuous_multi_rail_cycle_log.md",
        "- artifacts/reports/continuous_multi_rail_6h_report.json",
        "- artifacts/reports/continuous_multi_rail_6h_report.md",
        "- artifacts/reports/continuous_multi_rail_failures.json",
        "- artifacts/reports/continuous_multi_rail_2h_checkpoint.md",
        "- artifacts/reports/continuous_multi_rail_4h_checkpoint.md",
        "- artifacts/communication/communication_trace.json",
        "- artifacts/communication/communication_trace.md",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[{_ts()}] Starting 6-hour continuous multi-rail loop ({TOTAL_CYCLES} cycles, every {INTERVAL_MINUTES} min)")
    cycles = _load_cycle_log()
    failures = _load_failures()
    loop_start = time.time()

    for cycle_num in range(TOTAL_CYCLES):
        cycle_start = time.time()
        print(f"[{_ts()}] Cycle {cycle_num + 1}/{TOTAL_CYCLES} starting...")
        record = _run_one_cycle(cycle_num)
        cycles.append(record)
        _save_cycle_log(cycles)

        if record.get("status") == "failed":
            failures.append(
                {
                    "cycle": cycle_num,
                    "time": _ts(),
                    "errors": record.get("errors"),
                    "stage": "run",
                }
            )
            _save_failures(failures)
            print(f"[{_ts()}] Cycle {cycle_num + 1} FAILED: {record.get('errors')}")
        else:
            print(f"[{_ts()}] Cycle {cycle_num + 1} OK: XRPL={record.get('xrpl_tx_hash', '')[:16]}... task={record.get('internal_task_id')}")

        elapsed = time.time() - loop_start
        if elapsed >= 2 * 3600 and not CHECKPOINT_2H.exists():
            summary = _compute_summary(cycles)
            _write_checkpoint(summary, cycles, CHECKPOINT_2H, "2h")
            print(f"[{_ts()}] 2h checkpoint written")
        if elapsed >= 4 * 3600 and not CHECKPOINT_4H.exists():
            summary = _compute_summary(cycles)
            _write_checkpoint(summary, cycles, CHECKPOINT_4H, "4h")
            print(f"[{_ts()}] 4h checkpoint written")

        if cycle_num < TOTAL_CYCLES - 1:
            sleep_for = max(0, INTERVAL_SECONDS - (time.time() - cycle_start))
            if sleep_for > 0:
                print(f"[{_ts()}] Sleeping {int(sleep_for)}s until next cycle...")
                time.sleep(sleep_for)

    summary = _compute_summary(cycles)
    _write_final_report(summary, cycles)
    print(f"[{_ts()}] 6h loop complete. Summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
