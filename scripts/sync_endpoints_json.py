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
            pub = (os.getenv("PUBLIC_API_ORIGIN") or "").strip()
            if not pub.startswith("https://"):
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


def _portal_url() -> str:
    raw = (
        os.getenv("PUBLIC_PORTAL_URL")
        or os.getenv("SWARM_PORTAL_URL")
        or os.getenv("PUBLIC_SITE_ORIGIN")
        or "https://www.agentic-swarm-marketplace.com"
    ).strip()
    return raw.rstrip("/") + "/"


def _t54_catalog_endpoints(t54_base: str) -> list[dict]:
    if not t54_base:
        return []
    base = t54_base.rstrip("/")
    health = _health_url_from_origin(base)
    return [
        {
            "id": "t54_well_known_x402",
            "label": "T54 XRPL well-known catalog",
            "description": "Machine-readable XRPL SKU catalog for agent discovery (paths, drops, payTo, facilitator).",
            "url": f"{base}/.well-known/x402.json",
            "network": "xrpl:0",
            "health_url": health,
        },
        {
            "id": "t54_agent_card",
            "label": "T54 XRPL agent card",
            "description": "Agent capability card listing T54/LCG XRPL skills and endpoints.",
            "url": f"{base}/.well-known/agent-card.json",
            "network": "xrpl:0",
            "health_url": health,
        },
        {
            "id": "t54_lcg_procurement_readiness",
            "label": "T54 XRPL — LCG Procurement Readiness Scan",
            "description": "Entry SKU for LCG procurement intelligence on XRPL (POST JSON; GET ?payload= also supported).",
            "url": f"{base}/x402/v1/procurement-readiness",
            "network": "xrpl:0",
            "health_url": health,
        },
    ]



# Public mainnet settlement details and live 402 prices (2026-11-16 probes). No secrets.
BASE_USDC_ASSET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CELO_USDC_ASSET = "0xcebA9300f2b948710d2653dD7B07f33A8B32118C"
EVM_USDC_PAY_TO = "0x408f39B19266022FeC03076091e59D1f4f163658"
CELO_REVENUE_PAY_TO = "0xf00ebb2f7704e35593ce5bf9349921c8567c5fe4"

# CDP-listed Base USDC SKUs plus Celo USDC query. Prices from live HTTP 402 / well-known.
BASE_USDC_SKUS = [
    {
        "id": "base_x402_query",
        "path": "/x402/v1/query",
        "label": "Base USDC x402 seller (facilitator / Bazaar)",
        "description": "GET /x402/v1/query — constitution-safe structured Q&A with source attribution. Listed on CDP Bazaar.",
        "price_usd": "0.012",
    },
    {
        "id": "base_x402_constitution_audit",
        "path": "/x402/v1/constitution-audit",
        "label": "Base USDC — constitution audit",
        "description": "GET /x402/v1/constitution-audit — heuristic ethics and constitution-style review of a prompt excerpt.",
        "price_usd": "0.03",
    },
    {
        "id": "base_x402_agent_commerce_data",
        "path": "/x402/v1/agent-commerce-data",
        "label": "Base USDC — agent commerce data",
        "description": "GET /x402/v1/agent-commerce-data — premium x402 commerce intelligence bundle.",
        "price_usd": "0.07",
    },
    {
        "id": "base_x402_supplier_trust",
        "path": "/x402/v1/commerce/supplier-trust",
        "label": "Base USDC — commerce supplier trust",
        "description": "GET /x402/v1/commerce/supplier-trust — supplier trust pack for agent commerce.",
        "price_usd": "0.26",
    },
    {
        "id": "base_x402_product_evidence",
        "path": "/x402/v1/commerce/product-evidence",
        "label": "Base USDC — commerce product evidence",
        "description": "GET /x402/v1/commerce/product-evidence — product evidence pack for agent commerce.",
        "price_usd": "0.16",
    },
    {
        "id": "base_x402_product_search",
        "path": "/x402/v1/commerce/product-search",
        "label": "Base USDC — commerce product search",
        "description": "GET /x402/v1/commerce/product-search — product search pack for agent commerce.",
        "price_usd": "0.11",
    },
    {
        "id": "base_x402_airdrop_intelligence",
        "path": "/x402/v1/airdrop-intelligence",
        "label": "Base USDC — airdrop intelligence",
        "description": "GET /x402/v1/airdrop-intelligence — airdrop scam screening with Farm Score and EIP-7702 detection.",
        "price_usd": "0.09",
    },
    {
        "id": "base_x402_celo_agent_data",
        "path": "/x402/v1/celo-agent-data",
        "label": "Base USDC — Celo agent data",
        "description": "GET /x402/v1/celo-agent-data — Celo-rail evidence packed for buyers, settled in Base USDC.",
        "price_usd": "0.08",
    },
    {
        "id": "base_x402_research_brief",
        "path": "/x402/v1/research-brief",
        "label": "Base USDC — research brief",
        "description": "GET /x402/v1/research-brief — short research brief for agent buyers.",
        "price_usd": "0.06",
    },
    {
        "id": "base_x402_intake_resale",
        "path": "/x402/v1/intake-resale",
        "label": "Base USDC intake resale (same packs as T54 XRPL)",
        "description": "GET /x402/v1/intake-resale?pack_id=<uuid>. USDC settles to the Base seller payTo.",
        "price_usd": "0.05",
    },
    {
        "id": "base_x402_ecosystem_pulse",
        "path": "/x402/v1/ecosystem-pulse",
        "label": "Base USDC — ecosystem pulse",
        "description": "GET /x402/v1/ecosystem-pulse — PoCon ecosystem pulse: oracle snapshot, worker activity, bazaar readiness.",
        "price_usd": "0.04",
    },
    {
        "id": "base_x402_contract_triage",
        "path": "/x402/v1/contract-triage",
        "label": "Base USDC — contract triage",
        "description": "GET /x402/v1/contract-triage — fast smart contract malicious pattern triage.",
        "price_usd": "0.02",
    },
]


