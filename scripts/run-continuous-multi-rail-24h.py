#!/usr/bin/env python3
"""
Continuous 24-hour multi-rail soak test.

Runs every 15 minutes for 24 hours (96 cycles):
- XRPL testnet: real machine payment
- Celo Sepolia: real task lifecycle + settlement
- Olas intake: mocked (not live)

Usage:
  python scripts/run-continuous-multi-rail-24h.py

Produces:
  - continuous_multi_rail_24h_report.json
  - continuous_multi_rail_24h_report.md
  - continuous_multi_rail_metrics_summary.md
  - trace_archive_24h/cycle_NNNN_communication_trace.{json,md}
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from scripts.soak_test_runner import (
    INTERVAL_SECONDS,
    OLAS_BOUNDARY,
    compute_summary,
    run_cycle,
    snapshot_config,
    ts,
    write_metrics_summary,
)

DURATION_HOURS = 24
TOTAL_CYCLES = (DURATION_HOURS * 60) // 15

OUT_DIR = root
CYCLE_LOG_JSON = OUT_DIR / "continuous_multi_rail_24h_cycle_log.json"
CYCLE_LOG_MD = OUT_DIR / "continuous_multi_rail_24h_cycle_log.md"
REPORT_JSON = OUT_DIR / "continuous_multi_rail_24h_report.json"
REPORT_MD = OUT_DIR / "continuous_multi_rail_24h_report.md"
METRICS_MD = OUT_DIR / "continuous_multi_rail_metrics_summary.md"
FAILURES_JSON = OUT_DIR / "continuous_multi_rail_24h_failures.json"
TRACE_ARCHIVE_DIR = OUT_DIR / "trace_archive_24h"
CHECKPOINT_6H = OUT_DIR / "continuous_multi_rail_24h_6h_checkpoint.md"
CHECKPOINT_12H = OUT_DIR / "continuous_multi_rail_24h_12h_checkpoint.md"
CHECKPOINT_18H = OUT_DIR / "continuous_multi_rail_24h_18h_checkpoint.md"


def load_cycle_log() -> list[dict]:
    if CYCLE_LOG_JSON.exists():
        try:
            return json.loads(CYCLE_LOG_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_cycle_log(cycles: list[dict]) -> None:
    CYCLE_LOG_JSON.write_text(json.dumps(cycles, indent=2), encoding="utf-8")
    lines = [
        "# Continuous Multi-Rail 24h Cycle Log",
        "",
        f"Generated: {ts()}",
        f"Total cycles: {len(cycles)}",
        "",
        "| Cycle | Start | End | Status | XRPL Tx | Task ID | Celo Txs |",
        "|-------|-------|-----|--------|---------|---------|----------|",
    ]
    for c in cycles:
        xrpl_tx = (c.get("xrpl_tx_hash") or "")[:16] + "..." if c.get("xrpl_tx_hash") else "-"
        lines.append(
            f"| {c.get('cycle', '?')} | {c.get('start_time', '')} | {c.get('end_time', '')} | "
            f"{c.get('status', '')} | {xrpl_tx} | {c.get('internal_task_id', '-')} | {len(c.get('celo_tx_hashes') or [])} |"
        )
    CYCLE_LOG_MD.write_text("\n".join(lines), encoding="utf-8")


def load_failures() -> list[dict]:
    if FAILURES_JSON.exists():
        try:
            return json.loads(FAILURES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_failures(failures: list[dict]) -> None:
    FAILURES_JSON.write_text(json.dumps(failures, indent=2), encoding="utf-8")


def write_checkpoint(summary: dict, path: Path, label: str) -> None:
    lines = [
        f"# 24h Soak Test — {label} Checkpoint",
        "",
        f"Generated: {ts()}",
        "",
        f"- Cycles: {summary.get('total_cycles_completed', 0)}/{summary.get('total_cycles_attempted', 0)}",
        f"- Success rate: {summary.get('success_rate', 0)}%",
        f"- XRPL txs: {summary.get('total_xrpl_txs', 0)}",
        f"- Celo txs: {summary.get('total_celo_txs', 0)}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print(f"[{ts()}] Starting 24-hour continuous multi-rail soak test ({TOTAL_CYCLES} cycles, every 15 min)")
    print(f"[{ts()}] Olas intake: {OLAS_BOUNDARY} (mocked)")
    locked_config = snapshot_config()
    print(f"[{ts()}] Locked config for entire run: marketplace={locked_config.get('COMPUTE_MARKETPLACE_ADDRESS') or locked_config.get('PRIVATE_MARKETPLACE_ADDRESS') or 'N/A'}")
    cycles = load_cycle_log()
    failures = load_failures()
    loop_start = time.time()

    for cycle_num in range(TOTAL_CYCLES):
        cycle_start = time.time()
        print(f"[{ts()}] Cycle {cycle_num + 1}/{TOTAL_CYCLES} starting...")
        record = run_cycle(cycle_num, OUT_DIR, TRACE_ARCHIVE_DIR, locked_config)
        cycles.append(record)
        save_cycle_log(cycles)

        if record.get("status") == "failed":
            failures.append({"cycle": cycle_num, "time": ts(), "errors": record.get("errors"), "stage": "run"})
            save_failures(failures)
            print(f"[{ts()}] Cycle {cycle_num + 1} FAILED: {record.get('errors')}")
        else:
            print(f"[{ts()}] Cycle {cycle_num + 1} OK: XRPL={str(record.get('xrpl_tx_hash', ''))[:16]}... task={record.get('internal_task_id')}")

        elapsed = time.time() - loop_start
        for h, path in [(6, CHECKPOINT_6H), (12, CHECKPOINT_12H), (18, CHECKPOINT_18H)]:
            if elapsed >= h * 3600 and not path.exists():
                summary = compute_summary(cycles)
                write_checkpoint(summary, path, f"{h}h")
                print(f"[{ts()}] {h}h checkpoint written")

        if cycle_num < TOTAL_CYCLES - 1:
            sleep_for = max(0, INTERVAL_SECONDS - (time.time() - cycle_start))
            if sleep_for > 0:
                print(f"[{ts()}] Sleeping {int(sleep_for)}s until next cycle...")
                time.sleep(sleep_for)

    summary = compute_summary(cycles)
    write_metrics_summary(summary, METRICS_MD, "24h soak test")

    report = {
        "report_type": "continuous_multi_rail_24h",
        "generated_at": ts(),
        "duration_hours": DURATION_HOURS,
        "interval_minutes": 15,
        "expected_cycles": TOTAL_CYCLES,
        "olas_boundary": OLAS_BOUNDARY,
        "summary": summary,
        "top_failure_causes": dict(
            sorted((summary.get("failure_count_by_category") or {}).items(), key=lambda x: -x[1])[:5]
        ),
        "strongest_evidence": [
            {"cycle": c.get("cycle"), "xrpl_tx_hash": c.get("xrpl_tx_hash"), "internal_task_id": c.get("internal_task_id")}
            for c in cycles
            if c.get("status") == "completed" and c.get("xrpl_tx_hash")
        ][-5:],
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_lines = [
        "# Continuous Multi-Rail 24-Hour Report",
        "",
        f"Generated: {ts()}",
        "",
        "## Summary",
        "",
        f"- Total cycles attempted: {summary.get('total_cycles_attempted', 0)}",
        f"- Total cycles completed: {summary.get('total_cycles_completed', 0)}",
        f"- Success rate: {summary.get('success_rate', 0)}%",
        f"- Total XRPL txs: {summary.get('total_xrpl_txs', 0)}",
        f"- Total Celo txs: {summary.get('total_celo_txs', 0)}",
        f"- Total XRP paid: {summary.get('total_xrp_paid', 0)}",
        f"- Average cycle duration: {summary.get('average_cycle_duration_seconds', 0)}s",
        "",
        "## Settlement Totals",
        "",
        f"- Protocol fee: {summary.get('total_protocol_fee_wei', 0)} wei",
        f"- Finance fee: {summary.get('total_finance_fee_wei', 0)} wei",
        f"- Worker payout: {summary.get('total_worker_payout_wei', 0)} wei",
        f"- Requester refund: {summary.get('total_requester_refund_wei', 0)} wei",
        "",
        "## Olas Intake",
        "",
        f"Boundary: `{OLAS_BOUNDARY}` (mocked)",
        "",
        "## Artifacts",
        "",
        "- continuous_multi_rail_24h_report.json",
        "- continuous_multi_rail_24h_report.md",
        "- continuous_multi_rail_metrics_summary.md",
        "- trace_archive_24h/cycle_NNNN_communication_trace.{json,md}",
        "",
    ]
    REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[{ts()}] 24h soak test complete. Summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
