#!/usr/bin/env python3
"""
Short test: buy from ourselves using Celo wallet.
- Seller: our api_402 (Celo AgentRevenueService)
- Buyer: our Celo wallet (ROOT_STRATEGIST)
- Proves agent-to-agent commerce using existing .env wallets.
"""
from __future__ import annotations

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


def main() -> int:
    api_url = os.getenv("API_402_BASE_URL", "http://127.0.0.1:8042")
    query = os.getenv("X402_TEST_QUERY", "What is agentic commerce?")
    rpc = os.getenv("RPC_URL", os.getenv("PRIVATE_RPC_URL", "")).strip()
    revenue = os.getenv("REVENUE_SERVICE_ADDRESS", "").strip()
    pk = os.getenv("ROOT_STRATEGIST_PRIVATE_KEY", "").strip()

    if not revenue:
        print("REVENUE_SERVICE_ADDRESS not set. Deploy AgentRevenueService or set in .env")
        return 1
    if not pk or "0x" not in pk:
        print("ROOT_STRATEGIST_PRIVATE_KEY not set. Required for Celo payment.")
        return 1

    api_process = None
    agents_dir = root / "packages" / "agents"
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(agents_dir)
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api_402:create_app", "--host", "127.0.0.1", "--port", "8042", "--factory"],
            cwd=str(agents_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        api_process = proc
        for _ in range(15):
            time.sleep(0.5)
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8042/health", timeout=2)
                break
            except Exception:
                pass
        else:
            print("api_402 did not become ready in time")
    except Exception as e:
        print(f"Could not start api_402: {e}")
        print("Start manually: cd packages/agents && python -m uvicorn api_402:create_app --host 127.0.0.1 --port 8042 --factory")

    resource_url = f"{api_url.rstrip('/')}/query"
    print(f"Testing: BUY from ourselves (seller=api_402, buyer=Celo wallet)")
    print(f"  URL: {resource_url}?q={query[:40]}...")

    from external_commerce.celo_native_buyer import invoke_celo_native_402

    start = time.time()
    status, data, err = invoke_celo_native_402(resource_url, params={"q": query}, timeout=90)
    elapsed = (time.time() - start) * 1000

    if api_process:
        try:
            api_process.terminate()
        except Exception:
            pass

    if status == 200 and data:
        print(f"  SUCCESS: {status} in {elapsed:.0f}ms")
        print(f"  Response: {json.dumps(data, indent=2)[:400]}...")
        return 0
    print(f"  FAILED: status={status} err={err}")
    if data:
        print(f"  Data: {data}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