def _sku_entry(*, sku_id: str, label: str, description: str, url: str, network: str, health_url: str, price: str, asset: str, pay_to: str, method: str = "GET") -> dict:
    return {
        "id": sku_id,
        "label": label,
        "description": description,
        "url": url,
        "network": network,
        "health_url": health_url,
        "method": method,
        "price": price,
        "asset": asset,
        "payTo": pay_to,
    }


def _extend_live_priced_skus(endpoints: list[dict], api_origin: str, celo_origin: str) -> list[dict]:
    """Replace/append live priced routes so Pages matches current 402 probes."""
    api = (api_origin or "").rstrip("/")
    if not api:
        return endpoints
    health = _health_url_from_origin(api)
    by_id = {e.get("id"): i for i, e in enumerate(endpoints)}
    priced: list[dict] = []
    for sku in BASE_USDC_SKUS:
        priced.append(
            _sku_entry(
                sku_id=sku["id"],
                label=sku["label"],
                description=sku["description"],
                url=f"{api}{sku['path']}",
                network="eip155:8453",
                health_url=health,
                price=f"{sku['price_usd']} USDC",
                asset=BASE_USDC_ASSET,
                pay_to=EVM_USDC_PAY_TO,
            )
        )
    celo_health = f"{celo_origin}/celo/health" if celo_origin else f"{api}/celo/health"
    priced.append(
        _sku_entry(
            sku_id="celo_usdc_x402_query",
            label="Celo USDC x402 query",
            description="GET /celo/x402/v1/query — constitution-safe Q&A settled in Celo USDC (eip155:42220). Not the native fulfillQuery rail.",
            url=f"{api}/celo/x402/v1/query",
            network="eip155:42220",
            health_url=celo_health,
            price="0.01 USDC",
            asset=CELO_USDC_ASSET,
            pay_to=EVM_USDC_PAY_TO,
        )
    )
    priced.append(
        _sku_entry(
            sku_id="celo_native_query",
            label="Celo native x402 seller (api_402 / fulfillQuery)",
            description="GET/POST /celo/query — HTTP 402 with 0.001 CELO via AgentRevenueService.fulfillQuery (no facilitator).",
            url=f"{api}/celo/query",
            network="eip155:42220",
            health_url=celo_health,
            price="0.001 CELO",
            asset="CELO",
            pay_to=CELO_REVENUE_PAY_TO,
        )
    )
    # Drop unpriced stubs that the priced rows replace, then insert priced SKUs
    # after the last T54 catalog row (or at the original query position).
    replace_ids = {s["id"] for s in BASE_USDC_SKUS} | {"celo_native_query", "celo_usdc_x402_query"}
    insert_at = None
    for i, e in enumerate(endpoints):
        if e.get("id") in replace_ids and insert_at is None:
            insert_at = i
    kept = [e for e in endpoints if e.get("id") not in replace_ids]
    if insert_at is None:
        # after t54 catalog if present, else before marketplace
        for i, e in enumerate(kept):
            if e.get("id") == "marketplace_public_origin":
                insert_at = i
                break
        else:
            insert_at = len(kept)
    else:
        # insert_at was an index into the original list; map to kept
        # Recompute: place after last kept row that originally preceded the first replaced id.
        prefix_ids = [e.get("id") for e in endpoints[:insert_at]]
        insert_at = len([e for e in kept if e.get("id") in prefix_ids])
    return kept[:insert_at] + priced + kept[insert_at:]


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
    openapi_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated docs/openapi.json x-payment-info.amount -> {cents}")


