#!/usr/bin/env python3
"""Celo mainnet USDC x402 seller (separate from Base CDP/PayAI seller).

Uses Celo hosted facilitator https://api.x402.celo.org — CDP/PayAI do NOT
support eip155:42220. Requires CELO_X402_API_KEY (X-API-Key) for /settle.

Run (local):
  CELO_X402_API_KEY=... python -m uvicorn api_seller_celo_x402:create_app --factory --host 127.0.0.1 --port 8044

Do not point X402_TEST_FACILITATOR_URL of the Base seller here.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

_log = logging.getLogger("api_seller_celo_x402")

ROOT = Path(__file__).resolve().parents[2]
for name in (".env", ".env.mainnet", ".env.mainnet.secure"):
    p = ROOT / name
    if p.is_file():
        load_dotenv(p, override=False)

_FAC_CELO = "https://api.x402.celo.org"
_NETWORK = "eip155:42220"
_USDC = "0xcebA9300f2b948710d2653dD7B07f33A8B32118C"
_USDC_EXTRA = {"name": "USDC", "version": "2"}


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _pay_to() -> str:
    for key in ("X402_SELLER_PAY_TO", "CELO_X402_PAY_TO", "DEPLOYER_ADDRESS"):
        v = _env(key)
        if v.startswith("0x") and len(v) == 42:
            return v
    return ""


def _api_key() -> str:
    return _env("CELO_X402_API_KEY") or _env("X402_API_KEY")


def _amount_atomic(usd: float) -> str:
    # USDC 6 decimals
    return str(int(round(usd * 1_000_000)))


def _price(usd: float) -> dict:
    return {
        "amount": _amount_atomic(usd),
        "asset": _USDC,
        "extra": dict(_USDC_EXTRA),
    }


def create_app():
    import asyncio

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, CreateHeadersAuthProvider
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.register import register_exact_evm_server
    from x402.server import x402ResourceServer

    try:
        from x402.extensions.bazaar import bazaar_resource_server_extension, declare_discovery_extension, OutputConfig
    except Exception:  # pragma: no cover - optional until package present
        bazaar_resource_server_extension = None
        declare_discovery_extension = None
        OutputConfig = None

    pay_to = _pay_to()
    if not pay_to:
        raise RuntimeError("Set X402_SELLER_PAY_TO (or CELO_X402_PAY_TO) for Celo USDC settles")

    api_key = _api_key()
    if not api_key:
        _log.warning(
            "CELO_X402_API_KEY / X402_API_KEY unset — /verify may work but /settle returns 401"
        )

    def _create_headers():
        if not api_key:
            return {}
        h = {"X-API-Key": api_key}
        return {"verify": h, "settle": h, "supported": h}

    fac = HTTPFacilitatorClient(
        FacilitatorConfig(
            url=_FAC_CELO,
            auth_provider=CreateHeadersAuthProvider(_create_headers) if api_key else None,
        )
    )
    server = x402ResourceServer(fac)
    register_exact_evm_server(server, networks=[_NETWORK])
    if bazaar_resource_server_extension is not None:
        server.register_extension(bazaar_resource_server_extension)

    query_price = float(_env("CELO_X402_QUERY_USD", "0.01") or "0.01")
    accepts = {
        "scheme": "exact",
        "network": _NETWORK,
        "payTo": pay_to,
        "price": _price(query_price),
    }
    row = {
        "accepts": accepts,
        "description": (
            "Constitution-safe short-form answer on Celo USDC x402 "
            "(eip155:42220). Use for lightweight Q&A settled via Celo facilitator."
        ),
        "mimeType": "application/json",
    }
    if declare_discovery_extension is not None:
        row["extensions"] = declare_discovery_extension(
            input={"q": "What is x402 micropayment settlement?"},
            input_schema={
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
            output=OutputConfig(
                example={
                    "query": "What is x402 micropayment settlement?",
                    "answer": "x402 settles HTTP 402 challenges with on-chain payments.",
                    "network": _NETWORK,
                }
            ),
        )

    routes = {
        "GET /celo/x402/v1/query": row,
        "HEAD /celo/x402/v1/query": row,
        "GET /x402/celo/v1/query": row,
        "HEAD /x402/celo/v1/query": row,
    }

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.celo_x402_ready = bool(api_key)
        yield

    app = FastAPI(
        title="Agentic Swarm Celo USDC x402 Seller",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["*"],
    )

    _mw = payment_middleware(routes, server)

    @app.middleware("http")
    async def force_https(request, call_next):
        public = _env("PUBLIC_API_ORIGIN") or _env("CELO_X402_PUBLIC_URL")
        xf = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        if xf == "https" or (public and public.startswith("https://")):
            request.scope["scheme"] = "https"
        if request.method == "HEAD":
            request.scope["method"] = "GET"
        return await call_next(request)

    @app.middleware("http")
    async def x402_gate(request, call_next):
        path = request.url.path or ""
        if path in ("/", "/health") or path.startswith("/.well-known/"):
            return await call_next(request)
        try:
            return await _mw(request, call_next)
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "celo_x402_gateway_unavailable",
                    "detail": str(exc),
                    "facilitator": _FAC_CELO,
                    "network": _NETWORK,
                    "hint": "Set CELO_X402_API_KEY from https://x402.celo.org",
                },
            )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "api_seller_celo_x402",
            "network": _NETWORK,
            "asset": _USDC,
            "facilitator": _FAC_CELO,
            "pay_to": pay_to,
            "api_key_configured": bool(api_key),
            "note": (
                "CDP/PayAI do not index eip155:42220. "
                "Discovery is Celo facilitator + agent402/8004/Buy."
            ),
        }

    @app.get("/")
    async def root():
        return await health()

    @app.get("/celo/x402/v1/query")
    @app.get("/x402/celo/v1/query")
    async def paid_query(q: str = "ping"):
        return {
            "query": q,
            "answer": "Celo USDC x402 path live.",
            "network": _NETWORK,
            "rail": "celo_usdc_facilitator",
        }

    return app


def main():
    import uvicorn

    host = _env("CELO_X402_HOST", "127.0.0.1")
    port = int(_env("CELO_X402_PORT", "8044") or "8044")
    uvicorn.run("api_seller_celo_x402:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
