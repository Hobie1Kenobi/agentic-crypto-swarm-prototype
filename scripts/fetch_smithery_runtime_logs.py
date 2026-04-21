#!/usr/bin/env python3
"""Fetch Smithery runtime logs (per-invocation) for the published MCP server.

Requires SMITHERY_API_KEY in .env.local (gitignored). See:
  documentation/operations/SMITHERY_OBSERVABILITY.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def _load_env_local() -> None:
    p = root / ".env.local"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def main() -> int:
    ap = argparse.ArgumentParser(description="GET Smithery /servers/.../logs")
    ap.add_argument(
        "--qualified-name",
        default=os.getenv("SMITHERY_QUALIFIED_NAME", "hobiecunningham/agentic-swarm-marketplace"),
        help="Server qualified name (namespace/server)",
    )
    ap.add_argument("--limit", type=int, default=20, help="Max invocations (1-100)")
    ap.add_argument("--search", default="", help="Filter log text")
    ap.add_argument("--raw", action="store_true", help="Print JSON only")
    args = ap.parse_args()

    _load_env_local()
    key = (os.getenv("SMITHERY_API_KEY") or "").strip()
    if not key:
        print("Set SMITHERY_API_KEY in .env.local (see .env.example).", file=sys.stderr)
        return 1

    enc = urllib.parse.quote(args.qualified_name, safe="")
    q = urllib.parse.urlencode({"limit": min(100, max(1, args.limit))})
    if args.search:
        q += "&" + urllib.parse.urlencode({"search": args.search})
    url = f"https://api.smithery.ai/servers/{enc}/logs?{q}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "AgenticSwarmMarketplace-fetch-logs/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:2000]
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Request failed: {e!r}", file=sys.stderr)
        return 1

    if args.raw:
        print(body)
        return 0

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(body[:4000])
        return 0

    inv = data.get("invocations") or []
    total = data.get("total", len(inv))
    print(f"invocations={len(inv)} total_reported={total}\n")
    for i, row in enumerate(inv):
        rid = row.get("id", "")
        ts = row.get("timestamp", "")
        dur = row.get("duration") or {}
        wall = dur.get("wallMs", "?")
        resp = row.get("response") or {}
        status = resp.get("status", "?")
        outcome = resp.get("outcome", "?")
        req = row.get("request") or {}
        method = req.get("method", "")
        req_url = req.get("url", "")
        print(f"--- [{i + 1}] {ts} id={rid}")
        print(f"    http={status} outcome={outcome} wall_ms={wall}")
        print(f"    {method} {req_url[:120]}")
        for ex in row.get("exceptions") or []:
            print(f"    EXC {ex.get('name')}: {ex.get('message', '')[:200]}")
        for log in (row.get("logs") or [])[-5:]:
            print(f"    [{log.get('level')}] {log.get('message', '')[:200]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