def main() -> int:
    _load_env()
    pub = (os.getenv("PUBLIC_API_ORIGIN") or "").strip().rstrip("/")
    if pub.startswith("https://"):
        os.environ["MARKETPLACE_PUBLIC_BASE_URL"] = pub
        os.environ["X402_SELLER_PUBLIC_URL"] = f"{pub}/x402/v1/query"
        os.environ["T54_SELLER_PUBLIC_BASE_URL"] = f"{pub}/t54"
        os.environ["CELO_402_PUBLIC_URL"] = f"{pub}/celo/query"
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

    celo_query = (os.getenv("CELO_402_PUBLIC_URL") or "").strip()
    if not celo_query and pub:
        celo_query = f"{pub}/celo/query"
    celo_origin = _origin(celo_query)
    chain_id = (os.getenv("CHAIN_ID") or "42220").strip()
    celo_network = f"eip155:{chain_id}" if chain_id.isdigit() else "eip155:42220"

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
        {
            "id": "celo_native_query",
            "label": "Celo native x402 seller (api_402 / fulfillQuery)",
            "description": "GET/POST /celo/query — HTTP 402 with CELO payment via AgentRevenueService.fulfillQuery (no facilitator). Set CELO_402_PUBLIC_URL or PUBLIC_API_ORIGIN.",
            "url": celo_query,
            "network": celo_network,
            "health_url": f"{celo_origin}/celo/health" if celo_origin else "",
        },
    ]
    if mp_base:
        endpoints.append(
            {
                "id": "marketplace_public_origin",
                "label": "Marketplace HTTP (Stripe MPP, buyer API, webhooks)",
                "description": "Stripe MPP + buyer API + webhooks: unified Caddy maps /webhooks/stripe, /v1/*, /marketplace/* to marketplace:serve (8055). Same public HTTPS origin as x402/T54 when MARKETPLACE_PUBLIC_BASE_URL is that origin.",
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

    t54_origin = next((e for e in endpoints if e.get("id") == "t54_public_origin"), None)
    if t54_origin is not None:
        idx = endpoints.index(t54_origin) + 1
        endpoints[idx:idx] = _t54_catalog_endpoints(t54_base)

    api_origin = pub or x402_origin or mp_base
    endpoints = _extend_live_priced_skus(endpoints, api_origin, celo_origin)

    data = {
        "schema_note": "Canonical public URLs for agents and buyers. Regenerate: npm run docs:sync-endpoints (reads repo-root .env). Commit result for GitHub Pages. Stable HTTPS + mainnet alignment: documentation/PUBLIC_MAINNET_OPERATIONS.md",
        "portal_url": _portal_url(),
        "updated_at": ts,
        "endpoints": endpoints,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"  T54_SELLER_PUBLIC_BASE_URL -> {t54_base or '(empty)'}")
    print(f"  X402_SELLER_PUBLIC_URL -> {x402_full or '(empty)'}")
    print(f"  X402_INTAKE_RESALE_PUBLIC_URL -> {intake_resale_url or '(empty)'}")
    print(f"  CELO_402_PUBLIC_URL -> {celo_query or '(empty)'}")
    print(f"  MARKETPLACE_PUBLIC_BASE_URL -> {mp_base or '(empty)'}")
    print(f"  MCP_SSE_PUBLIC_URL -> {mcp_sse or '(empty)'}")
    _sync_docs_openapi_mpp_amount()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
