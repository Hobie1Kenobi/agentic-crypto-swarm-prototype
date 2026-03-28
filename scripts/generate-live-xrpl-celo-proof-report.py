#!/usr/bin/env python3
"""
Generate live_xrpl_to_celo_proof_report from multi_rail_run_report.json.

Use when you have a successful live XRPL + Celo run and want to regenerate
the presentation-grade proof without re-running the demo.

Usage:
  python scripts/generate-live-xrpl-celo-proof-report.py [path/to/multi_rail_run_report.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

_default = root / "artifacts" / "reports" / "multi_rail_run_report.json"
if not _default.exists():
    _default = root / "multi_rail_run_report.json"
report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _default
out_dir = root / "artifacts" / "reports"


def main() -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not report_path.exists():
        print(f"Error: {report_path} not found")
        return 1
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if data.get("payment_boundary") != "real_xrpl_payment":
        print("Error: multi_rail_run_report does not contain real_xrpl_payment")
        return 1
    xrpl = data.get("xrpl_payment") or {}
    private = data.get("private_market_report") or {}
    if not private.get("ok"):
        print("Error: Celo settlement did not succeed")
        return 1

    from services.multi_rail_hybrid import _write_live_proof_report

    _write_live_proof_report(out_dir, data.get("run_id", "unknown"), xrpl, private)
    print(f"Generated live_xrpl_to_celo_proof_report.(json|md) in {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
