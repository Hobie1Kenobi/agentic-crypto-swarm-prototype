#!/usr/bin/env python3
"""
CI / curl-friendly probe: unpaid GET must return HTTP 402 with JSON payment requirements.

Does not send USDC. Use after: uvicorn api_seller_x402:create_app --port 8043

Env:
  X402_SELLER_PROBE_URL — full query URL (default http://127.0.0.1:8043/x402/v1/query)
  X402_SELLER_PUBLIC_URL — alias for probe URL if PROBE unset
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def _default_url() -> str:
    return (
        (os.getenv("X402_SELLER_PROBE_URL") or "").strip()
        or (os.getenv("X402_SELLER_PUBLIC_URL") or "").strip()
        or "http://127.0.0.1:8043/x402/v1/query"
    )


def _has_payment_shape(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    if obj.get("accepts"):
        return True
    pay = obj.get("payment") or obj.get("paymentRequirements") or obj.get("requirements")
    if pay is not None:
        return True
    if "error" in obj and obj.get("message"):
        return "payment" in str(obj).lower() or "402" in str(obj.get("message", "")).lower()
    return len(obj) > 0


def _headers_indicate_payment(headers) -> bool:
    if not headers:
        return False
    for name in ("PAYMENT-REQUIRED", "Payment-Required", "WWW-Authenticate"):
        if headers.get(name):
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Probe x402 seller returns 402 + payment JSON")
    p.add_argument("--url", default=_default_url(), help="Full ?q= query endpoint")
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args()

    sep = "&" if "?" in args.url else "?"
    full = f"{args.url}{sep}q=ci-probe"

    req = urllib.request.Request(full, method="GET", headers={"Accept": "application/json"})
    hdrs = None
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        hdrs = e.headers
    except Exception as ex:
        print(f"probe FAIL: request error: {ex}", file=sys.stderr)
        return 2

    if code != 402:
        print(f"probe FAIL: expected HTTP 402, got {code}", file=sys.stderr)
        print(body[:800], file=sys.stderr)
        return 1

    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        print("probe FAIL: 402 body is not JSON", file=sys.stderr)
        print(body[:800], file=sys.stderr)
        return 1

    if not _has_payment_shape(data) and not _headers_indicate_payment(hdrs):
        print("probe FAIL: 402 missing payment info (no accepts in JSON and no PAYMENT-REQUIRED header)", file=sys.stderr)
        print(json.dumps(data, indent=2)[:1200], file=sys.stderr)
        return 1

    print(f"probe OK: 402 with payment requirements ({full})")
    print(json.dumps(data, indent=2)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
