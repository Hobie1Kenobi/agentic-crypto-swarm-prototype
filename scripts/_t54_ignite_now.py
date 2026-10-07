"""Direct T54 ignition — buyer already funded. Cheapest-first. No XUMM wait."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "agents"))
os.chdir(ROOT / "packages" / "agents")

load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)
load_dotenv(ROOT / ".env.mainnet", override=False)
load_dotenv(ROOT / "secrets" / "t54-ignition-buyer.env", override=True)

os.environ["X402_BROKER_PAY_MODE"] = "xrpl_mainnet"
os.environ["X402_BROKER_MAINNET_ACK"] = "1"
os.environ["T54_XRPL_ENABLED"] = "1"
os.environ["T54_XRPL_MODE"] = "mainnet"
os.environ["MAX_XRP_SPEND_PER_TX"] = "1.5"
os.environ.setdefault("XRPL_RPC_URL", "https://xrplcluster.com")

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo
from xrpl.wallet import Wallet
from x402_broker_client.client import execute_x402_request, xrpl_mainnet_pay_invoice

BUYER = Wallet.from_seed(os.environ["AGENT_XRPL_WALLET_SEED"])
print("buyer", BUYER.classic_address, flush=True)
assert BUYER.classic_address == "r4n6M6QLWoFQVGXJ5PeESJjwUARVT91MYJ"

RPCs = ["https://xrplcluster.com", "https://s1.ripple.com:51234", "https://xrpl.ws"]

def get_bal() -> float:
    last = None
    for rpc in RPCs:
        try:
            c = JsonRpcClient(rpc)
            r = c.request(AccountInfo(account=BUYER.classic_address, ledger_index="validated"))
            return int(r.result["account_data"]["Balance"]) / 1e6
        except Exception as e:
            last = e
    raise RuntimeError(f"bal_failed:{last}")

bal0 = get_bal()
print(f"bal_before {bal0:.6f} XRP", flush=True)

BASE = "https://api.agentic-swarm-marketplace.com/t54"
session = requests.Session()
session.headers.update({"User-Agent": "ASM-T54-Ignition/1.0"})

health = session.get(BASE + "/health", timeout=30).json()
skus = sorted(health["skus"], key=lambda s: int(s["price_drops"]))
SKIP = {"peer-origin-verify"}
RESERVE_XRP = 1.05

POST_BODIES = {
    "procurement-readiness": {"request_text": "Need 24x Cisco C9300-48P switches with StackWise and 3yr SmartNet for Chicago DC refresh."},
    "specification-normalizer": {"raw_text": "Cisco Catalyst 9300 48-port PoE+ Switch, StackWise-480, Network Advantage"},
    "quote-completeness-audit": {"quote_text": "Line1: C9300-48P qty 24 @ $4500; freight TBD; tax not included; valid 30 days."},
    "rfp-requirement-extractor": {"rfp_text": "City RFP for network refresh due 2026-12-01. Mandatory: C9300 or equiv, TAA, 5yr support."},
    "bid-fit-score": {"opportunity_text": "MSP bid for mid-market campus LAN refresh, $400k ceiling, prefer Cisco.", "capabilities_text": "Cisco Gold VAR, local staging."},
    "bom-risk-audit": {"bom_text": "24x C9300-48P; missing stacking cables; no optics listed; licenses unclear."},
    "purchase-readiness-package": {"request_text": "Package a purchase-ready inquiry for 24x C9300-48P with optics and SmartNet."},
}
GET_PARAMS = {
    "hello": {},
    "structured-query": {"q": "What is ASM T54?"},
    "research-brief": {"topic": "XRPL x402 micropayments"},
    "constitution-audit-lite": {"prompt_snippet": "Should an agent auto-spend treasury without human review?"},
    "ecosystem-pulse": {"fresh": "0"},
    "agent-commerce-data": {"depth": "standard"},
    "airdrop-intelligence-report": {"topic": "XRPL incentive programs"},
    "intake-resale-pack": {"pack_id": "demo"},
}

results = []
for sku in skus:
    sid = sku["sku_id"]
    if sid in SKIP:
        results.append({"sku": sid, "status": "skipped", "reason": "not_asm_ignition"})
        print(f"SKIP {sid}", flush=True)
        continue
    drops = int(sku["price_drops"])
    xrp = drops / 1e6
    try:
        bal = get_bal()
    except Exception as e:
        results.append({"sku": sid, "status": "bal_error", "error": str(e)})
        print("BAL_ERR", e, flush=True)
        break
    if bal - xrp < RESERVE_XRP:
        results.append({"sku": sid, "status": "stopped_reserve", "bal": bal, "need_xrp": xrp})
        print(f"STOP_RESERVE {sid} bal={bal:.4f} need={xrp}", flush=True)
        break
    url = BASE + sku["path"]
    method = sku["method"].upper()
    params = GET_PARAMS.get(sid) if method == "GET" else None
    body = POST_BODIES.get(sid) if method == "POST" else None
    print(f"IGNITE {sid} {xrp} XRP bal={bal:.4f}", flush=True)
    try:
        code, data, err = execute_x402_request(
            url, payload=body, method=method, params=params, timeout=180.0,
            pay_invoice=xrpl_mainnet_pay_invoice, session=session,
        )
        tx = None
        if isinstance(data, dict):
            tx = data.get("xrpl_tx_hash") or data.get("transaction") or data.get("tx_hash")
            # nested
            for k in ("payment", "settlement", "receipt"):
                nested = data.get(k)
                if isinstance(nested, dict) and not tx:
                    tx = nested.get("xrpl_tx_hash") or nested.get("transaction") or nested.get("hash")
        # also check PAYMENT-RESPONSE isn't in body; broker may not surface hash
        row = {
            "sku": sid, "status": "ok" if code == 200 else "fail",
            "http": code, "err": err, "xrp": xrp, "tx": tx,
            "explorer": f"https://livenet.xrpl.org/transactions/{tx}" if tx else None,
            "data_preview": {k: data.get(k) for k in list(data)[:8]} if isinstance(data, dict) else None,
        }
        results.append(row)
        print(f"  -> http={code} err={err} tx={tx}", flush=True)
    except Exception as e:
        results.append({"sku": sid, "status": "exception", "error": str(e)[:500], "xrp": xrp})
        print(f"  EXC {e}", flush=True)
        if "exceeds cap" in str(e).lower():
            continue

bal1 = get_bal()
print(f"bal_after {bal1:.6f} XRP", flush=True)
out = {
    "fund_tx": "B3086A40E21BF62D5C7D3BA2418C0F823382D61372F87966A25A3D7962DC2649",
    "fund_explorer": "https://livenet.xrpl.org/transactions/B3086A40E21BF62D5C7D3BA2418C0F823382D61372F87966A25A3D7962DC2649",
    "buyer": BUYER.classic_address,
    "bal_before": bal0,
    "bal_after": bal1,
    "results": results,
}
out_path = ROOT / "artifacts" / "t54_ignition_results.json"
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
ok = sum(1 for r in results if r.get("status") == "ok")
print(f"DONE ok={ok}/{len(results)} wrote {out_path}", flush=True)
