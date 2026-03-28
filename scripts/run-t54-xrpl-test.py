"""
Run t54 XRPL adapter test — exercises mainnet/testnet/local modes.
Usage:
  T54_XRPL_ENABLED=1 T54_XRPL_MODE=testnet python scripts/run-t54-xrpl-test.py
  T54_XRPL_DRY_RUN=1 T54_XRPL_MODE=local python scripts/run-t54-xrpl-test.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))
os.chdir(root / "packages" / "agents")

from dotenv import load_dotenv
load_dotenv(root / ".env", override=True)
load_dotenv(root / ".env.local", override=True)

from config.t54_config import get_t54_xrpl_config, t54_testnet_blocked_reason
from integrations.t54_xrpl import T54XrplAdapter, write_reports


def main() -> int:
    cfg = get_t54_xrpl_config()
    print(f"T54 config: enabled={cfg.enabled}, mode={cfg.mode}, network={cfg.network}")
    blocked = t54_testnet_blocked_reason(cfg)
    if blocked:
        print(f"  Blocked: {blocked}")
    adapter = T54XrplAdapter(config=cfg)
    dummy_url = "https://httpbin.org/get"
    print(f"\nInvoke {dummy_url} (no 402 expected)...")
    status, data, err, rec = adapter.invoke(dummy_url, method="GET", timeout=10)
    print(f"  Status: {status}, err={err}")
    print(f"  Record: verification_status={rec.verification_status}, validated={rec.validated}")
    if rec.reason:
        print(f"  Reason: {rec.reason}")
    out_dir = root / "external_commerce_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path, report_path = write_reports(out_dir)
    print(f"\nReports: {summary_path.name}, {report_path.name}")
    attempts_path = out_dir / "t54-xrpl-payment-attempts.jsonl"
    if attempts_path.exists():
        lines = attempts_path.read_text(encoding="utf-8").strip().split("\n")
        for i, line in enumerate(lines[-3:]):
            if line:
                print(f"  Attempt: {json.dumps(json.loads(line), indent=2)[:400]}...")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["testnet", "mainnet", "local"], default="testnet")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    os.environ.setdefault("T54_XRPL_ENABLED", "1")
    os.environ["T54_XRPL_MODE"] = args.mode
    if args.dry_run:
        os.environ["T54_XRPL_DRY_RUN"] = "1"
    sys.exit(main())
