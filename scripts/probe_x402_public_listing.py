#!/usr/bin/env python3
"""
Probe your public Base x402 seller URL, run a dry-run buyer GET, and check remote discovery APIs
for your listing (so you are not guessing).

Loads repo-root .env (and .env.local). Requires X402_SELLER_PUBLIC_URL (or X402_SELLER_PROBE_URL).

  python scripts/probe_x402_public_listing.py
  python scripts/probe_x402_public_listing.py --url https://host/x402/v1/query
  python scripts/probe_x402_public_listing.py --skip-remote
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(root / ".env", override=True)
        if (root / ".env.local").exists():
            load_dotenv(root / ".env.local", override=True)
    except ImportError:
        pass


def _listing_url() -> str:
    u = (os.getenv("X402_SELLER_PUBLIC_URL") or os.getenv("X402_SELLER_PROBE_URL") or "").strip()
    return u


def _normalize(s: str) -> str:
    s = s.strip().rstrip("/")
    if "?" in s:
        s = s.split("?", 1)[0]
    return s


def _has_payment_shape(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    if obj.get("accepts"):
        return True
    pay = obj.get("payment") or obj.get("paymentRequirements") or obj.get("requirements")
    return pay is not None


def probe_health(listing: str, timeout: float) -> tuple[int, str]:
    p = urlparse(listing)
    if not p.scheme or not p.netloc:
        return 0, "skip (bad URL)"
    health = f"{p.scheme}://{p.netloc}/health"
    req = urllib.request.Request(health, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:600]
            return resp.getcode(), body
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", errors="replace") if e.fp else "")[:600]
    except Exception as ex:
        return 0, str(ex)


def probe_unpaid_402(listing: str, timeout: float) -> tuple[bool, str]:
    sep = "&" if "?" in listing else "?"
    full = f"{listing}{sep}q=listing-probe"
    req = urllib.request.Request(full, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as ex:
        return False, f"request error: {ex}"
    if code != 402:
        return False, f"expected HTTP 402, got {code}: {body[:400]}"
    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        return False, "402 body is not JSON"
    if not _has_payment_shape(data):
        return False, "402 JSON missing payment shape (accepts / payment fields)"
    return True, json.dumps(data, indent=2)[:1200]


DISCOVERY_URLS: list[tuple[str, str]] = [
    ("x402-discovery-api", "https://x402-discovery-api.onrender.com/discover"),
    ("cdp-bazaar", "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"),
    ("payai", "https://facilitator.payai.network/discovery/resources"),
]


def _fetch_discovery_json(name: str, url: str, timeout: float) -> tuple[int, object | None, str]:
    try:
        import requests

        if "discover" in url and "onrender" in url:
            r = requests.get(url, params={"limit": 200}, timeout=timeout)
        else:
            r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return r.status_code, None, r.text[:300]
        return 200, r.json(), ""
    except Exception as e:
        return 0, None, str(e)


def _haystack_contains_listing(haystack: str, listing_norm: str, host: str) -> bool:
    haystack_l = haystack.lower()
    if listing_norm.lower() in haystack_l:
        return True
    if host and host.lower() in haystack_l:
        return True
    return False


def search_remote_discovery(listing_norm: str, host: str, timeout: float) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, url in DISCOVERY_URLS:
        code, data, err = _fetch_discovery_json(name, url, timeout)
        row: dict[str, object] = {"source": name, "url": url, "http_status": code}
        if code != 200 or data is None:
            row["match"] = False
            row["detail"] = err or "non-200"
            results.append(row)
            continue
        blob = json.dumps(data, ensure_ascii=False)
        row["match"] = _haystack_contains_listing(blob, listing_norm, host)
        row["detail"] = "substring match on full URL or host" if row["match"] else "URL not found in response body"
        row["response_chars"] = len(blob)
        results.append(row)
    return results


def dry_run_buyer_invoke(listing: str, timeout: float) -> tuple[int, str]:
    os.environ.setdefault("X402_DRY_RUN", "1")
    from external_commerce.x402_buyer import X402Buyer

    net = (os.getenv("X402_SELLER_NETWORK") or "eip155:84532").strip()
    fac = os.getenv("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator").strip()
    buyer = X402Buyer(facilitator_url=fac, network=net, dry_run=True)
    status, data, err = buyer.invoke(listing, method="GET", params={"q": "dry-run-buyer"}, timeout=timeout)
    summary = f"status={status} err={err!r}"
    if data:
        summary += f" keys={list(data.keys())[:12] if isinstance(data, dict) else 'n/a'}"
    return status, summary


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser(description="Probe public x402 listing + remote discovery visibility")
    ap.add_argument("--url", default="", help="Override X402_SELLER_PUBLIC_URL")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--skip-remote", action="store_true", help="Only probe + dry-run (no discovery GETs)")
    args = ap.parse_args()

    listing = (args.url or _listing_url()).strip()
    if not listing.startswith("http"):
        print(
            "Set X402_SELLER_PUBLIC_URL (or X402_SELLER_PROBE_URL) in .env, "
            "or pass --url https://.../x402/v1/query",
            file=sys.stderr,
        )
        return 2

    listing_norm = _normalize(listing)
    host = urlparse(listing).netloc or ""

    print("=== 0) GET /health (same origin as listing) ===", flush=True)
    hc, hbody = probe_health(listing, args.timeout)
    print(f"health HTTP {hc}", flush=True)
    if hc == 200:
        print(hbody[:800], flush=True)
    else:
        print(
            f"WARN: /health not OK — seller may be down or ngrok URL stale. Body: {hbody[:400]}",
            file=sys.stderr,
            flush=True,
        )

    print("\n=== 1) Unpaid GET (expect 402 + payment JSON) ===", flush=True)
    ok, detail = probe_unpaid_402(listing, args.timeout)
    if ok:
        print("OK", listing_norm, flush=True)
        print(detail[:2000], flush=True)
    else:
        print("FAIL", detail, file=sys.stderr, flush=True)
        return 1

    print("\n=== 2) Dry-run buyer invoke (X402Buyer, X402_DRY_RUN=1) ===")
    st, summ = dry_run_buyer_invoke(listing, args.timeout)
    print(summ)
    if st == 402:
        print("(402 expected without signing; dry_run uses plain HTTP client)")
    elif st != 200:
        print(f"Note: unexpected status {st} for dry-run path", file=sys.stderr)

    if args.skip_remote:
        print("\n=== 3) Remote discovery (skipped) ===")
        return 0

    print("\n=== 3) Remote discovery — is your URL in the catalog response? ===")
    print(f"Looking for: {listing_norm}")
    rows = search_remote_discovery(listing_norm, host, args.timeout)
    any_match = False
    for r in rows:
        m = bool(r.get("match"))
        any_match = any_match or m
        print(f"  [{r['source']}] match={m} http={r['http_status']} {r.get('detail', '')}")
    if not any_match:
        print(
            "\nWARNING: No remote catalog response contained your URL/host substring. "
            "Common until you are explicitly indexed or listed; passive uptime is not enough.",
            file=sys.stderr,
        )
        return 0
    print("\nOK: At least one remote catalog response contained your URL or host.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
