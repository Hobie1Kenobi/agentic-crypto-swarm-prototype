#!/usr/bin/env python3
"""
Read ngrok local API and set X402_SELLER_PUBLIC_URL in repo .env.

Picks the tunnel whose local addr targets port 8043 (x402 facilitator seller).
With scripts/ngrok-dual-stack.yml, multiple tunnels share the same 4040 API.

Optional: --api-base http://127.0.0.1:4041 if you run a second ngrok with --web-addr.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _tunnel_for_port(tunnels: list[dict], port: int) -> dict | None:
    needle = f":{port}"
    for t in tunnels:
        addr = (t.get("config") or {}).get("addr") or ""
        addr = str(addr).lower()
        if needle in addr or addr.endswith(str(port)):
            return t
    return None


def _upsert_env(env_path: Path, key: str, value: str) -> None:
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    line = f"{key}={value}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pat.search(text):
        new = pat.sub(line, text)
    else:
        sep = "\n" if text and not text.endswith("\n") else ""
        new = text + sep + line + "\n"
    env_path.write_text(new, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Set X402_SELLER_PUBLIC_URL from ngrok tunnel to port 8043")
    ap.add_argument(
        "--api-base",
        default="http://127.0.0.1:4040",
        help="ngrok local API origin (default 4040)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=8043,
        help="Local port the x402 seller listens on",
    )
    ap.add_argument(
        "--path",
        default="/x402/v1/query",
        help="Path appended to public origin",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    url = f"{args.api_base.rstrip('/')}/api/tunnels"
    try:
        raw = urllib.request.urlopen(url, timeout=8).read()
    except (urllib.error.URLError, TimeoutError) as e:
        print("ngrok API not reachable (is ngrok running?)", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    data = json.loads(raw.decode("utf-8"))
    tunnels = data.get("tunnels") or []
    if not tunnels:
        print("no tunnels in ngrok response", file=sys.stderr)
        return 1
    tun = _tunnel_for_port(tunnels, args.port)
    if not tun:
        print(
            f"No ngrok tunnel found for localhost:{args.port}. "
            f"Use dual config: npm run ngrok:dual (see scripts/ngrok-dual-stack.yml), "
            f"or ngrok http {args.port}",
            file=sys.stderr,
        )
        return 1
    base = (tun.get("public_url") or "").strip().rstrip("/")
    if not base.startswith("https://"):
        print("unexpected public_url", tun, file=sys.stderr)
        return 1
    path = args.path if str(args.path).startswith("/") else f"/{args.path}"
    full = f"{base}{path}"
    _upsert_env(env_path, "X402_SELLER_PUBLIC_URL", full)
    print(f"Wrote X402_SELLER_PUBLIC_URL to {env_path}")
    mainnet = root / ".env.mainnet"
    if mainnet.exists():
        _upsert_env(mainnet, "X402_SELLER_PUBLIC_URL", full)
        print(f"Wrote X402_SELLER_PUBLIC_URL to {mainnet}")
    print(full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
