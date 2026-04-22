#!/usr/bin/env python3
"""Verify public API host: /health + /.well-known/* (passive discovery)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

DEFAULT_BASE = "https://api.agentic-swarm-marketplace.com"


def _get(url: str, accept: str | None = None) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": accept or "application/json",
            "User-Agent": "AgenticSwarmMarketplace-verify/1.0 (+https://agentic-swarm-marketplace.com)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.getcode(), r.read(8000).decode("utf-8", errors="replace")


def main() -> int:
    base = (os.getenv("MARKETPLACE_PUBLIC_BASE_URL") or DEFAULT_BASE).rstrip("/")
    ok = 0
    checks = [
        (f"{base}/health", "status", None),
        (f"{base}/.well-known/x402.json", "version", None),
        (f"{base}/.well-known/agent-card.json", "name", None),
        (f"{base}/.well-known/mcp.json", "mcp_endpoint", None),
        (
            f"{base}/.well-known/api-catalog",
            "linkset",
            "application/linkset+json, application/json",
        ),
    ]
    for url, key, accept in checks:
        try:
            code, body = _get(url, accept)
        except Exception as e:
            print(f"FAIL {url} err={e!r}")
            continue
        if code != 200:
            print(f"FAIL {url} http={code}")
            continue
        try:
            j = json.loads(body)
        except json.JSONDecodeError:
            print(f"FAIL {url} not JSON")
            continue
        if key == "linkset":
            ls = j.get("linkset")
            if not isinstance(ls, list) or not ls:
                print(f"FAIL {url} missing or empty linkset")
                continue
            entry = ls[0]
            need = ("anchor", "service-desc", "service-doc", "status")
            if any(k not in entry for k in need):
                print(f"FAIL {url} linkset[0] must include {need}")
                continue
            print(f"OK   {url} (anchor={str(entry.get('anchor'))[:56]}...)")
            ok += 1
            continue
        if key not in j:
            print(f"FAIL {url} missing key {key!r}")
            continue
        print(f"OK   {url} ({key}={str(j[key])[:60]}...)")
        ok += 1
    if ok == len(checks):
        print(f"All {ok} public API checks passed ({base})")
        return 0
    print(f"Only {ok}/{len(checks)} passed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
