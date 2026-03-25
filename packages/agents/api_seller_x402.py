#!/usr/bin/env python3
"""
Facilitator x402 seller (Base USDC): ExactEvm + x402.org facilitator.
Default network is Base Sepolia (eip155:84532); set X402_SELLER_NETWORK=eip155:8453 for Base mainnet
(Coinbase Bazaar / production USDC).

Celo-native payments remain on api_402 (fulfillQuery). This app is the path external marketplaces
expect (USDC + facilitator), not CELO direct.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env", override=True)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)

sys.path.insert(0, str(root / "packages" / "agents"))


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _route_description() -> str:
    n = _env("X402_SELLER_NETWORK", "eip155:84532")
    if n.endswith(":84532"):
        return "Agentic Swarm — ethical LLM query (x402 / Base Sepolia USDC)"
    if n.endswith(":8453"):
        return "Agentic Swarm — ethical LLM query (x402 / Base mainnet USDC)"
    return "Agentic Swarm — ethical LLM query (x402 / USDC)"


def _pay_to_address() -> str:
    explicit = _env("X402_SELLER_PAY_TO")
    if explicit.startswith("0x") and len(explicit) == 42:
        return explicit
    pk = _env("ROOT_STRATEGIST_PRIVATE_KEY") or _env("X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY")
    if pk and "0x" in pk:
        try:
            from eth_account import Account
            return Account.from_key(pk).address
        except Exception:
            pass
    return ""


def create_app():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from x402 import x402ResourceServer
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.register import register_exact_evm_server

    from api_402 import generate_response_for_query

    pay_to = _pay_to_address()
    if not pay_to:
        raise RuntimeError(
            "Set X402_SELLER_PAY_TO or ROOT_STRATEGIST_PRIVATE_KEY so facilitator knows where USDC settles."
        )

    facilitator_url = _env("X402_TEST_FACILITATOR_URL", "https://x402.org/facilitator")
    network = _env("X402_SELLER_NETWORK", "eip155:84532")
    price = _env("X402_SELLER_PRICE", "$0.01")

    try:
        from x402.extensions.bazaar import declare_discovery_extension
        from x402.extensions.bazaar.resource_service import OutputConfig

        extensions = declare_discovery_extension(
            input={"q": "What is ethical AI agent commerce?"},
            input_schema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "User question (ethical AI service)"},
                },
                "required": ["q"],
            },
            output=OutputConfig(
                example={"query": "example", "response": "Short ethical answer."},
            ),
        )
    except ImportError:
        extensions = None

    routes: dict = {
        "GET /x402/v1/query": {
            "accepts": {
                "scheme": "exact",
                "payTo": pay_to,
                "price": price,
                "network": network,
            },
            "description": _route_description(),
        }
    }
    if extensions:
        routes["GET /x402/v1/query"]["extensions"] = extensions

    fac = HTTPFacilitatorClient(FacilitatorConfig(url=facilitator_url))
    server = x402ResourceServer(fac)
    register_exact_evm_server(server, networks=[network])

    app = FastAPI(title="Agentic Swarm x402 Seller (facilitator)", version="0.1.0")

    _mw = payment_middleware(routes, server)

    @app.middleware("http")
    async def x402_gate(request, call_next):
        return await _mw(request, call_next)

    @app.get("/x402/v1/query")
    async def paid_query(q: str = ""):
        if not (q or "").strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Missing q (query string)"},
            )
        text = generate_response_for_query(q.strip())
        return {"query": q, "response": text, "seller": "agentic-swarm-x402"}

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "mode": "facilitator_seller",
            "pay_to": pay_to,
            "network": network,
            "price": price,
            "facilitator": facilitator_url,
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
