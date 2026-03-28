#!/usr/bin/env python3
"""
Discover x402 marketplaces and invoke them. Tests swarm interaction with Arcana,
x402 Bazaar, Agoragentic, x402 test echo, and our own Celo api_402.
Smart hybrid: Testnet=faucet; Mainnet=Celo facilitator or LI.FI bridge. Only Celo+XRPL wallets.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))
sys.path.insert(0, str(root / "scripts"))

from dotenv import load_dotenv
load_dotenv(root / ".env", override=True)

os.chdir(root / "packages" / "agents")

FACILITATOR_FIRST = "--facilitator-first" in sys.argv


def _ensure_funds(provider_id: str, is_testnet: bool, min_usdc: float = 0.05) -> None:
    try:
        from bridge_utils import ensure_base_sepolia_test_usdc, ensure_base_usdc_for_x402
        if is_testnet:
            r = ensure_base_sepolia_test_usdc(min_usdc=min_usdc)
            if r.get("needs_funding"):
                pass
            elif r.get("balance_usdc"):
                print(f"  Balance: {r['balance_usdc']:.4f} USDC")
        else:
            r = ensure_base_usdc_for_x402(is_testnet=False, min_usdc=min_usdc)
            if r.get("tx_hash"):
                print(f"  Bridge: ok, tx={r['tx_hash'][:18]}...")
            elif not r.get("ok") and not r.get("skipped"):
                print(f"  Bridge: {r.get('error', r)}")
                if r.get("hint"):
                    print(f"  Hint: {r['hint']}")
    except ImportError:
        pass


def main() -> int:
    from external_commerce.discovery import Discovery
    from external_commerce.invoker import invoke_by_provider

    discovery = Discovery()
    providers = discovery.discover_from_config()
    print(f"Loaded {len(providers)} providers from config\n")

    include_remote = os.getenv("X402_DISCOVERY_ENABLED", "0").strip().lower() in {"1", "true", "yes"}
    if include_remote:
        try:
            remote = discovery.discover_from_remote(merge=True)
            print(f"Remote discovery: {len(remote)} additional providers\n")
        except Exception as e:
            print(f"Remote discovery skipped: {e}\n")

    invokable = [p for p in providers if p.resource_url and p.resource_url.startswith("http")]
    pay_flow = [p for p in invokable if (p.metadata or {}).get("payment_flow") not in ("none",)]

    print("=" * 60)
    print("INVOKABLE PROVIDERS (with resource_url)")
    print("=" * 60)
    for p in invokable[:12]:
        flow = (p.metadata or {}).get("payment_flow", "?")
        print(f"  {p.provider_id}: {p.resource_url[:60]}... [flow={flow}]")

    print("\n" + "=" * 60)
    print("TEST INVOKE: x402-test-echo (Base Sepolia, ~$0.01 USDC)")
    print("=" * 60)
    sys.path.insert(0, str(root / "scripts"))
    try:
        from bridge_utils import ensure_base_usdc_for_x402
        br = ensure_base_usdc_for_x402(is_testnet=True, min_usdc=0.05)
        if br.get("tx_hash"):
            print(f"  Bridge: ok, tx={br['tx_hash'][:18]}...")
    except ImportError:
        pass

    test = next((p for p in providers if p.provider_id == "x402-test-echo"), None)
    if not test:
        test = next((p for p in providers if "echo" in (p.provider_name or "").lower()), None)
    if test:
        status, data, err = invoke_by_provider(test, params={"msg": "swarm-hello"}, timeout=30)
        print(f"  Status: {status}, err={err}")
        if data:
            print(f"  Response: {json.dumps(data, indent=2)[:500]}")
        if status != 200 and err:
            if "no_buyer_key" in str(err):
                print("\n  To pay: fund ROOT_STRATEGIST on Celo Sepolia; bridge auto-runs (or fund Base directly)")
            elif "payment_preparation" in str(err):
                print("\n  To pay: pip install x402; fund Celo Sepolia (bridge) or Base Sepolia directly")
    else:
        print("  No x402-test-echo provider found")

    print("\n" + "=" * 60)
    print("TEST INVOKE: swarm-self (Celo, our api_402)")
    print("=" * 60)
    self_p = next((p for p in providers if p.provider_id == "swarm-self"), None)
    api_process = None
    api_ready = False
    if self_p and "127.0.0.1" in (self_p.resource_url or ""):
        for attempt in range(20):
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8042/health", timeout=2)
                api_ready = True
                break
            except Exception:
                pass
            if attempt == 0:
                try:
                    import subprocess
                    agents_dir = root / "packages" / "agents"
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
                except Exception as e:
                    print(f"  Could not start api_402: {e}")
                    break
            time.sleep(0.5)
    if self_p and api_ready:
        status, data, err = invoke_by_provider(self_p, params={"q": "swarm marketplace test"}, timeout=90)
        print(f"  Status: {status}, err={err}")
        if data:
            print(f"  Response: {json.dumps(data, indent=2)[:400]}")
        if api_process:
            try:
                api_process.terminate()
            except Exception:
                pass
    elif self_p and not api_ready:
        print("  Skipped (api_402 not ready in time)")
    else:
        print("  No swarm-self provider")

    print("\n" + "=" * 60)
    print("TEST INVOKE: Arcana Price Oracle (Base Sepolia x402, ~$0.01 USDC)")
    print("=" * 60)
    _ensure_funds("arcana-x402", is_testnet=True, min_usdc=0.05)

    arcana = next((p for p in providers if p.provider_id == "arcana-x402"), None)
    if arcana:
        status, data, err = invoke_by_provider(
            arcana,
            method="GET",
            params={"symbol": "ETH"},
            timeout=45,
        )
        print(f"  Status: {status}, err={err}")
        if data:
            snippet = json.dumps(data, indent=2)
            print(f"  Response: {snippet[:450]}...")
        if status != 200 and err:
            if "no_buyer_key" in str(err):
                print("\n  To pay: fund ROOT_STRATEGIST on Celo Sepolia; bridge auto-runs (or fund Base Sepolia)")
            elif "payment" in str(err).lower() or "402" in str(err):
                print("\n  To pay: fund Celo Sepolia (bridge) or Base Sepolia with test USDC")
            elif "502" in str(err) or "resolve" in (err or "").lower() or "connection" in (err or "").lower():
                print("\n  Note: api.arcana.markets may be down or not publicly deployed")
    else:
        print("  No arcana-x402 provider found")

    print("\n" + "=" * 60)
    print("TEST INVOKE: Agoragentic x402 (Base mainnet, Text Summarizer ~$0.10 USDC)")
    print("=" * 60)
    _ensure_funds("agoragentic", is_testnet=False, min_usdc=0.15)

    agora_cfg = next((p for p in providers if p.provider_id == "agoragentic"), None)
    if agora_cfg:
        try:
            import requests
            r = requests.get("https://agoragentic.com/api/x402/listings", timeout=15)
            listings_data = r.json() if r.ok else {}
            listings = listings_data.get("listings", [])
            summarizer = next(
                (l for l in listings if "summariz" in (l.get("name") or "").lower() or "summariz" in (l.get("description") or "").lower()),
                listings[0] if listings else None,
            )
            if summarizer:
                listing_id = summarizer.get("id")
                invoke_url = f"https://agoragentic.com/api/x402/invoke/{listing_id}"
                meta = dict(agora_cfg.metadata or {})
                meta["payment_flow"] = "facilitator"
                from external_commerce.schemas import ExternalProvider
                agora_invoke = ExternalProvider(
                    provider_id="agoragentic",
                    provider_name=agora_cfg.provider_name,
                    source_type=agora_cfg.source_type,
                    discovery_source=agora_cfg.discovery_source,
                    protocol_type=agora_cfg.protocol_type,
                    network="eip155:8453",
                    facilitator_url="https://x402.org/facilitator",
                    resource_url=invoke_url,
                    supported_assets=agora_cfg.supported_assets,
                    pricing_model=agora_cfg.pricing_model,
                    categories=agora_cfg.categories,
                    metadata=meta,
                )
                status, data, err = invoke_by_provider(
                    agora_invoke,
                    method="POST",
                    json_body={"input": {"text": "Agent-to-agent commerce enables autonomous payment for AI services."}},
                    timeout=45,
                )
                print(f"  Listing: {summarizer.get('name', '?')} (${summarizer.get('price_usdc', '?')})")
                print(f"  Status: {status}, err={err}")
                if data:
                    snippet = json.dumps(data, indent=2)
                    print(f"  Response: {snippet[:450]}...")
                if status != 200 and err:
                    if "no_buyer_key" in str(err):
                        print("\n  To pay: fund ROOT_STRATEGIST on Celo; bridge auto-runs (or fund Base mainnet)")
                    elif "payment" in str(err).lower() or "402" in str(err):
                        print("\n  To pay: fund Celo (bridge) or Base mainnet with USDC")
            else:
                print("  No x402 listings found")
        except Exception as e:
            print(f"  Error: {e}")

        api_key = os.getenv("AGORAGENTIC_API_KEY", "").strip()
        if api_key and api_key.startswith("amk_"):
            print("\n  --- Bearer-auth execute (with AGORAGENTIC_API_KEY) ---")
            try:
                import requests
                r = requests.post(
                    "https://agoragentic.com/api/execute",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"task": "echo", "input": {"message": "swarm invoke test"}},
                    timeout=30,
                )
                data = r.json() if "application/json" in (r.headers.get("content-type") or "") else {"raw": r.text[:200]}
                print(f"  Status: {r.status_code}")
                if r.status_code == 200:
                    print(f"  Response: {json.dumps(data, indent=2)[:300]}...")
                else:
                    print(f"  Error: {data.get('error', data)}")
            except Exception as e:
                print(f"  Error: {e}")
    else:
        print("  No agoragentic provider found")

    print("\n" + "=" * 60)
    print("DISCOVERY (no payment)")
    print("=" * 60)
    bazaar = next((p for p in providers if p.provider_id == "x402-bazaar-discovery"), None)
    if bazaar:
        status, data, err = invoke_by_provider(bazaar, timeout=15)
        print(f"  x402-bazaar-discovery (Coinbase): status={status}")
        if status == 200 and data and isinstance(data, dict):
            items = data.get("items", [])
            for i, item in enumerate(items[:3]):
                url = (item.get("resource") or item.get("url") or "?")[:60]
                print(f"    - {url}")
            if items:
                print(f"    ... {len(items)} total items")
        elif err:
            print(f"    error: {err}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
