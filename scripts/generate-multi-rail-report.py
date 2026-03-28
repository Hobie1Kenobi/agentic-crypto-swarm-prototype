#!/usr/bin/env python3
"""
Generate multi-rail correlation reports: xrpl_payment_report, xrpl_to_celo_correlation_report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _reports_dir(root: Path) -> Path:
    d = root / "artifacts" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _in_report(root: Path, name: str) -> Path:
    ar = root / "artifacts" / "reports" / name
    if ar.exists():
        return ar
    return root / name


def _comm_trace_json(root: Path) -> Path:
    p = root / "artifacts" / "communication" / "communication_trace.json"
    if p.exists():
        return p
    return root / "communication_trace.json"


def main() -> None:
    root = _root()
    rep = _reports_dir(root)
    multi = _read_json(_in_report(root, "multi_rail_run_report.json")) or _read_json(
        _in_report(root, "public_adapter_run_report.json")
    ) or {}
    trace = _read_json(_comm_trace_json(root)) or {}
    private = _read_json(_in_report(root, "celo_sepolia_task_market_report.json")) or _read_json(
        _in_report(root, "local_task_market_report.json")
    ) or {}

    xrpl_payment = multi.get("xrpl_payment") or {}
    payment_boundary = multi.get("payment_boundary", "none")
    chains = multi.get("chains", {})
    private_report = multi.get("private_market_report") or private

    xrpl_report: dict[str, Any] = {
        "ok": bool(xrpl_payment.get("verified", False)) or payment_boundary in {"mock_xrpl_payment", "replayed_xrpl_payment"},
        "payment_rail": "xrpl",
        "payment_asset": xrpl_payment.get("payment_asset", "XRP"),
        "external_payment_id": xrpl_payment.get("external_payment_id"),
        "xrpl_tx_hash": xrpl_payment.get("tx_hash"),
        "payer_address": xrpl_payment.get("payer_address"),
        "receiver_address": xrpl_payment.get("receiver_address"),
        "amount": xrpl_payment.get("amount"),
        "verified": xrpl_payment.get("verified", False),
        "verification_boundary": payment_boundary,
        "internal_task_id": None,
    }

    correlation: dict[str, Any] = {
        "xrpl_payment": xrpl_report,
        "celo_settlement": {
            "ok": bool(private_report.get("ok")),
            "internal_task_id": (private_report.get("task") or {}).get("task_id"),
            "tx_hashes": [t.get("tx_hash") for t in (private_report.get("tx_hashes") or []) if t.get("tx_hash")],
            "compute_marketplace_address": private_report.get("compute_marketplace_address"),
        },
        "correlation": trace.get("correlation", {}).get("xrpl_to_celo") or {},
    }

    if correlation["celo_settlement"].get("internal_task_id") is not None:
        xrpl_report["internal_task_id"] = correlation["celo_settlement"]["internal_task_id"]

    xrpl_report_path = rep / "xrpl_payment_report.json"
    xrpl_report_path.write_text(json.dumps(xrpl_report, indent=2), encoding="utf-8")
    print(f"Wrote {xrpl_report_path}")

    corr_path = rep / "xrpl_to_celo_correlation_report.json"
    corr_path.write_text(json.dumps(correlation, indent=2), encoding="utf-8")
    print(f"Wrote {corr_path}")

    md_lines = [
        "# XRPL Payment Report",
        "",
        f"- Payment rail: `{xrpl_report['payment_rail']}`",
        f"- Asset: `{xrpl_report['payment_asset']}`",
        f"- External payment ID: `{xrpl_report.get('external_payment_id') or 'n/a'}`",
        f"- XRPL tx hash: `{xrpl_report.get('xrpl_tx_hash') or 'n/a'}`",
        f"- Verified: `{xrpl_report['verified']}`",
        f"- Verification boundary: `{xrpl_report['verification_boundary']}`",
        "",
    ]
    (rep / "xrpl_payment_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {rep / 'xrpl_payment_report.md'}")

    corr_md = [
        "# XRPL to Celo Correlation Report",
        "",
        "## XRPL Payment",
        "",
        f"- Tx hash: `{xrpl_report.get('xrpl_tx_hash') or 'n/a'}`",
        f"- Boundary: `{xrpl_report['verification_boundary']}`",
        "",
        "## Celo Settlement",
        "",
        f"- Internal task ID: `{correlation['celo_settlement'].get('internal_task_id') or 'n/a'}`",
        f"- Tx count: `{len(correlation['celo_settlement'].get('tx_hashes') or [])}`",
        "",
    ]
    (rep / "xrpl_to_celo_correlation_report.md").write_text("\n".join(corr_md), encoding="utf-8")
    print(f"Wrote {rep / 'xrpl_to_celo_correlation_report.md'}")


if __name__ == "__main__":
    main()
