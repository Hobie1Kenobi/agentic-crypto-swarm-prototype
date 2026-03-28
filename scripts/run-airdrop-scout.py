#!/usr/bin/env python3
"""
Standalone Airdrop Intelligence scan — does NOT start soak or T54/Base sellers.

Loads repo .env, runs one LLM report, appends JSON line to external_commerce_data/airdrop-scans.jsonl.

Usage:
  python scripts/run-airdrop-scout.py
  python scripts/run-airdrop-scout.py --topic "March 2026 testnet incentives" --context "user notes"
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

load_dotenv(root / ".env", override=False)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one airdrop intelligence scan (separate from swarm sellers)")
    ap.add_argument("--topic", default="", help="Focus topic for the scan")
    ap.add_argument("--context", default="", help="Optional notes or URLs (truncated in prompt)")
    ap.add_argument("--stdout-only", action="store_true", help="Print JSON only; do not append JSONL")
    args = ap.parse_args()

    from airdrop_scout.report import generate_airdrop_report

    report = generate_airdrop_report(args.topic or None, args.context or None)
    line = json.dumps(report, ensure_ascii=False)
    print(line)

    if not args.stdout_only:
        out_dir = root / "external_commerce_data"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "airdrop-scans.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"Appended to {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
