from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def write_proof_bundle(
    out_dir: Path,
    run_id: str,
    run_label: str,
    cycles: list[dict[str, Any]],
    summary: dict[str, Any],
) -> Path:
    bundle_dir = out_dir / "proof_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = bundle_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    run_summary = {
        "proof_type": "market_realism",
        "run_id": run_id,
        "run_label": run_label,
        "generated_at": _ts(),
        "total_cycles": len(cycles),
        "completed": summary.get("total_cycles_completed", 0),
        "failed": summary.get("total_cycles_failed", 0),
        "success_rate": summary.get("success_rate", 0),
        "total_xrpl_txs": summary.get("total_xrpl_txs", 0),
        "total_celo_txs": summary.get("total_celo_txs", 0),
        "average_settlement_seconds": summary.get("average_settlement_seconds", 0),
        "summary": summary,
    }
    (bundle_dir / "run-summary.json").write_text(json.dumps(run_summary, indent=2), encoding="utf-8")

    cycles_path = bundle_dir / "cycles.csv"
    with open(cycles_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = [
            "cycle", "start_time", "status", "task_template", "worker_metadata",
            "xrpl_tx_hash", "xrpl_amount", "internal_task_id", "celo_tx_count",
            "elapsed_seconds", "errors"
        ]
        writer.writerow(headers)
        for c in cycles:
            task = c.get("task") or {}
            template = task.get("template") if isinstance(task, dict) else c.get("task_template", "")
            celo = c.get("celo") or {}
            lifecycle = celo.get("lifecycle", []) if isinstance(celo, dict) else []
            writer.writerow([
                c.get("cycle"),
                c.get("start_time"),
                c.get("status"),
                (template or "")[:80],
                (c.get("actors") or {}).get("worker_id") if isinstance(c.get("actors"), dict) else c.get("worker_metadata"),
                (c.get("xrpl") or {}).get("tx_hash") if isinstance(c.get("xrpl"), dict) else c.get("xrpl_tx_hash"),
                (c.get("xrpl") or {}).get("delivered_amount") if isinstance(c.get("xrpl"), dict) else c.get("xrpl_amount"),
                (c.get("correlation") or {}).get("internal_task_id") if isinstance(c.get("correlation"), dict) else c.get("internal_task_id"),
                len(lifecycle) if lifecycle else len(c.get("celo_tx_hashes") or []),
                (c.get("elapsed") or {}).get("total_seconds") if isinstance(c.get("elapsed"), dict) else c.get("elapsed_seconds"),
                "; ".join(c.get("errors") or [])[:200],
            ])

    failed = [c for c in cycles if c.get("status") == "failed"]
    exceptions_path = bundle_dir / "exceptions.csv"
    with open(exceptions_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cycle", "start_time", "error_classification", "error_detail"])
        for c in failed:
            err = "; ".join(c.get("errors") or ["unknown"])[:200]
            writer.writerow([
                c.get("cycle"),
                c.get("start_time"),
                "failed",
                err,
            ])

    for c in cycles:
        cid = c.get("cycle", 0)
        ev = dict(c) if c.get("xrpl") or c.get("celo", {}).get("lifecycle") else {
            "cycle": cid,
            "start_time": c.get("start_time"),
            "end_time": c.get("end_time"),
            "status": c.get("status"),
            "task_template": c.get("task_template"),
            "worker_metadata": c.get("worker_metadata"),
            "worker_payout_address": c.get("worker_payout_address"),
            "xrpl_tx_hash": c.get("xrpl_tx_hash"),
            "xrpl_amount": c.get("xrpl_amount"),
            "xrpl_verification": c.get("xrpl_verification"),
            "internal_task_id": c.get("internal_task_id"),
            "celo_tx_hashes": c.get("celo_tx_hashes", []),
            "task_final_status": c.get("task_final_status"),
            "settlement": c.get("settlement", {}),
            "elapsed_seconds": c.get("elapsed_seconds"),
            "errors": c.get("errors", []),
            "warnings": c.get("warnings", []),
        }
        (evidence_dir / f"{cid:06d}.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")

    md_lines = [
        "# Market Realism Proof Report",
        "",
        f"**Run:** {run_label} | **Run ID:** {run_id} | **Generated:** {_ts()}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total cycles | {run_summary['total_cycles']} |",
        f"| Completed | {run_summary['completed']} |",
        f"| Failed | {run_summary['failed']} |",
        f"| Success rate | {run_summary['success_rate']}% |",
        f"| XRPL txs | {run_summary['total_xrpl_txs']} |",
        f"| Celo txs | {run_summary['total_celo_txs']} |",
        f"| Avg settlement | {run_summary['average_settlement_seconds']}s |",
        "",
        "## Artifacts",
        "",
        "- `run-summary.json` — Run metadata and aggregates",
        "- `cycles.csv` — Per-cycle data",
        "- `exceptions.csv` — Failed cycle classifications",
        "- `evidence/` — Per-cycle proof artifacts",
        "",
    ]
    (bundle_dir / "PROOF_REPORT.md").write_text("\n".join(md_lines), encoding="utf-8")
    return bundle_dir
