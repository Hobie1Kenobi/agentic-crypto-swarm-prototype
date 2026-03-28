#!/usr/bin/env python3
"""
1-hour soak test: x402 agent commerce (buy + sell) using only components that work
without Base/USDC faucet funding.
- BUY: Celo wallet pays our api_402 (Celo native)
- DISCOVERY: x402-bazaar (read-only, no payment)
- SELL: api_402 delivers; each buy cycle exercises the sell path

Runs for 1 hour, logs interactions, transactions, tasks. Produces soak report.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))
sys.path.insert(0, str(root / "scripts"))

from dotenv import load_dotenv
load_dotenv(root / ".env", override=True)

DURATION_HOURS = 1
INTERVAL_SECONDS = 90
QUERIES = [
    "What is agentic commerce in one phrase?",
    "Summarize: one ethical use of AI.",
    "Classify: Is sustainable compute beneficial? Yes or no.",
    "Short answer: What is x402 payment protocol?",
    "One sentence: Why do agents need micropayments?",
]

OUT_DIR = root
LOG_JSON = OUT_DIR / "x402_agent_commerce_soak_log.json"
REPORT_JSON = OUT_DIR / "x402_agent_commerce_soak_report.json"
REPORT_MD = OUT_DIR / "x402_agent_commerce_soak_report.md"


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cycle(cycle_num: int, api_process: subprocess.Popen | None) -> dict:
    os.chdir(root / "packages" / "agents")
    query = QUERIES[cycle_num % len(QUERIES)]
    record = {
        "cycle": cycle_num,
        "start_time": ts(),
        "type": "buy",
        "query": query[:60],
        "status": None,
        "latency_ms": None,
        "error": None,
        "seller": "api_402",
        "buyer": "celo_wallet",
    }
    start = time.time()
    try:
        from external_commerce.celo_native_buyer import invoke_celo_native_402
        status, data, err = invoke_celo_native_402(
            "http://127.0.0.1:8042/query",
            params={"q": query},
            timeout=90,
        )
        record["status"] = status
        record["latency_ms"] = round((time.time() - start) * 1000, 1)
        record["error"] = err
        if data and isinstance(data, dict):
            record["response_preview"] = (data.get("response") or str(data))[:100]
    except Exception as e:
        record["status"] = 0
        record["latency_ms"] = round((time.time() - start) * 1000, 1)
        record["error"] = str(e)
    record["end_time"] = ts()
    return record


def run_discovery_cycle(cycle_num: int) -> dict:
    os.chdir(root / "packages" / "agents")
    record = {
        "cycle": cycle_num,
        "start_time": ts(),
        "type": "discovery",
        "status": None,
        "latency_ms": None,
        "error": None,
        "item_count": None,
    }
    start = time.time()
    try:
        import requests
        r = requests.get(
            "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources",
            timeout=15,
        )
        record["status"] = r.status_code
        record["latency_ms"] = round((time.time() - start) * 1000, 1)
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            record["item_count"] = len(items)
    except Exception as e:
        record["status"] = 0
        record["latency_ms"] = round((time.time() - start) * 1000, 1)
        record["error"] = str(e)
    record["end_time"] = ts()
    return record


def main() -> int:
    revenue = os.getenv("REVENUE_SERVICE_ADDRESS", "").strip()
    pk = os.getenv("ROOT_STRATEGIST_PRIVATE_KEY", "").strip()
    rpc = os.getenv("RPC_URL", "").strip() or os.getenv("PRIVATE_RPC_URL", "").strip()
    if not revenue:
        print("REVENUE_SERVICE_ADDRESS not set. Deploy or set in .env")
        return 1
    if not pk or "0x" not in pk:
        print("ROOT_STRATEGIST_PRIVATE_KEY not set. Required for Celo payment.")
        return 1
    if not rpc:
        print("RPC_URL or PRIVATE_RPC_URL not set.")
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
        for _ in range(20):
            time.sleep(0.5)
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8042/health", timeout=2)
                break
            except Exception:
                pass
        else:
            print("api_402 did not become ready in time")
            return 1
    except Exception as e:
        print(f"Could not start api_402: {e}")
        return 1

    print(f"[{ts()}] x402 Agent Commerce Soak: 1 hour, ~{int(3600/INTERVAL_SECONDS)} cycles")
    print("  BUY: Celo wallet -> api_402 | DISCOVERY: x402-bazaar (read-only)")
    print("  Log: x402_agent_commerce_soak_log.json")
    print("-" * 60)

    cycles = []
    end_ts = time.time() + DURATION_HOURS * 3600
    cycle_num = 0

    while time.time() < end_ts:
        if cycle_num % 3 == 2:
            rec = run_discovery_cycle(cycle_num)
        else:
            rec = run_cycle(cycle_num, api_process)
        cycles.append(rec)
        try:
            LOG_JSON.write_text(json.dumps(cycles, indent=2), encoding="utf-8")
        except Exception:
            pass

        status = rec.get("status")
        lat = rec.get("latency_ms")
        typ = rec.get("type", "?")
        ok = "OK" if (status == 200) else "FAIL"
        extra = f" items={rec.get('item_count')}" if rec.get("item_count") is not None else ""
        print(f"  [{cycle_num:3d}] {typ:10s} {ok:4s} {lat}ms{extra}")

        cycle_num += 1
        remaining = end_ts - time.time()
        if remaining > 0:
            sleep = min(INTERVAL_SECONDS, remaining)
            time.sleep(sleep)

    if api_process:
        try:
            api_process.terminate()
            api_process.wait(timeout=5)
        except Exception:
            pass

    buy_cycles = [c for c in cycles if c.get("type") == "buy"]
    disc_cycles = [c for c in cycles if c.get("type") == "discovery"]
    buy_ok = sum(1 for c in buy_cycles if c.get("status") == 200)
    disc_ok = sum(1 for c in disc_cycles if c.get("status") == 200)
    latencies = [c["latency_ms"] for c in cycles if c.get("latency_ms") is not None]
    avg_lat = sum(latencies) / len(latencies) if latencies else 0

    summary = {
        "report_type": "x402_agent_commerce_soak",
        "generated_at": ts(),
        "duration_hours": DURATION_HOURS,
        "total_cycles": len(cycles),
        "buy_cycles": len(buy_cycles),
        "buy_success": buy_ok,
        "buy_success_rate": round(buy_ok / len(buy_cycles), 4) if buy_cycles else 0,
        "discovery_cycles": len(disc_cycles),
        "discovery_success": disc_ok,
        "discovery_success_rate": round(disc_ok / len(disc_cycles), 4) if disc_cycles else 0,
        "avg_latency_ms": round(avg_lat, 1),
        "errors": [c.get("error") for c in cycles if c.get("error")],
    }

    LOG_JSON.write_text(json.dumps(cycles, indent=2), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# x402 Agent Commerce Soak Report",
        "",
        f"Generated: {ts()}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Duration | {DURATION_HOURS}h |",
        f"| Total cycles | {len(cycles)} |",
        f"| Buy cycles | {len(buy_cycles)} |",
        f"| Buy success | {buy_ok}/{len(buy_cycles)} ({summary['buy_success_rate']*100:.1f}%) |",
        f"| Discovery cycles | {len(disc_cycles)} |",
        f"| Discovery success | {disc_ok}/{len(disc_cycles)} ({summary['discovery_success_rate']*100:.1f}%) |",
        f"| Avg latency | {avg_lat:.1f}ms |",
        "",
        "## Errors",
        "",
    ]
    for e in summary.get("errors") or []:
        if e:
            md_lines.append(f"- {e}")
    if not summary.get("errors"):
        md_lines.append("- None")
    REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print("-" * 60)
    print(f"[{ts()}] Soak complete. Buy: {buy_ok}/{len(buy_cycles)} | Discovery: {disc_ok}/{len(disc_cycles)} | Avg: {avg_lat:.0f}ms")
    print(f"  Report: {REPORT_MD}")
    return 0 if buy_ok == len(buy_cycles) else 1


if __name__ == "__main__":
    sys.exit(main())
