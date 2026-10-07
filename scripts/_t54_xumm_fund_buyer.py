"""Fund saved ignition buyer from Xaman via XUMM push — one phone sign.
HARDENING: never overwrite AGENT_XRPL_WALLET_SEED if saved address is already funded.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from xrpl.wallet import Wallet

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)
load_dotenv(ROOT / ".env.local", override=True)
load_dotenv(ROOT / ".env.mainnet", override=False)

out = ROOT / "secrets" / "t54-ignition-buyer.env"
out.parent.mkdir(parents=True, exist_ok=True)

def account_xrp(addr: str) -> float | None:
    import json, urllib.request
    body = json.dumps({"method":"account_info","params":[{"account":addr,"ledger_index":"validated","strict":True}]}).encode()
    try:
        d = json.loads(urllib.request.urlopen(urllib.request.Request("https://xrplcluster.com", data=body, headers={"Content-Type":"application/json"}), timeout=20).read())
        if "error" in d.get("result", {}):
            return None
        return int(d["result"]["account_data"]["Balance"]) / 1e6
    except Exception:
        return None

buyer = None
if out.exists():
    vals = {}
    for line in out.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k,_,v = line.partition("=")
            vals[k.strip()] = v.strip()
    seed = vals.get("AGENT_XRPL_WALLET_SEED", "")
    addr = vals.get("AGENT_XRPL_WALLET_ADDRESS", "")
    if seed:
        w = Wallet.from_seed(seed)
        bal = account_xrp(w.classic_address)
        print("existing_buyer", w.classic_address, "bal", bal)
        if bal is not None and bal >= 1.0:
            print("KEEP existing funded buyer seed — refuse overwrite")
            buyer = w
        elif addr and addr != w.classic_address:
            print("WARN address mismatch in env file", addr, "vs", w.classic_address)
            stranded = account_xrp(addr)
            print("stranded_listed_addr", addr, "bal", stranded)
            if stranded and stranded >= 1.0:
                print("FATAL: funded address in file has no matching seed. Refusing to create replacement until resolved.")
                sys.exit(10)
            buyer = w  # reuse unfunded seeded buyer
        else:
            buyer = w

if buyer is None:
    buyer = Wallet.create()
    out.write_text(
        "\n".join([
            "# Ephemeral T54 ignition buyer — DO NOT COMMIT",
            f"AGENT_XRPL_WALLET_SEED={buyer.seed}",
            f"AGENT_XRPL_WALLET_ADDRESS={buyer.classic_address}",
            "X402_BROKER_PAY_MODE=xrpl_mainnet",
            "X402_BROKER_MAINNET_ACK=1",
            "T54_XRPL_ENABLED=1",
            "T54_XRPL_MODE=mainnet",
            "MAX_XRP_SPEND_PER_TX=1.5",
            "",
        ]),
        encoding="utf-8",
    )
    print("buyer_saved", buyer.classic_address)
else:
    # ensure address field matches seed
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    if f"AGENT_XRPL_WALLET_ADDRESS={buyer.classic_address}" not in text:
        out.write_text(
            "\n".join([
                "# Ephemeral T54 ignition buyer — DO NOT COMMIT",
                f"AGENT_XRPL_WALLET_SEED={buyer.seed}",
                f"AGENT_XRPL_WALLET_ADDRESS={buyer.classic_address}",
                "X402_BROKER_PAY_MODE=xrpl_mainnet",
                "X402_BROKER_MAINNET_ACK=1",
                "T54_XRPL_ENABLED=1",
                "T54_XRPL_MODE=mainnet",
                "MAX_XRP_SPEND_PER_TX=1.5",
                "",
            ]),
            encoding="utf-8",
        )
    print("buyer_reused", buyer.classic_address)

print("env_file", out)

key = (os.getenv("XUMM_API_KEY") or "").strip()
secret = (os.getenv("XUMM_API_SECRET") or "").strip()
user_token = (os.getenv("XUMM_USER_TOKEN") or "").strip()
if not key or not secret:
    print("FATAL missing XUMM creds")
    sys.exit(2)

# If already funded, skip XUMM
bal = account_xrp(buyer.classic_address)
if bal is not None and bal >= 2.0:
    print("STATUS already_funded", bal)
    sys.exit(0)

amount_drops = "5000000"
body = {
    "txjson": {
        "TransactionType": "Payment",
        "Destination": buyer.classic_address,
        "Amount": amount_drops,
    },
    "options": {"submit": True, "expire": 60},
    "custom_meta": {
        "instruction": f"ASM T54 ignition — fund buyer {buyer.classic_address} with 5 XRP",
    },
}
if user_token:
    body["user_token"] = user_token

headers = {
    "x-api-key": key,
    "x-api-secret": secret,
    "Content-Type": "application/json",
}
base = "https://xumm.app/api/v1"
r = requests.post(f"{base}/platform/payload", headers=headers, json=body, timeout=60)
print("create_http", r.status_code)
if r.status_code >= 400:
    print("create_body", r.text[:500])
    sys.exit(3)
created = r.json()
uuid = created.get("uuid")
nxt = created.get("next") or {}
refs = created.get("refs") or {}
sign_url = nxt.get("always")
print("uuid", uuid)
print("sign_url", sign_url)
print("qr", refs.get("qr_png"))
# write URL immediately for parent
try:
    Path("/workspace/scratch/t54-xaman-sign-url.txt").write_text(sign_url or "", encoding="utf-8")
except Exception:
    pass
(ROOT / "artifacts" / "t54_xumm_fund_meta.json").write_text(
    __import__("json").dumps({"uuid": uuid, "sign_url": sign_url, "buyer": buyer.classic_address, "amount_drops": amount_drops, "expire_min": 60}, indent=2),
    encoding="utf-8",
)

deadline = time.time() + 180
signed = False
txid = None
while time.time() < deadline:
    time.sleep(4)
    pr = requests.get(f"{base}/platform/payload/{uuid}", headers=headers, timeout=60)
    data = pr.json()
    meta = data.get("meta") or {}
    if meta.get("resolved"):
        signed = bool(meta.get("signed"))
        resp = data.get("response") or {}
        txid = resp.get("txid")
        print("resolved signed=", signed, "txid=", txid)
        break
    print("waiting...", int(deadline - time.time()), "s left")

if not signed:
    print("STATUS waiting_for_xaman_sign")
    print("ACTION Open sign_url on phone / Xaman to fund ignition buyer")
    sys.exit(4)

print("fund_explorer", f"https://livenet.xrpl.org/transactions/{txid}")
print("STATUS funded_via_xaman")
