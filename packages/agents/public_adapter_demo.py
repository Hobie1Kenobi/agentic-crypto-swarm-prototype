#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env", override=True)


def _should_load_env_local() -> bool:
    chain_id = os.getenv("CHAIN_ID", "").strip()
    rpc = os.getenv("RPC_URL", "").strip().lower()
    if os.getenv("USE_ENV_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if chain_id == "31337":
        return True
    if rpc.startswith("http://127.0.0.1") or rpc.startswith("http://localhost") or "localhost" in rpc:
        return True
    return False


if _should_load_env_local() and (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)

sys.path.insert(0, str(root / "packages" / "agents"))

from services.public_market_adapter import run_public_adapter_demo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="What is one ethical use of AI?")
    ap.add_argument("--hybrid", action="store_true", help="Force hybrid path (public intake -> private settlement)")
    ap.add_argument("--replay", default="", help="Path to a JSON payload to replay as external request intake")
    args = ap.parse_args()
    replay_payload = None
    if args.replay:
        p = Path(args.replay)
        if not p.is_absolute():
            p = (root / p)
        replay_payload = json.loads(p.read_text(encoding="utf-8"))
    out = run_public_adapter_demo(args.prompt, force_hybrid=bool(args.hybrid), external_payload=replay_payload)
    print(out["public_response"])


if __name__ == "__main__":
    main()

