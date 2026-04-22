#!/usr/bin/env python3
"""
Facilitator x402 seller (Base USDC): ExactEvm + x402.org (or CDP) facilitator.
Default network is Base mainnet (eip155:8453). Set X402_SELLER_NETWORK=eip155:84532 only for Base Sepolia dev.

Bazaar catalogs resources after the facilitator verifies/settles payments — use
https://x402.org/facilitator or https://facilitator.cdp.coinbase.com (see _normalize_facilitator_url).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

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


_ALLOWED_FAC = (
    "https://x402.org/facilitator",
    "https://facilitator.cdp.coinbase.com",
)


def _normalize_facilitator_url(raw: str) -> tuple[str, str]:
    """Return (before_display, normalized_url). Reject non-HTTP or non-allowlisted hosts."""
    before = raw.strip().rstrip("/") or "(empty)"
    u = raw.strip().rstrip("/")
    if not u.startswith("https://"):
        return before, "https://x402.org/facilitator"
    if "x402.org/facilitator" in u:
        return before, "https://x402.org/facilitator"
    if "facilitator.cdp.coinbase.com" in u:
        return before, "https://facilitator.cdp.coinbase.com"
    return before, "https://x402.org/facilitator"


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
    from contextlib import asynccontextmanager

    from fastapi import Body, FastAPI
    from fastapi.responses import JSONResponse

    from facilitator_health import FacilitatorMonitor
    from intake_resale_sell_guard import create_intake_resale_probe_middleware
    from mcp_routing_hint import is_mcp_path, mcp_wrong_port_response
    from t54_seller_handlers import (
        run_agent_commerce_data,
        run_airdrop_intelligence_report,
        run_constitution_audit_lite,
        run_intake_resale_pack,
        run_research_brief,
    )
    from x402 import x402ResourceServer
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.register import register_exact_evm_server

    from api_402 import generate_response_for_query
    from well_known_discovery import (
        LINKSET_JSON_MEDIA_TYPE,
        build_agent_card_manifest,
        build_api_catalog_linkset,
        build_mcp_manifest,
        build_x402_manifest,
    )
    from x402_seller_bazaar import (
        bazaar_agent_commerce_data,
        bazaar_airdrop_intelligence,
        bazaar_constitution_audit,
        bazaar_contract_audit,
        bazaar_contract_monitor,
        bazaar_contract_triage,
        bazaar_query,
        bazaar_research_brief,
    )

    pay_to = _pay_to_address()
    if not pay_to:
        raise RuntimeError(
            "Set X402_SELLER_PAY_TO or ROOT_STRATEGIST_PRIVATE_KEY so facilitator knows where USDC settles."
        )

    fac_raw = _env("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator")
    fac_before, facilitator_url = _normalize_facilitator_url(fac_raw)
    network = _env("X402_SELLER_NETWORK", "eip155:8453")
    price = _usd("X402_SELLER_PRICE", "$0.01")
    data_price = _usd("X402_SELLER_DATA_PRICE", "$0.05")
    resale_price = _usd("X402_INTAKE_RESALE_PRICE", "$0.05")
    px_research = _usd("X402_SELLER_PRICE_RESEARCH", "$0.05")
    px_constitution = _usd("X402_SELLER_PRICE_CONSTITUTION", "$0.03")
    px_commerce = _usd("X402_SELLER_PRICE_COMMERCE", "$0.05")
    px_airdrop = _usd("X402_SELLER_PRICE_AIRDROP", "$0.09")
    px_triage = _usd("X402_SELLER_PRICE_TRIAGE", "$0.01")
    px_audit = _usd("X402_SELLER_PRICE_DEEP_AUDIT", "$0.50")
    px_monitor = _usd("X402_SELLER_PRICE_MONITOR", "$5.00")
    deep_audit_max_timeout = int((_env("X402_SELLER_DEEP_AUDIT_MAX_TIMEOUT_SECONDS", "180") or "180").strip() or "180")
    monitor_max_timeout = int((_env("X402_SELLER_MONITOR_MAX_TIMEOUT_SECONDS", "300") or "300").strip() or "300")

    monitor = FacilitatorMonitor(facilitator_url, disable_env="X402_FACILITATOR_HEALTH_DISABLE")

    def _merge_ext(d: dict, b) -> None:
        if b:
            d["extensions"] = b

    routes: dict = {}

    q = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": price, "network": network},
        "description": (
            "Constitution-safe structured Q&A. Returns a validated short-form answer to agent queries "
            "with source attribution. Input: natural language question. "
            "Output: JSON {answer, confidence, sources[]}."
        ),
    }
    _merge_ext(q, bazaar_query())
    routes["GET /x402/v1/query"] = q

    r_brief = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": px_research, "network": network},
        "description": (
            "Multi-section research brief generator. Produces a structured report with executive summary, "
            "findings, and citations on any topic. Ideal for agent research pipelines. "
            "Input: topic string. Output: JSON {title, summary, sections[], citations[]}."
        ),
    }
    _merge_ext(r_brief, bazaar_research_brief())
    routes["GET /x402/v1/research-brief"] = r_brief

    r_const = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": px_constitution, "network": network},
        "description": (
            "Prompt and ethics heuristic review. Screens text content or agent instructions against "
            "constitutional AI principles and policy heuristics. Returns violation flags and severity scores. "
            "Input: text string. Output: JSON {pass: bool, flags[], severity: low|medium|high}."
        ),
    }
    _merge_ext(r_const, bazaar_constitution_audit())
    routes["GET /x402/v1/constitution-audit"] = r_const

    r_com = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": px_commerce, "network": network},
        "description": (
            "Premium x402 commerce intelligence bundle. Returns live catalog snapshot, median price data, "
            "agent earning playbooks, and x402 ecosystem JSON. Used by agents building or optimizing "
            "their own marketplace presence. Input: depth param (standard|full). Output: JSON commerce bundle."
        ),
    }
    _merge_ext(r_com, bazaar_agent_commerce_data())
    routes["GET /x402/v1/agent-commerce-data"] = r_com

    r_air = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": px_airdrop, "network": network},
        "description": (
            "Smart contract malicious pattern detection and airdrop scam screening. Screens EVM contract "
            "addresses for honeypot mechanics, rug pull indicators, deployer wallet profiling, EIP-7702 "
            "delegate analysis, shared infrastructure fingerprinting, and holder concentration analysis. "
            "Returns risk score 0-100, verdict SAFE/SUSPICIOUS/MALICIOUS, top threat flags, and on-chain evidence. "
            "Supports Base chain (eip155:8453). Input: contractAddress. "
            "Output: JSON {riskScore, verdict, flags[], deployer, adminProfile, liquidityDepth, holderCount, evidence[]}."
        ),
    }
    _merge_ext(r_air, bazaar_airdrop_intelligence())
    routes["GET /x402/v1/airdrop-intelligence"] = r_air

    r_tri = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": px_triage, "network": network},
        "description": (
            "Fast EVM smart contract malicious pattern triage. 30-second static analysis screens a single "
            "contract address for honeypots, drainers, rug mechanics, trust-borrowing brand names "
            "(Vanguard, BlackRock, Trump, Federal Reserve variants), and Slither high-severity detectors. "
            "Embeds Phase 6 audit counterparty intel: EIP-7702 23-byte delegate pattern, match on known "
            "EIP7702StatelessDeleGator implementation (0x63c0…32B), SNOT / meme-style name heuristics, "
            "and deployer wallet fingerprint vs the Phase 6 SNOT operator line. "
            "Returns risk score, verdict, top flags, and phase6Intel. "
            "Input: contractAddress (required), chainId (optional, default eip155:8453). "
            "Output: JSON {riskScore, verdict, topFlags[], verified, completedIn, phase6Intel?}."
        ),
    }
    _merge_ext(r_tri, bazaar_contract_triage())
    routes["GET /x402/v1/contract-triage"] = r_tri

    r_deep = {
        "accepts": {
            "scheme": "exact",
            "payTo": pay_to,
            "price": px_audit,
            "network": network,
            "maxTimeoutSeconds": max(60, min(900, deep_audit_max_timeout)),
        },
        "description": (
            "Full 5-phase EVM smart contract security audit. Accepts up to 3 contract addresses "
            "(handles EIP-1167 proxy + implementation pairs automatically). Runs Slither static analysis, "
            "Echidna fork-mode fuzz testing (12k cycles), on-chain identity resolution, deployer wallet "
            "profiling including EIP-7702 delegate detection, money flow tracing (claim conditions, fee routing, "
            "sale recipients), and holder concentration analysis. Returns structured intelligence card per "
            "contract with confidence-scored verdict. "
            "Pricing is a single x402 v2 session authorization (maxAmountRequired = full $0.50 pipeline; "
            "not per internal RPC/sub-call). Input: addresses (comma-separated, required), "
            "chainId (optional). Output: full audit_report_v2 JSON schema."
        ),
    }
    _merge_ext(r_deep, bazaar_contract_audit())
    routes["GET /x402/v1/contract-audit"] = r_deep

    r_mon = {
        "accepts": {
            "scheme": "exact",
            "payTo": pay_to,
            "price": px_monitor,
            "network": network,
            "maxTimeoutSeconds": max(120, min(900, monitor_max_timeout)),
        },
        "description": (
            "30-day continuous monitoring subscription for EVM smart contract threat intelligence. "
            "Monitors up to 10 addresses for: admin key movement, claim condition changes, liquidity "
            "threshold breaches (configurable %), new Slither critical findings on any code update. "
            "Fires webhook on alert. Ideal for DeFi agents and wallet providers managing live positions. "
            "Input POST body: {addresses[], webhookUrl, thresholds{}, durationDays}. "
            "Output: {subscriptionId, expiresAt, status}."
        ),
    }
    _merge_ext(r_mon, bazaar_contract_monitor())
    routes["POST /x402/v1/contract-monitor"] = r_mon

    try:
        from x402.extensions.bazaar import declare_discovery_extension
        from x402.extensions.bazaar.resource_service import OutputConfig

        extensions_celo = declare_discovery_extension(
            input={"depth": "standard"},
            input_schema={
                "type": "object",
                "properties": {
                    "depth": {
                        "type": "string",
                        "description": "Payload size: standard (smaller) or full (more evidence rows)",
                        "enum": ["standard", "full"],
                    },
                },
            },
            output=OutputConfig(
                example={
                    "sku_id": "agent-commerce-data",
                    "celo_sepolia": {"task_market_report": {}},
                    "proof_run": {},
                },
            ),
        )
    except ImportError:
        extensions_celo = None

    routes["GET /x402/v1/celo-agent-data"] = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": data_price, "network": network},
        "description": (
            "Celo Sepolia + proof / soak / x402 commerce JSON bundle (public artifacts) "
            f"({network})"
        ),
    }
    if extensions_celo:
        routes["GET /x402/v1/celo-agent-data"]["extensions"] = extensions_celo

    routes["GET /x402/v1/intake-resale"] = {
        "accepts": {"scheme": "exact", "payTo": pay_to, "price": resale_price, "network": network},
        "description": "Minted intake bundle replay (same artifacts/intake_resale UUID files as T54 rail)",
    }

    fac = HTTPFacilitatorClient(FacilitatorConfig(url=facilitator_url))
    server = x402ResourceServer(fac)
    register_exact_evm_server(server, networks=[network])

    fac_lifespan = monitor.make_lifespan()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with fac_lifespan(app):
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
    app.state.facilitator_url_before = fac_before
    app.state.facilitator_url_after = facilitator_url

    _mw = payment_middleware(routes, server)

    @app.middleware("http")
    async def guard_evm_facilitator(request, call_next):
        if request.url.path in ("/", "/health"):
            return await call_next(request)
        if request.url.path.startswith("/.well-known/"):
            return await call_next(request)
        if is_mcp_path(request.url.path):
            return mcp_wrong_port_response()
        if not monitor.is_ok():
            return JSONResponse(
                status_code=503,
                content={"error": "payment_gateway_unavailable", "detail": "facilitator_unhealthy"},
            )
        return await call_next(request)

    app.middleware("http")(create_intake_resale_probe_middleware())

    @app.middleware("http")
    async def x402_gate(request, call_next):
        return await _mw(request, call_next)

    @app.get("/")
    async def root():
        return {
            "service": "agentic-swarm-x402-seller",
            "facilitator_configured_as": facilitator_url,
            "facilitator_raw_env": fac_before,
            "facilitator_healthy": monitor.is_ok(),
            "probe": "/health",
            "paid_routes": list(routes.keys()),
            "note": "Bazaar indexes after facilitator-settled payments (not direct wallet transfers).",
        }

    @app.get("/x402/v1/query")
    async def paid_query(q: str = "", depth: str = "brief"):
        if not (q or "").strip():
            return JSONResponse(status_code=400, content={"error": "Missing q (query string)"})
        text = generate_response_for_query(q.strip())
        return {
            "query": q,
            "depth": depth,
            "answer": text,
            "confidence": 0.85,
            "sources": ["agentic-swarm-x402"],
            "seller": "agentic-swarm-x402",
        }

    @app.get("/x402/v1/research-brief")
    async def paid_research_brief(topic: str = "", context: str | None = None):
        return run_research_brief(topic or "Ethical agent commerce", context).model_dump()

    @app.get("/x402/v1/constitution-audit")
    async def paid_constitution(prompt_snippet: str = ""):
        return run_constitution_audit_lite(prompt_snippet).model_dump()

    @app.get("/x402/v1/agent-commerce-data")
    async def paid_agent_commerce_data(depth: str = "standard"):
        return run_agent_commerce_data(depth).model_dump()

    @app.get("/x402/v1/airdrop-intelligence")
    async def paid_airdrop(
        topic: str = "Ethical airdrop and incentive screening",
        context: str | None = None,
        contractAddress: str | None = None,
    ):
        from marketplace.skus.smart_contract_audit import triage_contract

        base = run_airdrop_intelligence_report(topic, context).model_dump()
        if contractAddress and contractAddress.startswith("0x") and len(contractAddress) == 42:
            base["contractTriage"] = triage_contract(contractAddress, "eip155:8453")
        return base

    @app.get("/x402/v1/contract-triage")
    async def paid_triage(contractAddress: str, chainId: str = "eip155:8453"):
        from marketplace.skus.smart_contract_audit import triage_contract

        return triage_contract(contractAddress, chainId)

    @app.get("/x402/v1/contract-audit")
    async def paid_audit(addresses: str, chainId: str = "eip155:8453"):
        from marketplace.skus.smart_contract_audit import deep_audit

        parts = [p.strip() for p in addresses.split(",") if p.strip()][:3]
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
        return data

    @app.get("/x402/v1/intake-resale")
    async def paid_intake_resale(pack_id: str):
        m = run_intake_resale_pack(pack_id, revenue_usd=resale_price, rail="Base")
        return m.model_dump()

    @app.get("/.well-known/x402.json")
    async def well_known_x402():
        return JSONResponse(content=build_x402_manifest(pay_to))

    @app.get("/.well-known/agent-card.json")
    async def well_known_agent_card():
        return JSONResponse(content=build_agent_card_manifest())

    @app.get("/.well-known/mcp.json")
    async def well_known_mcp():
        return JSONResponse(content=build_mcp_manifest())

    @app.get("/.well-known/api-catalog")
    async def well_known_api_catalog():
        return JSONResponse(
            content=build_api_catalog_linkset(),
            media_type=LINKSET_JSON_MEDIA_TYPE,
        )

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
            "llm": get_llm_probe_info(),
        }

    from services.access_log_middleware import attach_access_log

    attach_access_log(app, "api_seller_x402")
    return app


def main():
    import uvicorn

    host = _env("X402_SELLER_HOST", "127.0.0.1")
    port = int(_env("X402_SELLER_PORT", "8043"))
    uvicorn.run("api_seller_x402:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
