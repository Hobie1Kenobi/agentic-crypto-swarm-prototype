#!/usr/bin/env python3
"""
Smoke test: facilitator x402 seller (api_seller_x402) — external-style buyer pays Base Sepolia USDC.

Prereqs:
  - pip install x402[requests] (already in packages/agents/requirements.txt)
  - Fund ROOT_STRATEGIST on Celo Sepolia; bridge auto-funds Base Sepolia USDC (see bridge_utils), OR fund Base Sepolia USDC directly
  - Ollama running if you want real LLM answers (else may error inside generate_response_for_query)

Usage:
  Terminal A:  python -m uvicorn api_seller_x402:create_app --host 127.0.0.1 --port 8043 --factory
                (from packages/agents, PYTHONPATH=.)

  Terminal B:  python scripts/run-x402-seller-smoke.py

  Or one-shot (starts seller subprocess):
    python scripts/run-x402-seller-smoke.py --auto-start

Dry run (no USDC spend, probes 402 only):
    X402_DRY_RUN=1 python scripts/run-x402-seller-smoke.py --auto-start

Public URL (Bazaar / third parties must reach you):
  - Expose https://your-domain/x402/v1/query via reverse proxy or ngrok
  - First successful paid call through x402.org facilitator indexes you in Bazaar discovery
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)

DEFAULT_URL = os.getenv("X402_SELLER_SMOKE_URL", "http://127.0.0.1:8043/x402/v1/query")


def _wait_health(timeout: float = 25.0) -> bool:
    import urllib.request

    health = "http://127.0.0.1:8043/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(health, timeout=2)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test x402 facilitator seller")
    parser.add_argument("--auto-start", action="store_true", help="Start api_seller_x402 on 8043 via subprocess")
    parser.add_argument("--url", default=DEFAULT_URL, help="Full query URL (default local seller)")
    args = parser.parse_args()

    os.environ.setdefault("X402_ALLOWED_NETWORKS", "eip155:84532")
    os.environ.setdefault("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator")

    proc = None
    if args.auto_start:
        agents = root / "packages" / "agents"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(agents)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api_seller_x402:create_app",
                "--host",
                "127.0.0.1",
                "--port",
                "8043",
                "--factory",
            ],
            cwd=str(agents),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_health():
            print("Seller did not become ready on :8043. Start manually: cd packages/agents && PYTHONPATH=. python -m uvicorn api_seller_x402:create_app --host 127.0.0.1 --port 8043 --factory")
            if proc:
                proc.terminate()
            return 1

    from external_commerce.x402_buyer import X402Buyer

    dry = os.getenv("X402_DRY_RUN", "0").strip().lower() in {"1", "true", "yes"}
    print(f"X402_DRY_RUN={dry} | URL={args.url}")
    if not dry:
        print("Paid mode: ensure Base Sepolia USDC (bridge from Celo or CDP faucet).")

    buyer = X402Buyer(dry_run=dry)
    start = time.time()
    status, data, err = buyer.invoke(args.url, method="GET", params={"q": "One sentence: what is agentic commerce?"}, timeout=120)
    ms = (time.time() - start) * 1000
    print(f"status={status} latency_ms={ms:.0f} err={err}")
    if data:
        print(json.dumps(data, indent=2)[:1200])

    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if status == 200:
        print("\nOK — seller received payment + returned body. After a public URL + real pay, Bazaar may index (facilitator catalog).")
        return 0
    if status == 402 and dry:
        print("\n402 without pay is expected in dry_run (no signature path).")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
