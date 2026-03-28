"""
T54 XRPL reporting — summary JSON and markdown report.
"""
from __future__ import annotations

import json
from pathlib import Path

from .reconciliation import T54ReconciliationStore


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_output_dir() -> Path:
    return _repo_root() / "external_commerce_data"


def build_summary(attempts: list[dict]) -> dict:
    mainnet = sum(1 for a in attempts if a.get("network") == "mainnet" or a.get("mode") == "mainnet")
    testnet = sum(1 for a in attempts if a.get("network") == "testnet" or a.get("mode") == "testnet")
    local_dev = sum(1 for a in attempts if a.get("mode") == "local")
    real = sum(1 for a in attempts if a.get("verification_status") == "real_t54_xrpl_payment")
    simulated = sum(1 for a in attempts if a.get("verification_status") == "simulated_t54_xrpl_testnet")
    blocked = sum(1 for a in attempts if a.get("verification_status") == "testnet_facilitator_unavailable")
    failed_pre = sum(1 for a in attempts if a.get("verification_status") == "payment_failed_pre_submit")
    failed_verify = sum(1 for a in attempts if a.get("verification_status") == "facilitator_verify_failed")
    failed_settle = sum(1 for a in attempts if a.get("verification_status") == "facilitator_settle_failed")
    local_only = sum(1 for a in attempts if a.get("verification_status") == "local_dev_only")
    return {
        "total_attempts": len(attempts),
        "mainnet_attempts": mainnet,
        "testnet_attempts": testnet,
        "local_dev_attempts": local_dev,
        "real_settlements": real,
        "simulated_settlements": simulated,
        "blocked_no_testnet_facilitator": blocked,
        "failed_pre_submit": failed_pre,
        "failed_verify": failed_verify,
        "failed_settle": failed_settle,
        "local_dev_only": local_only,
    }


def write_reports(output_dir: Path | None = None) -> tuple[Path, Path]:
    out = output_dir or _default_output_dir()
    out.mkdir(parents=True, exist_ok=True)
    store = T54ReconciliationStore()
    attempts = store.load_all()
    summary = build_summary(attempts)
    summary_path = out / "t54-xrpl-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path = out / "t54-xrpl-report.md"
    lines = [
        "# T54 XRPL Payment Report",
        "",
        f"- **Total attempts:** {summary['total_attempts']}",
        f"- **Mainnet attempts:** {summary['mainnet_attempts']}",
        f"- **Testnet attempts:** {summary['testnet_attempts']}",
        f"- **Local/dev attempts:** {summary['local_dev_attempts']}",
        "",
        "## Outcomes",
        f"- **Real settlements:** {summary['real_settlements']}",
        f"- **Simulated settlements:** {summary['simulated_settlements']}",
        f"- **Blocked (no testnet facilitator):** {summary['blocked_no_testnet_facilitator']}",
        f"- **Failed pre-submit:** {summary['failed_pre_submit']}",
        f"- **Failed verify:** {summary['failed_verify']}",
        f"- **Failed settle:** {summary['failed_settle']}",
        f"- **Local/dev only:** {summary['local_dev_only']}",
        "",
        "## Artifacts",
        f"- `t54-xrpl-payment-attempts.jsonl` — Raw attempts",
        f"- `t54-xrpl-summary.json` — Aggregated summary",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path, report_path
