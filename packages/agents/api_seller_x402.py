#!/usr/bin/env python3
"""
Facilitator x402 seller (Base mainnet USDC only): ExactEvm + CDP facilitator.

Production network is fixed at eip155:8453 (Base mainnet). Base Sepolia is not supported on this seller.
Bazaar catalogs resources after the CDP facilitator (https://api.cdp.coinbase.com/platform/v2/x402) verifies/settles payments.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Fix Windows UTF-8 encoding for CDP library banner output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env", override=False)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)

sys.path.insert(0, str(root / "packages" / "agents"))
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


_FAC_CDP = "https://api.cdp.coinbase.com/platform/v2/x402"
_FAC_PAYAI = "https://facilitator.payai.network"
_SELLER_NETWORK = "eip155:8453"
_FORBIDDEN_NETWORKS = frozenset(
    {
        "eip155:84532",
        "84532",
        "base-sepolia",
        "basesepolia",
        "base_sepolia",
    }
)


def _require_mainnet_network() -> str:
    """Seller is mainnet-only; reject Sepolia env overrides."""
    raw = _env("X402_SELLER_NETWORK", _SELLER_NETWORK)
    key = raw.lower().replace(" ", "")
    if key in _FORBIDDEN_NETWORKS or "84532" in key or "sepolia" in key:
        raise RuntimeError(
            "Base Sepolia is disabled for api_seller_x402. "
            f"Unset X402_SELLER_NETWORK or set eip155:8453 (got {raw!r})."
        )
    if raw and raw not in (_SELLER_NETWORK, "8453", "base-mainnet", "base_mainnet"):
        raise RuntimeError(
            f"api_seller_x402 only supports {_SELLER_NETWORK}; got X402_SELLER_NETWORK={raw!r}"
        )
    return _SELLER_NETWORK


def _payment_setup_failure(exc: BaseException) -> bool:
    chain: list[BaseException] = []
    cur: BaseException | None = exc
    while cur is not None and cur not in chain:
        chain.append(cur)
        cur = cur.__cause__  # type: ignore[assignment]
    markers = (
        "routeconfigurationerror",
        "connecterror",
        "facilitatorresponseerror",
        "getaddrinfo",
        "facilitator doesn't support",
        "unauthorized",
        "401",
    )
    for item in chain:
        name = type(item).__name__.lower()
        text = str(item).lower()
        if any(m in name or m in text for m in markers):
            return True
    return False


def _build_facilitator_client(facilitator_url: str):
    """Build facilitator client. CDP auth only when URL is the CDP facilitator."""
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient

    url = facilitator_url.rstrip("/")
    # PayAI (and any non-CDP facilitator) must not carry CDP API auth headers.
    if "payai.network" in url or "api.cdp.coinbase.com" not in url:
        return HTTPFacilitatorClient(FacilitatorConfig(url=url))

    try:
        from cdp.x402 import create_facilitator_config

        cfg = create_facilitator_config()
        if isinstance(cfg, dict):
            cfg = dict(cfg)
            cfg["url"] = url
            return HTTPFacilitatorClient(cfg)
    except ImportError:
        pass

    return HTTPFacilitatorClient(FacilitatorConfig(url=url))


def _cdp_keys_configured() -> bool:
    return bool(_env("CDP_API_KEY_ID") and _env("CDP_API_KEY_SECRET"))


def _normalize_facilitator_url(raw: str) -> tuple[str, str]:
    """Return (before_display, normalized_url).

    Default remains CDP. Explicitly allowlisted facilitators (PayAI) pass through
    so discovery settles can index ASM on that bazaar. Everything else maps to CDP.
    """
    before = raw.strip().rstrip("/") or "(default)"
    u = raw.strip().rstrip("/")
    if not u:
        return "(default)", _FAC_CDP
    if "facilitator.payai.network" in u:
        return before, _FAC_PAYAI
    if "api.cdp.coinbase.com" in u and "x402" in u:
        return before, _FAC_CDP
    if "facilitator.cdp.coinbase.com" in u:
        return f"{before} (legacy->CDP API)", _FAC_CDP
    if "x402.org/facilitator" in u:
        return f"{before} (ignored->CDP)", _FAC_CDP
    if "cdp.coinbase.com" in u:
        return f"{before} (->CDP API)", _FAC_CDP
    return f"{before} (->CDP API)", _FAC_CDP


def _pay_to_address() -> str:
    explicit = _env("X402_SELLER_PAY_TO")
    if explicit.startswith("0x") and len(explicit) == 42:
        return explicit
    pk = _env("ROOT_STRATEGIST_PRIVATE_KEY") or _env("X402_BUYER_BASE_MAINNET_PRIVATE_KEY")
    if pk and "0x" in pk:
        try:
            from eth_account import Account

            return Account.from_key(pk).address
        except Exception:
            pass
    return ""


def _usd(name: str, default: str) -> str:
    return _env(name, default)


def create_app():
    import logging
    from contextlib import asynccontextmanager

    from fastapi import Body, FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, Response

    from facilitator_health import FacilitatorMonitor
    from intake_resale_sell_guard import create_intake_resale_probe_middleware
    from mcp_routing_hint import is_mcp_path, mcp_wrong_port_response
    from t54_seller_handlers import (
        run_agent_commerce_data,
        run_airdrop_intelligence_report,
        run_constitution_audit_lite,
        run_intake_resale_pack,
        run_ecosystem_pulse,
        run_research_brief,
    )
    from x402 import x402ResourceServer
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.register import register_exact_evm_server

    from api_402 import generate_response_for_query
    from well_known_discovery import (
        LINKSET_JSON_MEDIA_TYPE,
        agent_skill_markdown_path,
        build_agent_card_manifest,
        build_glama_claim,
        build_agent_skills_index,
        build_api_catalog_linkset,
        build_jwks_document,
        build_mcp_manifest,
        build_mcp_server_card,
        build_mcp_server_cards_list,
        build_oauth_authorization_server_metadata,
        build_oauth_protected_resource_metadata,
        build_openid_configuration,
        build_acp_discovery,
        build_ucp_profile,
        build_x402_manifest,
        oauth_stub_unavailable_payload,
    )
    from identity.routes import attach_identity_routes
    from config.base_x402_skus import (
        load_base_x402_skus,
        recommended_next_actions_for,
        sku_by_path,
    )
    from x402_seller_bazaar import (
        bazaar_agent_commerce_data,
        bazaar_airdrop_intelligence,
        bazaar_bid_fit_score,
        bazaar_bom_risk_audit,
        bazaar_celo_agent_data,
        bazaar_commerce_compatibility_check,
        bazaar_commerce_compliance_check,
        bazaar_commerce_product_evidence,
        bazaar_commerce_product_search,
        bazaar_commerce_purchase_readiness,
        bazaar_commerce_quote_comparison,
        bazaar_commerce_supplier_trust,
        bazaar_constitution_audit,
        bazaar_contract_audit,
        bazaar_contract_monitor,
        bazaar_contract_triage,
        bazaar_ecosystem_pulse,
        bazaar_intake_resale,
        bazaar_procurement_readiness,
        bazaar_purchase_readiness_package,
        bazaar_query,
        bazaar_quote_completeness_audit,
        bazaar_research_brief,
        bazaar_rfp_requirement_extractor,
        bazaar_specification_normalizer,
    )

    pay_to = _pay_to_address()
    if not pay_to:
        raise RuntimeError(
            "Set X402_SELLER_PAY_TO or ROOT_STRATEGIST_PRIVATE_KEY so facilitator knows where USDC settles."
        )

    network = _require_mainnet_network()
    fac_raw = _env("X402_TEST_FACILITATOR_URL", _FAC_CDP)
    fac_before, facilitator_url = _normalize_facilitator_url(fac_raw)
    _log = logging.getLogger("api_seller_x402")
    _log.info("x402 seller locked to network=%s facilitator=%s", network, facilitator_url)
    resale_price = _usd("X402_INTAKE_RESALE_PRICE", "$0.05")
    deep_audit_max_timeout = int((_env("X402_SELLER_DEEP_AUDIT_MAX_TIMEOUT_SECONDS", "180") or "180").strip() or "180")
    monitor_max_timeout = int((_env("X402_SELLER_MONITOR_MAX_TIMEOUT_SECONDS", "300") or "300").strip() or "300")

    monitor = FacilitatorMonitor(facilitator_url, disable_env="X402_FACILITATOR_HEALTH_DISABLE")

    def _merge_ext(d: dict, b) -> None:
        if b:
            d["extensions"] = b

    bazaar_by_id = {
        "structured-query": bazaar_query,
        "research-brief": bazaar_research_brief,
        "constitution-audit-lite": bazaar_constitution_audit,
        "agent-commerce-data": bazaar_agent_commerce_data,
        "ecosystem-pulse": bazaar_ecosystem_pulse,
        "airdrop-intelligence-report": bazaar_airdrop_intelligence,
        "contract-triage": bazaar_contract_triage,
        "contract-audit": bazaar_contract_audit,
        "contract-monitor": bazaar_contract_monitor,
        "celo-agent-data": bazaar_celo_agent_data,
        "intake-resale-pack": bazaar_intake_resale,
        "commerce-product-search": bazaar_commerce_product_search,
        "commerce-product-evidence": bazaar_commerce_product_evidence,
        "commerce-supplier-trust": bazaar_commerce_supplier_trust,
        "commerce-compatibility-check": bazaar_commerce_compatibility_check,
        "commerce-quote-comparison": bazaar_commerce_quote_comparison,
        "commerce-compliance-check": bazaar_commerce_compliance_check,
        "commerce-purchase-readiness": bazaar_commerce_purchase_readiness,
        "procurement-readiness": bazaar_procurement_readiness,
        "specification-normalizer": bazaar_specification_normalizer,
        "quote-completeness-audit": bazaar_quote_completeness_audit,
        "rfp-requirement-extractor": bazaar_rfp_requirement_extractor,
        "bid-fit-score": bazaar_bid_fit_score,
        "bom-risk-audit": bazaar_bom_risk_audit,
        "purchase-readiness-package": bazaar_purchase_readiness_package,
    }

    routes: dict = {}
    for sku in load_base_x402_skus(receiver=pay_to):
        accepts: dict = {
            "scheme": "exact",
            "payTo": pay_to,
            "price": sku.price_accepts(),
            "network": network,
        }
        if sku.id == "contract-audit":
            accepts["maxTimeoutSeconds"] = max(60, min(900, deep_audit_max_timeout))
        if sku.id == "contract-monitor":
            accepts["maxTimeoutSeconds"] = max(120, min(900, monitor_max_timeout))
        row = {"accepts": accepts, "description": sku.description}
        ext_fn = bazaar_by_id.get(sku.id)
        if ext_fn:
            _merge_ext(row, ext_fn())
        routes[sku.route_key] = row
        routes[f"HEAD {sku.path}"] = row
        if sku.method == "POST" and sku.id != "contract-monitor":
            routes[f"GET {sku.path}"] = row

    if not _cdp_keys_configured():
        _log.warning(
            "CDP_API_KEY_ID and CDP_API_KEY_SECRET not set — paid routes will fail until "
            "Coinbase Developer Platform API keys are in .env.local"
        )
    fac = _build_facilitator_client(facilitator_url)
    server = x402ResourceServer(fac)
    register_exact_evm_server(server, networks=[network])

    fac_lifespan = monitor.make_lifespan()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with fac_lifespan(app):
            app.state.x402_routes_ok = None

            stop = asyncio.Event()
            try:
                from marketplace.skus.contract_monitor_worker import run_contract_monitor_worker

                task = asyncio.create_task(run_contract_monitor_worker(stop))
            except Exception:
                task = None
            try:
                yield
            finally:
                stop.set()
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    app = FastAPI(
        title="Agentic Swarm x402 Seller (facilitator)",
        version="0.3.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-asm-sku"],
    )
    app.state.facilitator_url_before = fac_before
    app.state.facilitator_url_after = facilitator_url

    _mw = payment_middleware(routes, server)

    @app.middleware("http")
    async def force_public_https_scheme(request, call_next):
        """Ensure payment-required resource URLs use https behind TLS-terminating proxies."""
        public = (
            _env("PUBLIC_API_ORIGIN")
            or _env("MARKETPLACE_PUBLIC_BASE_URL")
            or _env("X402_SELLER_PUBLIC_URL")
        )
        xf_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if xf_proto == "https" or (public and public.startswith("https://")):
            request.scope["scheme"] = "https"
        path = request.url.path or ""
        if path.startswith("/x402/") and path[-1:] in "`.,;":
            cleaned = path.rstrip("`.,;")
            request.scope["path"] = cleaned
            request.scope["raw_path"] = cleaned.encode("utf-8")
            path = cleaned
        # Indexers HEAD first. Treat HEAD on GET-capable paid paths as GET so
        # the facilitator middleware emits a 402 instead of FastAPI 405.
        if request.method == "HEAD" and path.startswith("/x402/v1/") and "contract-monitor" not in path:
            request.scope["method"] = "GET"
        return await call_next(request)

    @app.middleware("http")
    async def guard_evm_facilitator(request, call_next):
        if request.url.path in ("/", "/health"):
            return await call_next(request)
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)
        if request.url.path.startswith("/x402/discovery"):
            return await call_next(request)
        if request.url.path.startswith("/oauth/"):
            return await call_next(request)
        if is_mcp_path(request.url.path):
            return mcp_wrong_port_response()
        if getattr(request.app.state, "x402_routes_ok", None) is False:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "x402_route_misconfigured",
                    "detail": "Paid routes failed facilitator validation at startup",
                    "facilitator": facilitator_url,
                    "network": network,
                    "hint": f"Mainnet only: {_SELLER_NETWORK} + {_FAC_CDP}",
                },
            )
        if not monitor.is_ok():
            return JSONResponse(
                status_code=503,
                content={"error": "payment_gateway_unavailable", "detail": "facilitator_unhealthy"},
            )
        return await call_next(request)

    app.middleware("http")(create_intake_resale_probe_middleware())

    @app.middleware("http")
    async def x402_gate(request, call_next):
        if request.url.path.startswith("/x402/") and getattr(
            request.app.state, "x402_routes_ok", None
        ) is False:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "x402_route_misconfigured",
                    "detail": "Paid routes failed facilitator validation at startup",
                    "facilitator": facilitator_url,
                    "network": network,
                    "hint": f"Mainnet only: {_SELLER_NETWORK} + {_FAC_CDP}",
                },
            )
        try:
            response = await _mw(request, call_next)
            if request.url.path.startswith("/x402/"):
                request.app.state.x402_routes_ok = True
            return response
        except Exception as exc:
            if request.url.path.startswith("/x402/") and _payment_setup_failure(exc):
                # Do not latch the whole seller: one bad settle/verify must not 503 every SKU.
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "payment_gateway_unavailable",
                        "detail": str(exc),
                        "facilitator": facilitator_url,
                        "network": network,
                        "hint": (
                            f"Mainnet seller uses {_SELLER_NETWORK} and {_FAC_CDP}. "
                            "Set CDP_API_KEY_ID and CDP_API_KEY_SECRET in .env.local (portal.cdp.coinbase.com)."
                        ),
                    },
                )
            raise

    @app.get("/")
    async def root():
        return {
            "service": "agentic-swarm-x402-seller",
            "facilitator_configured_as": facilitator_url,
            "facilitator_raw_env": fac_before,
            "seller_network": network,
            "x402_routes_ok": getattr(app.state, "x402_routes_ok", None),
            "facilitator_healthy": monitor.is_ok(),
            "cdp_api_keys_configured": _cdp_keys_configured(),
            "probe": "/health",
            "paid_routes": list(routes.keys()),
            "note": "Bazaar indexes after facilitator-settled payments (not direct wallet transfers).",
        }

    def _with_next_actions(sku_id: str, payload: dict) -> dict:
        payload = dict(payload or {})
        actions = recommended_next_actions_for(sku_id)
        if actions and not payload.get("recommended_next_actions"):
            payload["recommended_next_actions"] = actions
        payload.setdefault("sku_id", sku_id)
        return payload

    @app.get("/x402/v1/query")
    async def paid_query(q: str = "", depth: str = "brief"):
        question = (q or "").strip() or (
            "What paid x402 SKUs does Agentic Swarm Marketplace offer and how do I call them?"
        )
        text = generate_response_for_query(question)
        return _with_next_actions(
            "structured-query",
            {
                "query": question,
                "depth": depth,
                "answer": text,
                "confidence": 0.85,
                "sources": ["agentic-swarm-x402"],
                "seller": "agentic-swarm-x402",
                "defaulted_query": not bool((q or "").strip()),
            },
        )

    @app.get("/x402/v1/research-brief")
    async def paid_research_brief(topic: str = "", context: str | None = None):
        return _with_next_actions(
            "research-brief",
            run_research_brief(topic or "Ethical agent commerce", context).model_dump(),
        )

    @app.get("/x402/v1/constitution-audit")
    async def paid_constitution(prompt_snippet: str = ""):
        return _with_next_actions(
            "constitution-audit-lite",
            run_constitution_audit_lite(prompt_snippet).model_dump(),
        )

    @app.get("/x402/v1/agent-commerce-data")
    async def paid_agent_commerce_data(depth: str = "standard"):
        return _with_next_actions(
            "agent-commerce-data",
            run_agent_commerce_data(depth).model_dump(),
        )

    @app.get("/x402/v1/ecosystem-pulse")
    async def paid_ecosystem_pulse(fresh: int = 0):
        return _with_next_actions(
            "ecosystem-pulse",
            run_ecosystem_pulse(fresh=bool(fresh)).model_dump(),
        )

    @app.get("/x402/v1/airdrop-intelligence")
    async def paid_airdrop(
        topic: str = "Ethical airdrop and incentive screening",
        context: str | None = None,
        contractAddress: str | None = None,
    ):
        base = run_airdrop_intelligence_report(topic, context).model_dump()
        addr = (contractAddress or "").strip()
        if addr.startswith("0x") and len(addr) == 42:
            try:
                from marketplace.skus.smart_contract_audit import triage_contract

                base["contractTriage"] = triage_contract(addr, "eip155:8453")
            except Exception as exc:
                base["contractTriage"] = {"error": "triage_engine_unavailable", "detail": str(exc)[:200]}
        return base

    @app.get("/x402/v1/contract-triage")
    async def paid_triage(contractAddress: str = "", chainId: str = "eip155:8453"):
        addr = (contractAddress or "").strip()
        if not (addr.startswith("0x") and len(addr) == 42):
            return _with_next_actions(
                "contract-triage",
                {
                    "error": "missing_or_invalid_contractAddress",
                    "hint": "Pass ?contractAddress=0x…&chainId=eip155:8453",
                    "example": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "verdict": None,
                },
            )
        try:
            from marketplace.skus.smart_contract_audit import triage_contract

            return _with_next_actions("contract-triage", triage_contract(addr, chainId))
        except Exception as exc:
            return _with_next_actions(
                "contract-triage",
                {
                    "contractAddress": addr,
                    "chainId": chainId,
                    "verdict": "engine_unavailable",
                    "error": "triage_engine_unavailable",
                    "detail": str(exc)[:200],
                },
            )

    @app.get("/x402/v1/contract-audit")
    async def paid_audit(addresses: str = "", chainId: str = "eip155:8453"):
        from marketplace.skus.smart_contract_audit import deep_audit

        parts = [p.strip() for p in (addresses or "").split(",") if p.strip()][:3]
        if not parts:
            return _with_next_actions(
                "contract-audit",
                {
                    "error": "missing_addresses",
                    "hint": "Pass ?addresses=0x… (comma-separated, max 3)",
                    "example": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                },
            )
        return deep_audit(parts, chainId)

    @app.post("/x402/v1/contract-monitor")
    async def paid_monitor(
        body: dict = Body(...),
    ):
        from marketplace.skus.smart_contract_audit import monitor_subscribe

        addrs = body.get("addresses") or []
        if not isinstance(addrs, list):
            return JSONResponse(status_code=400, content={"error": "addresses must be array"})
        url = (body.get("webhookUrl") or "").strip()
        if not url.startswith("https://"):
            return JSONResponse(status_code=400, content={"error": "webhookUrl must be https URL"})
        thr = body.get("thresholds") if isinstance(body.get("thresholds"), dict) else {}
        days = int(body.get("durationDays") or 30)
        return monitor_subscribe([str(a) for a in addrs[:10]], url, thr, days)

    @app.get("/x402/v1/celo-agent-data")
    async def paid_celo_agent_data(depth: str = "standard"):
        from seller_public_data_bundle import build_public_data_bundle_dict

        d = (depth or "standard").strip().lower()
        if d not in ("standard", "full"):
            d = "standard"
        data = build_public_data_bundle_dict(d)
        data["seller"] = "agentic-swarm-x402"
        data["rail"] = "base_x402_usdc"
        data["listing_id"] = "celo-agent-data"
        return _with_next_actions("celo-agent-data", data)

    @app.get("/x402/v1/intake-resale")
    async def paid_intake_resale(pack_id: str = ""):
        m = run_intake_resale_pack(pack_id, revenue_usd=resale_price, rail="Base")
        payload = m.model_dump() if hasattr(m, "model_dump") else dict(m)
        return _with_next_actions("intake-resale-pack", payload)

    @app.get("/x402/v1/commerce/product-search")
    async def paid_commerce_product_search(q: str = "", category: str = ""):
        from commerce.x402_handlers import handle_commerce_product_search

        return handle_commerce_product_search(q=q, category=category)

    @app.get("/x402/v1/commerce/product-evidence")
    async def paid_commerce_product_evidence(productId: str = ""):
        from commerce.x402_handlers import handle_commerce_product_evidence

        return handle_commerce_product_evidence(productId)

    @app.get("/x402/v1/commerce/supplier-trust")
    async def paid_commerce_supplier_trust(supplierId: str = ""):
        from commerce.x402_handlers import handle_commerce_supplier_trust

        return handle_commerce_supplier_trust(supplierId)

    @app.get("/x402/v1/commerce/compatibility-check")
    async def paid_commerce_compatibility(productId: str = "", requirements: str = "{}"):
        from commerce.x402_handlers import handle_commerce_compatibility

        return handle_commerce_compatibility(productId, requirements_json=requirements)

    @app.get("/x402/v1/commerce/quote-comparison")
    async def paid_commerce_quote_comparison(
        productId: str = "", quantity: int = 1, buyerId: str = "buyer_agent"
    ):
        from commerce.x402_handlers import handle_commerce_quote_comparison

        return handle_commerce_quote_comparison(productId, quantity=quantity, buyer_id=buyerId)

    @app.get("/x402/v1/commerce/compliance-check")
    async def paid_commerce_compliance(quoteId: str = "", requirements: str = "{}"):
        from commerce.x402_handlers import handle_commerce_compliance

        return handle_commerce_compliance(quote_id=quoteId, requirements_json=requirements)

    @app.get("/x402/v1/commerce/purchase-readiness")
    async def paid_commerce_purchase_readiness(
        productId: str = "", quantity: int = 1, buyerId: str = "buyer_agent"
    ):
        from commerce.x402_handlers import handle_commerce_purchase_readiness

        return handle_commerce_purchase_readiness(productId, quantity=quantity, buyer_id=buyerId)

    def _lcg_payload_from_query(payload: str | None) -> dict:
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"requirements_text": payload, "text": payload}

    def _register_lcg(path: str, sku_id: str) -> None:
        async def _post(body: dict = Body(default_factory=dict)):
            from lcg_procurement import handle_lcg_sku

            return handle_lcg_sku(sku_id, body)

        async def _get(payload: str | None = Query(default=None, max_length=20000)):
            from lcg_procurement import handle_lcg_sku

            return handle_lcg_sku(sku_id, _lcg_payload_from_query(payload))

        _post.__name__ = f"paid_{sku_id.replace('-', '_')}_post"
        _get.__name__ = f"paid_{sku_id.replace('-', '_')}_get"
        app.add_api_route(path, _post, methods=["POST"])
        app.add_api_route(path, _get, methods=["GET"])

    for _lcg_id, _lcg_path in (
        ("procurement-readiness", "/x402/v1/procurement-readiness"),
        ("specification-normalizer", "/x402/v1/specification-normalizer"),
        ("quote-completeness-audit", "/x402/v1/quote-completeness-audit"),
        ("rfp-requirement-extractor", "/x402/v1/rfp-requirement-extractor"),
        ("bid-fit-score", "/x402/v1/bid-fit-score"),
        ("bom-risk-audit", "/x402/v1/bom-risk-audit"),
        ("purchase-readiness-package", "/x402/v1/purchase-readiness-package"),
    ):
        _register_lcg(_lcg_path, _lcg_id)

    def _discovery_catalog():
        manifest = build_x402_manifest(pay_to)
        return {
            "x402Version": 2,
            "seller": manifest.get("seller"),
            "resources": manifest.get("resources") or [],
            "catalog": "/.well-known/x402.json",
            "note": "Free discovery catalog. Pay the resource URL to settle.",
        }

    attach_identity_routes(app, rail="base")

    @app.get("/x402/discovery/resources")
    @app.get("/x402/discovery")
    async def x402_discovery_resources():
        return JSONResponse(content=_discovery_catalog())

    @app.api_route("/x402/{full_path:path}", methods=["HEAD"], include_in_schema=False)
    async def x402_head_probe(full_path: str):
        return Response(status_code=200)

    @app.get("/.well-known/ucp")
    async def well_known_ucp():
        return JSONResponse(content=build_ucp_profile())

    @app.get("/.well-known/acp.json")
    async def well_known_acp():
        return JSONResponse(content=build_acp_discovery())

    @app.get("/.well-known/x402.json")
    async def well_known_x402():
        return JSONResponse(content=build_x402_manifest(pay_to))

    @app.get("/.well-known/agent-card.json")
    async def well_known_agent_card():
        return JSONResponse(content=build_agent_card_manifest())

    @app.get("/.well-known/glama.json")
    async def well_known_glama():
        return JSONResponse(content=build_glama_claim())

    @app.get("/.well-known/mcp.json")
    async def well_known_mcp():
        return JSONResponse(content=build_mcp_manifest())

    @app.get("/.well-known/mcp/server-card.json")
    async def well_known_mcp_server_card():
        return JSONResponse(content=build_mcp_server_card())

    @app.get("/.well-known/mcp/server-cards.json")
    async def well_known_mcp_server_cards():
        return JSONResponse(content=build_mcp_server_cards_list())

    @app.get("/.well-known/api-catalog")
    async def well_known_api_catalog():
        return JSONResponse(
            content=build_api_catalog_linkset(),
            media_type=LINKSET_JSON_MEDIA_TYPE,
        )

    @app.get("/.well-known/openid-configuration")
    async def well_known_openid_configuration():
        return JSONResponse(content=build_openid_configuration())

    @app.get("/.well-known/oauth-authorization-server")
    async def well_known_oauth_authorization_server():
        return JSONResponse(content=build_oauth_authorization_server_metadata())

    @app.get("/.well-known/oauth-protected-resource")
    async def well_known_oauth_protected_resource():
        return JSONResponse(content=build_oauth_protected_resource_metadata())

    @app.get("/.well-known/jwks.json")
    async def well_known_jwks():
        return JSONResponse(content=build_jwks_document())

    @app.get("/.well-known/agent-skills/index.json")
    async def well_known_agent_skills_index():
        return JSONResponse(content=build_agent_skills_index())

    @app.get("/.well-known/skills/index.json")
    async def well_known_agent_skills_index_legacy():
        return JSONResponse(content=build_agent_skills_index())

    @app.get("/.well-known/agent-skills/{skill_name}/SKILL.md")
    async def well_known_agent_skill_md(skill_name: str):
        p = agent_skill_markdown_path(skill_name)
        if p is None:
            return JSONResponse(status_code=404, content={"error": "skill_not_found"})
        return Response(content=p.read_bytes(), media_type="text/markdown; charset=utf-8")

    @app.get("/oauth/authorize")
    async def oauth_authorize_stub():
        return JSONResponse(status_code=501, content=oauth_stub_unavailable_payload())

    @app.post("/oauth/token")
    async def oauth_token_stub():
        return JSONResponse(status_code=501, content=oauth_stub_unavailable_payload())

    @app.get("/health")
    async def health():
        from swarm.llm import get_llm_probe_info

        return {
            "status": "ok",
            "mode": "facilitator_seller",
            "pay_to": pay_to,
            "network": network,
            "facilitator": facilitator_url,
            "facilitator_raw_env": fac_before,
            "facilitator_healthy": monitor.is_ok(),
            "routes": list(routes.keys()),
            "sku_count": len(load_base_x402_skus()),
            "llm": get_llm_probe_info(),
        }

    @app.get("/internal/x402/telemetry")
    async def internal_x402_telemetry(token: str = ""):
        """SKU/revenue attribution summary. Requires X402_TELEMETRY_TOKEN when set."""
        from services.x402_request_events import summarize_events

        expected = _env("X402_TELEMETRY_TOKEN")
        if expected and token != expected:
            return JSONResponse(status_code=401, content={"error": "unauthorized"})
        if not expected:
            # Fail closed on public deployments unless explicitly opened.
            if _env("X402_TELEMETRY_OPEN") not in ("1", "true", "yes"):
                return JSONResponse(
                    status_code=401,
                    content={"error": "set_X402_TELEMETRY_TOKEN_or_X402_TELEMETRY_OPEN"},
                )
        return summarize_events()

    from services.access_log_middleware import attach_access_log
    from services.x402_request_events import attach_fulfillment_log

    attach_access_log(app, "api_seller_x402")

    def _sku_lookup(path: str, method: str) -> dict | None:
        sku = sku_by_path(path, method)
        if sku is None:
            return None
        return {
            "skuId": sku.id,
            "quotedPriceUsd": sku.price_usd,
            "asset": sku.asset,
        }

    # Outermost: unpaid 402 short-circuits inside x402_gate.
    attach_fulfillment_log(
        app,
        service="api_seller_x402",
        sku_lookup=_sku_lookup,
        receiver=pay_to,
        facilitator=facilitator_url,
        network=network,
    )

    return app


def main():
    import uvicorn

    host = _env("X402_SELLER_HOST", "127.0.0.1")
    port = int(_env("X402_SELLER_PORT", "8043"))
    uvicorn.run("api_seller_x402:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
