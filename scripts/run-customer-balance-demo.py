#!/usr/bin/env python3
"""
Customer balance layer demo: XRPL payment -> credit -> debit -> Celo settlement.

Runs one multi-rail hybrid cycle with CUSTOMER_BALANCE_ENABLED=1 on live Celo Sepolia.
Uses mock XRPL by default (no XRPL faucet needed). For live XRPL, set XRPL_PAYMENT_MODE=live
and fund XRPL_WALLET_SEED.

Usage:
  python scripts/run-customer-balance-demo.py [--live-xrpl] [--prompt "query"]

Produces:
  - multi_rail_run_report.json (includes customer_balance section)
  - customer_balance_demo_report.json
  - customer_balance_demo_report.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run customer balance layer demo on live testnet")
    parser.add_argument("--prompt", default="What is one ethical use of AI?", help="Query prompt")
    parser.add_argument("--live-xrpl", action="store_true", help="Use live XRPL payment (requires funded XRPL_WALLET_SEED)")
    args = parser.parse_args()

    os.environ["CUSTOMER_BALANCE_ENABLED"] = "1"
    os.environ["PAYMENT_RAIL_MODE"] = "hybrid_public_request_xrpl_payment_private_celo_settlement"
    os.environ["MARKET_MODE"] = "hybrid"
    os.environ["XRPL_ENABLED"] = "1"
    os.environ["XRPL_PAYMENT_MODE"] = "live" if args.live_xrpl else "mock"

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        demo_db = f.name
    os.environ["CUSTOMER_BALANCE_DB_PATH"] = demo_db

    try:
        from services.multi_rail_hybrid import run_multi_rail_hybrid_demo

        print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] Customer balance demo starting...")
        print("  CUSTOMER_BALANCE_ENABLED=1, XRPL_PAYMENT_MODE=" + ("live" if args.live_xrpl else "mock"))
        result = run_multi_rail_hybrid_demo(args.prompt, force_hybrid=True)
        pmr = result.get("private_market_report") or {}
        ok = bool(pmr.get("ok", False))

        cb = result.get("customer_balance")
        balance_ok = bool(cb and (cb.get("credits") or cb.get("debits")))
        report = {
            "demo_type": "customer_balance_layer",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ok": ok,
            "balance_layer_ok": balance_ok,
            "celo_settlement_ok": ok,
            "payment_mode": "live" if args.live_xrpl else "mock",
            "customer_balance": cb,
            "xrpl_payment": result.get("xrpl_payment"),
            "private_market_report": {
                "ok": result.get("private_market_report", {}).get("ok"),
                "task_id": (result.get("private_market_report") or {}).get("task", {}).get("task_id"),
                "tx_hashes": (result.get("private_market_report") or {}).get("tx_hashes", []),
                "compute_marketplace_address": (result.get("private_market_report") or {}).get("compute_marketplace_address"),
            },
            "flow": [
                "1. XRPL payment (mock/live) -> verified receipt",
                "2. Credit customer balance (XRP/RLUSD -> wei)",
                "3. Budget check (balance >= escrow)",
                "4. Debit escrow",
                "5. createTask on Celo Sepolia",
                "6. Metering record",
            ],
        }

        out_dir = root
        _write_json(out_dir / "customer_balance_demo_report.json", report)

        cb = report.get("customer_balance") or {}
        pmr = report.get("private_market_report") or {}
        explorer = "https://celo-sepolia.blockscout.com"
        md_lines = [
            "# Customer Balance Layer Demo Report",
            "",
            f"**Date:** {report['timestamp']}",
            "",
            f"- **Balance layer (credit/debit):** {'✅ OK' if report.get('balance_layer_ok') else '❌'}",
            f"- **Celo settlement:** {'✅ OK' if report.get('celo_settlement_ok') else '❌'}",
            "",
            "## Flow",
            "",
        ]
        for line in report["flow"]:
            md_lines.append(f"- {line}")
        md_lines.extend([
            "",
            "## Customer Balance Activity",
            "",
            f"- **Customer ID:** `{cb.get('customer_id', 'n/a')}`",
            f"- **Balance (after):** {cb.get('balance_wei', 0)} wei",
            f"- **Credits:** {len(cb.get('credits', []))}",
            f"- **Debits:** {len(cb.get('debits', []))}",
            f"- **Metering records:** {len(cb.get('metering', []))}",
            "",
        ])
        if cb.get("credits"):
            md_lines.append("### Credits")
            for c in cb["credits"]:
                md_lines.append(f"- +{c.get('amount_wei', 0)} wei ({c.get('asset', '')}) ref={c.get('external_ref', '')[:20]}...")
        if cb.get("debits"):
            md_lines.append("### Debits")
            for d in cb["debits"]:
                md_lines.append(f"- -{d.get('amount_wei', 0)} wei task_id={d.get('task_id')}")
        md_lines.extend([
            "",
            "## Celo Settlement",
            "",
            f"- **Task ID:** {pmr.get('task_id', 'n/a')}",
            f"- **ComputeMarketplace:** `{pmr.get('compute_marketplace_address', 'n/a')}`",
            "",
        ])
        for t in pmr.get("tx_hashes", []):
            h = t.get("tx_hash", "") if isinstance(t, dict) else str(t)
            if h:
                md_lines.append(f"- [{t.get('name', 'tx')}]({explorer}/tx/{h})")
        md_lines.append("")
        (out_dir / "customer_balance_demo_report.md").write_text("\n".join(md_lines), encoding="utf-8")

        print(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] Demo complete. ok={ok}")
        print(f"  Reports: customer_balance_demo_report.json, customer_balance_demo_report.md")
        if cb:
            print(f"  Customer: {cb.get('customer_id')} | Credits: {len(cb.get('credits', []))} | Debits: {len(cb.get('debits', []))}")
        return 0 if ok else 1
    finally:
        try:
            os.unlink(demo_db)
        except OSError:
            pass


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
