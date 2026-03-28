#!/usr/bin/env python3
"""
Validate T54 XRPL x402: adapter smoke + optional full 402→pay→settle against a merchant URL.

1) Adapter smoke (httpbin, no 402) — same as run-t54-xrpl-test
2) Marketplace invoke — needs a merchant that returns HTTP 402 with XRPL payment terms.
   Set T54_X402_RESOURCE_URL in .env, or pass --merchant-url.
   For a local merchant: pip install fastapi uvicorn x402-xrpl python-dotenv
   then: python scripts/t54_local_merchant.py
        T54_X402_RESOURCE_URL=http://127.0.0.1:8765/hello python scripts/run-t54-marketplace-cycle.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)
load_dotenv(root / ".env.local", override=True)


def main() -> int:
    p = argparse.ArgumentParser(description="T54 XRPL marketplace validation cycle")
    p.add_argument(
        "--mode",
        choices=["mainnet", "testnet", "local"],
        default=None,
        help="T54_XRPL_MODE (default: mainnet if unset in env; testnet needs T54_XRPL_FACILITATOR_URL)",
    )
    p.add_argument("--dry-run", action="store_true", help="T54_XRPL_DRY_RUN=1 for HTTP only")
    p.add_argument("--merchant-url", default="", help="Override T54_X402_RESOURCE_URL for this run")
    p.add_argument("--skip-smoke", action="store_true", help="Skip httpbin adapter smoke")
    p.add_argument("--skip-marketplace", action="store_true", help="Only run smoke + reports")
    args = p.parse_args()

    if args.mode:
        os.environ["T54_XRPL_MODE"] = args.mode
    elif not (os.environ.get("T54_XRPL_MODE") or "").strip():
        os.environ["T54_XRPL_MODE"] = "mainnet"
    if args.dry_run:
        os.environ["T54_XRPL_DRY_RUN"] = "1"
    if args.merchant_url:
        os.environ["T54_X402_RESOURCE_URL"] = args.merchant_url.strip()

    os.environ.setdefault("T54_XRPL_ENABLED", "1")

    os.chdir(root / "packages" / "agents")

    from config.t54_config import get_t54_xrpl_config, t54_testnet_blocked_reason
    from integrations.t54_xrpl import T54XrplAdapter, write_reports
    from external_commerce.discovery import Discovery
    from external_commerce.invoker import invoke_by_provider

    cfg = get_t54_xrpl_config()
    print("=== T54 config ===")
    print(f"  enabled={cfg.enabled} mode={cfg.mode} network={cfg.network} dry_run={cfg.dry_run}")
    print(f"  facilitator_url={cfg.facilitator_url or '(default mainnet in code)'}")
    blocked = t54_testnet_blocked_reason(cfg)
    if blocked:
        print(f"  testnet block: {blocked}")

    if not cfg.enabled:
        print("ERROR: Set T54_XRPL_ENABLED=1 in .env")
        return 1

    if not args.skip_smoke:
        print("\n=== Step 1: Adapter smoke (httpbin, expect 200, no XRPL payment) ===")
        adapter = T54XrplAdapter(config=cfg)
        dummy = "https://httpbin.org/get"
        status, data, err, rec = adapter.invoke(dummy, method="GET", timeout=15)
        print(f"  status={status} err={err}")
        print(f"  verification_status={rec.verification_status} validated={rec.validated}")
        if rec.reason:
            print(f"  reason={rec.reason}")

    out_dir = root / "external_commerce_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path, report_path = write_reports(out_dir)
    print(f"\n  Reports: {summary_path.name}, {report_path.name}")

    if args.skip_marketplace:
        print("\n=== Skipping marketplace (--skip-marketplace) ===")
        return 0

    merchant = (os.environ.get("T54_X402_RESOURCE_URL") or os.environ.get("X402_T54_RESOURCE_URL") or "").strip()
    if not merchant:
        print("\n=== Step 2: Marketplace invoke SKIPPED ===")
        print("  No T54_X402_RESOURCE_URL (or --merchant-url). No public catalog lists a free XRPL x402 merchant URL.")
        print("  Options:")
        print("    A) Run: python scripts/t54_local_merchant.py  (other terminal)")
        print("       then: set T54_X402_RESOURCE_URL=http://127.0.0.1:8765/hello")
        print("       and re-run this script.")
        print("    B) Set T54_X402_RESOURCE_URL to any HTTPS x402 merchant that returns 402 with XRPL (xrpl:0 mainnet).")
        return 0

    print(f"\n=== Step 2: Marketplace invoke (t54-xrpl) -> {merchant[:88]} ===")
    discovery = Discovery()
    providers = discovery.discover_from_config()
    prov = next((x for x in providers if x.provider_id == "t54-xrpl-example"), None)
    if not prov or not (prov.resource_url or "").strip():
        print("ERROR: t54-xrpl-example has no resource_url after env override.")
        return 1

    status, data, err = invoke_by_provider(prov, params={}, method="GET", timeout=120)
    print(f"  status={status} err={err}")
    if data:
        s = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
        print(f"  response: {s[:1200]}")
    write_reports(out_dir)
    attempts = out_dir / "t54-xrpl-payment-attempts.jsonl"
    cfg2 = get_t54_xrpl_config()
    ok = status == 200 and not err
    if cfg2.dry_run and status == 402:
        print("\n  OK: Merchant returned 402 Payment Required (dry-run path; no XRPL tx).")
        ok = True
    if err and "actNotFound" in str(err):
        print("\n  Hint: Fund the XRPL account for your T54_XRPL_WALLET_SEED on mainnet, or use T54_XRPL_DRY_RUN=1 to validate 402-only.")
    if attempts.exists():
        lines = attempts.read_text(encoding="utf-8").strip().split("\n")
        if lines:
            last = json.loads(lines[-1])
            print(f"\n  Last attempt verification_status: {last.get('verification_status')}")
            print(f"  validated: {last.get('validated')}")
            if last.get("xrpl_tx_hash"):
                print(f"  xrpl_tx_hash: {last.get('xrpl_tx_hash')}")
            if last.get("validated") and last.get("verification_status") == "real_t54_xrpl_payment":
                ok = True
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
