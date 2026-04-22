#!/usr/bin/env python3
"""Check passive discovery URLs on the public API host (no payment)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = (
    os.getenv("MARKETPLACE_PUBLIC_BASE_URL")
    or os.getenv("X402_SELLER_PUBLIC_URL", "").split("/x402")[0]
    or "https://api.agentic-swarm-marketplace.com"
).rstrip("/")

PATHS = (
    "/.well-known/x402.json",
    "/.well-known/agent-card.json",
    "/.well-known/mcp.json",
    "/.well-known/api-catalog",
)


def main() -> int:
    ok = 0
    for path in PATHS:
        url = f"{BASE}{path}"
        accept = (
            "application/linkset+json, application/json"
            if path == "/.well-known/api-catalog"
            else "application/json"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": "AgenticSwarmMarketplace-probe/1.0 (+https://agentic-swarm-marketplace.com)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                code = resp.getcode()
                ct = resp.headers.get("Content-Type", "")
                body = resp.read(4000)
        except Exception as e:
            print(f"FAIL {path} error={e!r}")
            continue
        if code != 200:
            print(f"FAIL {path} status={code}")
            continue
        if path == "/.well-known/api-catalog":
            if "application/linkset+json" not in ct.lower():
                print(f"WARN {path} status={code} content-type={ct!r}")
        elif "application/json" not in ct and "json" not in ct:
            print(f"WARN {path} status={code} content-type={ct!r}")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            print(f"FAIL {path} not valid JSON (first 120 chars): {body[:120]!r}")
            continue
        if path == "/.well-known/api-catalog":
            linkset = data.get("linkset")
            if not isinstance(linkset, list) or not linkset:
                print(f"FAIL {path} missing or empty linkset")
                continue
            entry = linkset[0]
            missing = next(
                (rel for rel in ("anchor", "service-desc", "service-doc", "status") if rel not in entry),
                None,
            )
            if missing:
                print(f"FAIL {path} linkset[0] missing {missing!r}")
                continue
            print(f"OK   {path} status={code} bytes={len(body)}")
            ok += 1
            continue
        print(f"OK   {path} status={code} bytes={len(body)}")
        ok += 1
    if ok == len(PATHS):
        print(f"All {ok} discovery URLs OK on {BASE}")
        return 0
    print(f"Only {ok}/{len(PATHS)} passed — deploy seller+marketplace with well_known_discovery.py or fix Cloudflare/Caddy routing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
