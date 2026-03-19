#!/usr/bin/env python3
"""
Run multi-rail hybrid demo: XRPL payment (mock/replay/live) + Celo private settlement.

Usage:
  python scripts/run-multi-rail-demo.py [--replay-xrpl path/to/replay.json] [--prompt "query"]

Env:
  PAYMENT_RAIL_MODE=hybrid_public_request_xrpl_payment_private_celo_settlement
  XRPL_ENABLED=1
  XRPL_PAYMENT_MODE=mock|replay|live
  MARKET_MODE=hybrid
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-rail hybrid demo")
    parser.add_argument("--prompt", default="What is one ethical use of AI?", help="Query prompt")
    parser.add_argument("--replay-xrpl", type=Path, help="Path to XRPL replay payload JSON")
    parser.add_argument("--force-hybrid", action="store_true", help="Force hybrid mode")
    args = parser.parse_args()

    if args.replay_xrpl and args.replay_xrpl.exists():
        os.environ["XRPL_PAYMENT_MODE"] = "replay"
        os.environ["PAYMENT_RAIL_MODE"] = "xrpl_x402_payment"
    xrpl_replay = None
    if args.replay_xrpl and args.replay_xrpl.exists():
        xrpl_replay = json.loads(args.replay_xrpl.read_text(encoding="utf-8"))

    from services.multi_rail_hybrid import run_multi_rail_hybrid_demo

    result = run_multi_rail_hybrid_demo(
        args.prompt,
        force_hybrid=args.force_hybrid,
        xrpl_replay_payload=xrpl_replay,
    )

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
