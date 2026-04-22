#!/usr/bin/env python3
"""Verify public API host: /health + /.well-known/* (passive discovery)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

DEFAULT_BASE = "https://api.agentic-swarm-marketplace.com"


def _mcp_server_card_ok(obj: dict) -> bool:
    si = obj.get("serverInfo")
    if not isinstance(si, dict) or not si.get("name") or not si.get("version"):
        return False
    tr = obj.get("transport")
    if not isinstance(tr, dict) or not tr.get("type") or not tr.get("endpoint"):
        return False
    return isinstance(obj.get("capabilities"), dict)


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
        (f"{base}/.well-known/mcp/server-card.json", "__mcp_server_card__", None),
        (f"{base}/.well-known/mcp/server-cards.json", "__mcp_server_cards__", None),
        (
            f"{base}/.well-known/api-catalog",
            "linkset",
            "application/linkset+json, application/json",
        ),
        (f"{base}/.well-known/openid-configuration", "__oauth_discovery__", None),
        (f"{base}/.well-known/oauth-authorization-server", "__oauth_discovery__", None),
        (f"{base}/.well-known/oauth-protected-resource", "__oauth_pr__", None),
        (f"{base}/.well-known/jwks.json", "__jwks__", None),
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
        if key == "__oauth_discovery__":
            need = ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri")
            if any(k not in j for k in need):
                print(f"FAIL {url} must include {need}")
                continue
            print(f"OK   {url} (issuer={str(j.get('issuer'))[:56]}...)")
            ok += 1
            continue
        if key == "__oauth_pr__":
            if "resource" not in j:
                print(f"FAIL {url} missing resource")
                continue
            servers = j.get("authorization_servers")
            if not isinstance(servers, list) or not servers:
                print(f"FAIL {url} authorization_servers must be non-empty list")
                continue
            scopes = j.get("scopes_supported")
            if not isinstance(scopes, list) or not scopes:
                print(f"FAIL {url} scopes_supported must be non-empty list")
                continue
            print(f"OK   {url} (resource={str(j.get('resource'))[:48]}...)")
            ok += 1
            continue
        if key == "__jwks__":
            if not isinstance(j.get("keys"), list):
                print(f"FAIL {url} missing keys array")
                continue
            print(f"OK   {url} (keys={len(j['keys'])})")
            ok += 1
            continue
        if key == "__mcp_server_card__":
            if not isinstance(j, dict) or not _mcp_server_card_ok(j):
                print(f"FAIL {url} invalid MCP server card")
                continue
            si = j.get("serverInfo") or {}
            print(f"OK   {url} (name={si.get('name')!r})")
            ok += 1
            continue
        if key == "__mcp_server_cards__":
            if not isinstance(j, list) or not j:
                print(f"FAIL {url} must be non-empty JSON array")
                continue
            if not all(isinstance(c, dict) and _mcp_server_card_ok(c) for c in j):
                print(f"FAIL {url} invalid server card entry")
                continue
            print(f"OK   {url} (count={len(j)})")
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
