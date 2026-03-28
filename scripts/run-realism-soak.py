#!/usr/bin/env python3
"""
Market realism soak test.

Multi-actor concurrency, quote-driven XRPL ingress, reconciliation, proof bundle.
Runs for configurable duration (default 6h) at 15-min intervals.

Env:
  REALISM_DURATION_HOURS=6
  XRPL_QUOTE_DRIVEN=1
  RECONCILIATION_ENABLED=1
  FAILURE_INJECTION_ENABLED=0
  REALISM_MAX_CYCLES=24  (overrides duration)

Usage:
  python scripts/run-realism-soak.py
  python scripts/run-realism-soak.py --duration 2 --cycles 8
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from scripts.soak_test_runner import (
    INTERVAL_SECONDS,
    compute_summary,
    run_cycle,
    snapshot_config,
    ts,
)

DURATION_HOURS = int(os.getenv("REALISM_DURATION_HOURS", "6"))
MAX_CYCLES = int(os.getenv("REALISM_MAX_CYCLES", "0")) or (DURATION_HOURS * 60) // 15

OUT_DIR = root / "artifacts"
REPORT_JSON = root / "artifacts" / "reports" / "realism_soak_report.json"
REPORT_MD = root / "artifacts" / "reports" / "realism_soak_report.md"
CYCLE_LOG_JSON = root / "artifacts" / "reports" / "realism_soak_cycle_log.json"
TRACE_ARCHIVE_DIR = root / "artifacts" / "traces" / "realism"


def main() -> int:
    (root / "artifacts" / "reports").mkdir(parents=True, exist_ok=True)
    TRACE_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RUN_MODE", "realism")
    os.environ.setdefault("XRPL_QUOTE_DRIVEN", "1")
    os.environ.setdefault("RECONCILIATION_ENABLED", "1")
    os.environ.setdefault("PAYMENT_RAIL_MODE", "hybrid_public_request_xrpl_payment_private_celo_settlement")
    os.environ.setdefault("XRPL_ENABLED", "1")
    os.environ.setdefault("XRPL_PAYMENT_MODE", "live")
    os.environ.setdefault("MARKET_MODE", "hybrid")
    os.environ.setdefault("OLAS_BOUNDARY", "mocked_external_replay")

    print(f"[{ts()}] Starting market realism soak ({MAX_CYCLES} cycles, every 15 min)")
    print(f"[{ts()}] Quote-driven XRPL: enabled | Reconciliation: enabled | Multi-actor: from registry")
    locked_config = snapshot_config()
    print(f"[{ts()}] Locked config: marketplace={locked_config.get('COMPUTE_MARKETPLACE_ADDRESS') or locked_config.get('PRIVATE_MARKETPLACE_ADDRESS') or 'N/A'}")

    cycles: list[dict] = []
    run_id = str(int(time.time()))
    run_label = f"realism_{MAX_CYCLES}cycles"

    for cycle_num in range(MAX_CYCLES):
        cycle_start = time.time()
        print(f"[{ts()}] Cycle {cycle_num + 1}/{MAX_CYCLES} starting...")
        record = run_cycle(cycle_num, root / "artifacts" / "reports", TRACE_ARCHIVE_DIR, locked_config)
        cycles.append(record)

        if record.get("status") == "failed":
            print(f"[{ts()}] Cycle {cycle_num + 1} FAILED: {record.get('errors')}")
        else:
            print(f"[{ts()}] Cycle {cycle_num + 1} OK: XRPL={str(record.get('xrpl_tx_hash', ''))[:16]}... task={record.get('internal_task_id')}")

        out = [c.get("realism_cycle", c) for c in cycles]
        CYCLE_LOG_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

        if cycle_num < MAX_CYCLES - 1:
            sleep_for = max(0, INTERVAL_SECONDS - (time.time() - cycle_start))
            if sleep_for > 0:
                time.sleep(sleep_for)

    summary = compute_summary(cycles)
    try:
        from services.proof_bundle import write_proof_bundle
        cycle_records = [c.get("realism_cycle", c) for c in cycles]
        bundle_dir = write_proof_bundle(OUT_DIR, run_id, run_label, cycle_records, summary)
        print(f"[{ts()}] Proof bundle written to {bundle_dir}")
    except ImportError:
        pass

    report = {
        "report_type": "market_realism_soak",
        "run_id": run_id,
        "run_label": run_label,
        "generated_at": ts(),
        "max_cycles": MAX_CYCLES,
        "summary": summary,
        "config": {
            "xrpl_quote_driven": os.getenv("XRPL_QUOTE_DRIVEN"),
            "reconciliation_enabled": os.getenv("RECONCILIATION_ENABLED"),
        },
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_lines = [
        "# Market Realism Soak Report",
        "",
        f"Run: {run_label} | Generated: {ts()}",
        "",
        "## Summary",
        "",
        f"- Cycles: {summary.get('total_cycles_completed', 0)}/{summary.get('total_cycles_attempted', 0)}",
        f"- Success rate: {summary.get('success_rate', 0)}%",
        f"- XRPL txs: {summary.get('total_xrpl_txs', 0)}",
        f"- Celo txs: {summary.get('total_celo_txs', 0)}",
        f"- Avg settlement: {summary.get('average_settlement_seconds', 0)}s",
        "",
        "## Config",
        "",
        f"- Quote-driven: {os.getenv('XRPL_QUOTE_DRIVEN', '0')}",
        f"- Reconciliation: {os.getenv('RECONCILIATION_ENABLED', '0')}",
        "",
        "## Artifacts",
        "",
        "- artifacts/reports/realism_soak_report.json",
        "- artifacts/reports/realism_soak_cycle_log.json",
        "- artifacts/proof_bundle/ (run-summary.json, cycles.csv, exceptions.csv, evidence/)",
        "",
    ]
    REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[{ts()}] Realism soak complete. Summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
