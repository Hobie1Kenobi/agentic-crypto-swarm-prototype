#!/usr/bin/env python3
"""
Write docs/endpoints.json from repo-root .env (T54, Base x402, optional marketplace origin).

Run after ngrok sync or when your public URLs change, then commit docs/endpoints.json
so GitHub Pages shows the same canonical links as discovery.

  python scripts/sync_endpoints_json.py
  npm run docs:sync-endpoints

After unified Caddy + ngrok: npm run stack:unified:wire
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
out_path = root / "docs" / "endpoints.json"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(root / ".env", override=True)
        if (root / ".env.local").exists():
            load_dotenv(root / ".env.local", override=True)
    except ImportError:
        pass


def _origin(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    p = urlparse(u)
    if p.scheme and p.netloc:
        return f"{p.scheme}://{p.netloc}".rstrip("/")
    return ""


def _health_url_from_origin(origin: str) -> str:
    return f"{origin}/health" if origin else ""


def main() -> int:
    _load_env()
    t54_base = (os.getenv("T54_SELLER_PUBLIC_BASE_URL") or "").strip()
    if not t54_base:
        legacy = (
            os.getenv("T54_SELLER_PUBLIC_URL")
            or os.getenv("T54_X402_RESOURCE_URL")
            or os.getenv("X402_T54_RESOURCE_URL")
            or ""
        ).strip()
        if legacy:
            t54_base = _origin(legacy) or legacy

    x402_full = (os.getenv("X402_SELLER_PUBLIC_URL") or os.getenv("X402_SELLER_PROBE_URL") or "").strip()
    x402_origin = _origin(x402_full)

    mp_base = (os.getenv("MARKETPLACE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    mp_health = f"{mp_base}/health" if mp_base else ""

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    endpoints = [
        {
            "id": "t54_public_origin",
            "label": "T54 XRPL x402 seller (discovery origin)",
            "description": "Discovery appends each SKU path from x402_providers.json. With unified Caddy, base URL ends with /t54.",
            "url": t54_base,
            "network": "xrpl:0",
            "health_url": _health_url_from_origin(t54_base) if t54_base else "",
        },
        {
            "id": "base_x402_query",
            "label": "Base USDC x402 seller (facilitator / Bazaar)",
            "description": "Full GET /x402/v1/query URL for Coinbase Bazaar / x402 clients.",
            "url": x402_full,
            "network": (os.getenv("X402_SELLER_NETWORK") or "eip155:8453").strip(),
            "health_url": _health_url_from_origin(x402_origin) if x402_origin else "",
        },
    ]
    if mp_base:
        endpoints.append(
            {
                "id": "marketplace_public_origin",
                "label": "Marketplace HTTP (Stripe MPP, buyer API, webhooks)",
                "description": "Unified reverse proxy exposes /webhooks/stripe, /v1/*, /marketplace/* on this origin when using Caddy + ngrok.",
                "url": mp_base,
                "network": "marketplace",
                "health_url": mp_health,
            }
        )

    data = {
        "schema_note": "Canonical public URLs for agents and buyers. Regenerate: python scripts/sync_endpoints_json.py",
        "portal_url": "https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/",
        "updated_at": ts,
        "endpoints": endpoints,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"  T54_SELLER_PUBLIC_BASE_URL -> {t54_base or '(empty)'}")
    print(f"  X402_SELLER_PUBLIC_URL -> {x402_full or '(empty)'}")
    print(f"  MARKETPLACE_PUBLIC_BASE_URL -> {mp_base or '(empty)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
