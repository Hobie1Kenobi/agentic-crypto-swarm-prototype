"""
T54 XRPL x402 seller — FastAPI app: 402 + xrpl:0 terms; t54 facilitator verifies/settles.

Multi-SKU: paths and prices come from config/t54_seller_skus.json (override with T54_SELLER_SKUS_JSON).
Each SKU has its own require_payment middleware (per-path pricing).

Env (see docs/T54_SELLER.md):
  XRPL_RECEIVER_ADDRESS or T54_LOCAL_MERCHANT_PAY_TO — receive XRP
  XRPL_FACILITATOR_URL — default https://xrpl-facilitator-mainnet.t54.ai
  T54_SELLER_NETWORK — xrpl:0 mainnet (default) or xrpl:1 testnet
"""
from __future__ import annotations

import os
from typing import Any


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def create_t54_seller_app() -> Any:
    from fastapi import FastAPI, Query

    try:
        from x402_xrpl.server.fastapi import require_payment
    except ImportError as e:
        raise RuntimeError("pip install fastapi uvicorn x402-xrpl python-dotenv") from e

    from pydantic import ValidationError

    from t54_seller_catalog import load_t54_seller_skus
    from t54_seller_handlers import (
        run_constitution_audit_lite,
        run_hello,
        run_research_brief,
        run_structured_query,
    )
    from t54_seller_models import (
        ConstitutionAuditLiteResponse,
        HelloResponse,
        ResearchBriefResponse,
        StructuredQueryResponse,
    )

    pay_to = _env("T54_LOCAL_MERCHANT_PAY_TO") or _env("XRPL_RECEIVER_ADDRESS") or _env("T54_SELLER_PAY_TO")
    if not pay_to.startswith("r"):
        raise RuntimeError(
            "Set XRPL_RECEIVER_ADDRESS or T54_LOCAL_MERCHANT_PAY_TO to your XRPL r-address (seller receives here)."
        )

    fac = _env("XRPL_FACILITATOR_URL", "https://xrpl-facilitator-mainnet.t54.ai")
    network = _env("T54_SELLER_NETWORK", "xrpl:0")

    skus = load_t54_seller_skus()

    model_for_handler: dict[str, type] = {
        "hello": HelloResponse,
        "structured_query": StructuredQueryResponse,
        "research_brief": ResearchBriefResponse,
        "constitution_audit_lite": ConstitutionAuditLiteResponse,
    }

    app = FastAPI(title="T54 XRPL x402 Seller", version="1.1.0")

    for sku in skus:
        hid = sku["handler"]
        if hid not in model_for_handler:
            raise RuntimeError(f"Unknown handler {hid!r} for sku {sku.get('sku_id')}")
        model_cls = model_for_handler[hid]
        app.middleware("http")(
            require_payment(
                path=sku["path"],
                price=str(sku["price_drops"]),
                pay_to_address=pay_to,
                facilitator_url=fac,
                network=network,
                asset="XRP",
                description=sku["description"],
                output_schema=model_cls.model_json_schema(),
            )
        )

    from fastapi.responses import JSONResponse

    def _dump(model: Any) -> dict[str, Any]:
        if isinstance(model, dict):
            return model
        return model.model_dump()

    def _err_val(e: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "validation_failed", "detail": e.errors()})

    def _err_exc(exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "handler_failed", "detail": str(exc)[:500]})

    def _mk_hello(pp: str) -> Any:
        async def _route() -> Any:
            try:
                return _dump(run_hello(pp))
            except ValidationError as e:
                return _err_val(e)
            except Exception as exc:
                return _err_exc(exc)

        return _route

    def _mk_structured(sku_id: str) -> Any:
        async def _route(
            q: str = Query(default="What is ethical agent commerce?", max_length=512),
        ) -> Any:
            try:
                return _dump(run_structured_query(q))
            except ValidationError as e:
                return _err_val(e)
            except Exception as exc:
                return _err_exc(exc)

        _route.__name__ = f"t54_route_{sku_id.replace('-', '_')}"
        return _route

    def _mk_research(sku_id: str) -> Any:
        async def _route(
            topic: str = Query(default="Ethical agent commerce on testnets", max_length=256),
            context: str | None = Query(default=None, max_length=2000),
        ) -> Any:
            try:
                return _dump(run_research_brief(topic, context))
            except ValidationError as e:
                return _err_val(e)
            except Exception as exc:
                return _err_exc(exc)

        _route.__name__ = f"t54_route_{sku_id.replace('-', '_')}"
        return _route

    def _mk_constitution(sku_id: str) -> Any:
        async def _route(
            prompt_snippet: str = Query(default="", max_length=4000),
        ) -> Any:
            try:
                return _dump(run_constitution_audit_lite(prompt_snippet))
            except ValidationError as e:
                return _err_val(e)
            except Exception as exc:
                return _err_exc(exc)

        _route.__name__ = f"t54_route_{sku_id.replace('-', '_')}"
        return _route

    for sku in skus:
        hid = sku["handler"]
        p = sku["path"]
        sid = sku["sku_id"]

        if hid == "hello":
            app.add_api_route(p, _mk_hello(p), methods=["GET"])
        elif hid == "structured_query":
            app.add_api_route(p, _mk_structured(sid), methods=["GET"])
        elif hid == "research_brief":
            app.add_api_route(p, _mk_research(sid), methods=["GET"])
        elif hid == "constitution_audit_lite":
            app.add_api_route(p, _mk_constitution(sid), methods=["GET"])
        else:
            raise RuntimeError(f"Unhandled handler {hid}")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "seller": "t54_xrpl",
            "pay_to": pay_to[:9] + "...",
            "network": network,
            "facilitator": fac,
            "skus": [
                {
                    "sku_id": s["sku_id"],
                    "path": s["path"],
                    "price_drops": s["price_drops"],
                    "description": s["description"],
                }
                for s in skus
            ],
        }

    return app
