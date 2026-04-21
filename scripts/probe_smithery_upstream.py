#!/usr/bin/env python3
"""Probe public stack the same way Smithery hits it: MCP streamable HTTP + API health.

Cloudflare/WAF may return 403 on /mcp unless User-Agent matches allowlisted bots
(e.g. SmitheryBot). See documentation/operations/CLOUDFLARE_CACHE_AND_SECURITY.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.agentic-swarm-marketplace.com"
SMITHERY_UA = "SmitheryBot/1.0 (+https://smithery.ai)"


def _post_json(url: str, payload: dict, *, timeout: float, user_agent: str) -> tuple[int, float, bytes]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": user_agent,
        },
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(2_000_000)
        return r.status, (time.perf_counter() - t0) * 1000, raw


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe api host + MCP /mcp (Smithery-style UA)")
    ap.add_argument("--base", default=os.getenv("MARKETPLACE_PUBLIC_BASE_URL") or DEFAULT_BASE)
    ap.add_argument("--user-agent", default=os.getenv("MCP_PROBE_USER_AGENT") or SMITHERY_UA)
    ap.add_argument("--cheap-tool", default="t54_list_operations", help="tools/call name (no paid HTTP)")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    mcp_url = f"{base}/mcp"

    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "probe_smithery_upstream", "version": "1.0"},
        },
    }
    list_tools = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    call_cheap = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": args.cheap_tool, "arguments": {}},
    }

    ok = 0
    for label, payload in (
        ("initialize", init),
        ("tools/list", list_tools),
        ("tools/call:" + args.cheap_tool, call_cheap),
    ):
        try:
            status, ms, raw = _post_json(mcp_url, payload, timeout=args.timeout, user_agent=args.user_agent)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8", "replace")[:500]
            except Exception:
                err_body = ""
            print(f"FAIL {label} http={e.code} {e.reason!r} body={err_body!r}")
            continue
        except Exception as e:
            print(f"FAIL {label} err={e!r}")
            continue
        try:
            j = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"OK   {label} http={status} ms={ms:.0f} (non-JSON body len={len(raw)})")
            ok += 1
            continue
        if "error" in j:
            print(f"FAIL {label} rpc_error={j['error']}")
            continue
        extra = ""
        if label == "tools/list":
            n = len(j.get("result", {}).get("tools", []))
            extra = f" tools={n}"
        print(f"OK   {label} http={status} ms={ms:.0f}{extra}")
        ok += 1

    if ok == 3:
        print("MCP chain OK (initialize -> tools/list -> cheap tools/call)")
        return 0
    print(f"MCP partial {ok}/3")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
