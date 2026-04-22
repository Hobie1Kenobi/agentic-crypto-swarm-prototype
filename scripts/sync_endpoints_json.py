#!/usr/bin/env python3
"""
Write docs/endpoints.json from repo-root .env (T54, Base x402, optional marketplace origin).

Run after ngrok sync or when your public URLs change, then commit docs/endpoints.json
so GitHub Pages shows the same canonical links as discovery.
If PUBLIC_API_ORIGIN is set in .env, it overrides per-key public URLs for this export
(same cohesion as scripts/apply_public_api_origin.py).
Also updates docs/openapi.json ``x-payment-info.amount`` from MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD when present.

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
from decimal import Decimal
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
out_path = root / "docs" / "endpoints.json"
openapi_path = root / "docs" / "openapi.json"


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


def _sync_docs_openapi_mpp_amount() -> None:
    """Keep docs/openapi.json MPP x-payment-info.amount in sync with bundle price env."""
    raw = (os.getenv("MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD") or "49.00").strip()
    try:
        cents = str(int((Decimal(raw) * 100).to_integral_value()))
    except Exception:
        cents = "4900"
    if not openapi_path.is_file():
        return
    try:
        data = json.loads(openapi_path.read_text(encoding="utf-8"))
    except Exception:
        return
    po = data.get("paths", {}).get("/v1/orders", {}).get("post")
    if not isinstance(po, dict):
        return
    xpi = po.get("x-payment-info")
    if not isinstance(xpi, dict):
        return
    if xpi.get("amount") == cents:
        return
    xpi["amount"] = cents
    openapi_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated docs/openapi.json x-payment-info.amount -> {cents}")


def main() -> int:
    _load_env()
    pub = (os.getenv("PUBLIC_API_ORIGIN") or "").strip().rstrip("/")
    if pub.startswith("https://"):
        os.environ["MARKETPLACE_PUBLIC_BASE_URL"] = pub
        os.environ["X402_SELLER_PUBLIC_URL"] = f"{pub}/x402/v1/query"
        os.environ["T54_SELLER_PUBLIC_BASE_URL"] = f"{pub}/t54"
        os.environ["MCP_SSE_PUBLIC_URL"] = f"{pub}/mcp"

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
    intake_explicit = (os.getenv("X402_INTAKE_RESALE_PUBLIC_URL") or "").strip()
    if intake_explicit:
        intake_resale_url = intake_explicit
    elif x402_full:
        intake_resale_url = x402_full.replace("/x402/v1/query", "/x402/v1/intake-resale")
    else:
        intake_resale_url = ""

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
        {
            "id": "base_x402_intake_resale",
            "label": "Base USDC intake resale (same packs as T54 XRPL)",
            "description": "GET /x402/v1/intake-resale?pack_id=<uuid>. USDC settles to X402_SELLER_PAY_TO. Override URL with X402_INTAKE_RESALE_PUBLIC_URL.",
            "url": intake_resale_url,
            "network": (os.getenv("X402_SELLER_NETWORK") or "eip155:8453").strip(),
            "health_url": _health_url_from_origin(x402_origin) if x402_origin else "",
        },
    ]
    if mp_base:
        endpoints.append(
            {
                "id": "marketplace_public_origin",
                "label": "Marketplace HTTP (Stripe MPP, buyer API, webhooks)",
                "description": "Stripe MPP + buyer API + webhooks: unified Caddy maps /webhooks/stripe, /v1/*, /marketplace/* to marketplace:serve (8055). Same public HTTPS origin as x402/T54 when MARKETPLACE_PUBLIC_BASE_URL matches your tunnel.",
                "url": mp_base,
                "network": "marketplace",
                "health_url": mp_health,
            }
        )

    mcp_sse = (os.getenv("MCP_SSE_PUBLIC_URL") or "").strip().rstrip("/")
    if mcp_sse:
        endpoints.append(
            {
                "id": "mcp_t54_sse",
                "label": "MCP T54 x402 (SSE, remote clients)",
                "description": "Streamable HTTP (Smithery): POST .../mcp (port 9052, mcp>=1.23). SSE: GET .../mcp/sse, POST .../mcp/messages/ (9051). Caddy: exact /mcp → 9052; /mcp/* → 9051. Set MCP_SSE_PUBLIC_URL to your public HTTPS origin + /mcp.",
                "url": mcp_sse,
                "sse_url": f"{mcp_sse}/sse",
                "messages_url": f"{mcp_sse}/messages/",
                "network": "mcp",
                "health_url": "",
            }
        )

    data = {
        "schema_note": "Canonical public URLs for agents and buyers. Regenerate: npm run docs:sync-endpoints (reads repo-root .env). Commit result for GitHub Pages. Stable HTTPS + mainnet alignment: documentation/PUBLIC_MAINNET_OPERATIONS.md",
        "portal_url": "https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/",
        "updated_at": ts,
        "endpoints": endpoints,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"  T54_SELLER_PUBLIC_BASE_URL -> {t54_base or '(empty)'}")
    print(f"  X402_SELLER_PUBLIC_URL -> {x402_full or '(empty)'}")
    print(f"  X402_INTAKE_RESALE_PUBLIC_URL -> {intake_resale_url or '(empty)'}")
    print(f"  MARKETPLACE_PUBLIC_BASE_URL -> {mp_base or '(empty)'}")
    print(f"  MCP_SSE_PUBLIC_URL -> {mcp_sse or '(empty)'}")
    _sync_docs_openapi_mpp_amount()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
