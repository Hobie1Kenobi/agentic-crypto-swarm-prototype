#!/usr/bin/env python3
"""
HTTP surface for Stripe MPP (crypto deposit) orders — optional; does not replace x402 sellers.

Set MARKETPLACE_HTTP_ENABLED=1 and STRIPE_SECRET_KEY. Run on a dedicated port (default 8055).

Includes:
  - POST /v1/orders — create PaymentIntent + pending order
  - GET /v1/orders/{payment_intent_id} — Stripe status + local fulfillment + download URL
  - POST /webhooks/stripe — Stripe webhook (STRIPE_WEBHOOK_SECRET); fulfills on payment_intent.succeeded
  - GET /v1/fulfillment/download/{token} — serve MARKETPLACE_BUNDLE_ZIP_PATH after webhook
  - GET /marketplace/success — buyer portal (polls order status)
"""

from __future__ import annotations

import json
import os
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

import sys

sys.path.insert(0, str(root / "packages" / "agents"))

from fastapi import Request
from pydantic import BaseModel, Field


class CreateOrderBody(BaseModel):
    product_id: str = Field(
        default="x402_strategy_dashboard_bundle",
        description="Catalog product id",
    )
    buyer_ref: str | None = Field(
        default=None,
        max_length=200,
        description="Optional email or opaque id for operator fulfillment",
    )


def _public_url(cfg, path: str, request: Request | None = None) -> str:
    path = path if path.startswith("/") else f"/{path}"
    if cfg.public_base_url:
        return f"{cfg.public_base_url}{path}"
    if request is not None:
        base = str(request.base_url).rstrip("/")
        return f"{base}{path}"
    return path


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

    from integrations.marketplace.config import (
        MarketplaceConfig,
        product_dashboard_bundle,
    )
    from integrations.marketplace.fulfillment import (
        finalize_pending_order,
        find_fulfillment_by_token,
        load_fulfilled,
        parse_stripe_webhook_event,
    )
    from integrations.marketplace.orders import write_pending_order
    from integrations.stripe_mpp.config import StripeMppConfig
    from integrations.stripe_mpp import create_crypto_deposit_payment_intent
    from integrations.stripe_mpp.mpp_orders_challenge import maybe_mpp_empty_orders_challenge

    app = FastAPI(title="Swarm Marketplace (Stripe MPP)", version="0.2.0")

    @app.get("/health")
    async def health():
        from swarm.llm import get_llm_probe_info

        cfg = MarketplaceConfig.from_env()
        mpp = StripeMppConfig.from_env()
        zip_ok = bool(
            cfg.bundle_zip_path and cfg.bundle_zip_path.is_file()
        )
        return {
            "status": "ok",
            "marketplace_http": cfg.http_enabled,
            "stripe_configured": bool(mpp.secret_key),
            "webhook_configured": bool(cfg.webhook_secret),
            "bundle_zip_ready": zip_ok,
            "public_base_url": cfg.public_base_url or None,
            "url_resolution": "env MARKETPLACE_PUBLIC_BASE_URL or incoming request Host",
            "llm": get_llm_probe_info(),
        }

    from well_known_discovery import (
        LINKSET_JSON_MEDIA_TYPE,
        agent_skill_markdown_path,
        build_agent_card_manifest,
        build_agent_skills_index,
        build_api_catalog_linkset,
        build_jwks_document,
        build_mcp_manifest,
        build_mcp_server_card,
        build_mcp_server_cards_list,
        build_oauth_authorization_server_metadata,
        build_oauth_protected_resource_metadata,
        build_openid_configuration,
        build_x402_manifest,
        get_seller_pay_to,
        oauth_stub_unavailable_payload,
    )

    @app.get("/.well-known/x402.json")
    async def well_known_x402():
        pay_to = get_seller_pay_to()
        if not pay_to:
            return JSONResponse(
                status_code=503,
                content={"error": "X402_SELLER_PAY_TO (or strategist key) not configured"},
            )
        return JSONResponse(content=build_x402_manifest(pay_to))

    @app.get("/.well-known/agent-card.json")
    async def well_known_agent_card():
        return JSONResponse(content=build_agent_card_manifest())

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

    @app.post("/v1/orders")
    async def create_order(request: Request):
        raw = await request.body()
        cfg = MarketplaceConfig.from_env()
        mpp = StripeMppConfig.from_env()
        challenged = await maybe_mpp_empty_orders_challenge(
            request, cfg=cfg, mpp_cfg=mpp, raw_body=raw
        )
        if challenged is not None:
            return challenged

        if not cfg.http_enabled:
            raise HTTPException(
                status_code=503,
                detail="MARKETPLACE_HTTP_ENABLED is not 1",
            )
        if not mpp.secret_key:
            raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not set")

        try:
            body = (
                CreateOrderBody.model_validate_json(raw)
                if raw.strip()
                else CreateOrderBody()
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

        prod = product_dashboard_bundle()
        if body.product_id != prod.product_id:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown product_id (supported: {prod.product_id})",
            )

        amount = cfg.dashboard_bundle_price_usd
        if amount < prod.price_usd_min:
            raise HTTPException(
                status_code=500,
                detail=f"MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD must be >= {prod.price_usd_min}",
            )

        try:
            import stripe
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Install stripe: pip install stripe",
            )

        meta = {
            "product_id": prod.product_id,
            "product_name": prod.name[:500],
        }
        if body.buyer_ref:
            meta["buyer_ref"] = body.buyer_ref[:500]

        try:
            details = create_crypto_deposit_payment_intent(
                amount_usd=amount,
                secret_key=mpp.secret_key,
                api_version=mpp.api_version,
                testnet=mpp.testnet,
                metadata=meta,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e

        path, order_ref = write_pending_order(
            cfg,
            payment_intent_id=details.payment_intent_id,
            amount_cents=details.amount_cents,
            currency=details.currency,
            pay_to_address=details.pay_to_address,
            network=details.network,
            product_id=prod.product_id,
            extra={"buyer_ref": body.buyer_ref} if body.buyer_ref else None,
        )

        try:
            pending_rel = str(path.relative_to(root))
        except ValueError:
            pending_rel = str(path)

        pi = details.payment_intent_id
        portal = _public_url(cfg, f"/marketplace/success?pi={pi}", request)

        return JSONResponse(
            {
                "order_reference": order_ref,
                "payment_intent_id": pi,
                "amount_cents": details.amount_cents,
                "currency": details.currency,
                "pay_to_address": details.pay_to_address,
                "network": details.network,
                "product_id": prod.product_id,
                "pending_order_file": pending_rel,
                "buyer_portal_url": portal,
                "instructions": (
                    "Send crypto to pay_to_address on the given network, then open buyer_portal_url "
                    "or poll GET /v1/orders/{payment_intent_id} until fulfilled is true."
                ),
            }
        )

    def _order_payload(
        cfg: MarketplaceConfig,
        payment_intent_id: str,
        pi_obj: object,
        request: Request | None,
    ) -> dict:
        try:
            import stripe
        except ImportError:
            raise HTTPException(status_code=503, detail="Install stripe")

        st = pi_obj.status if hasattr(pi_obj, "status") else pi_obj.get("status")
        amt = getattr(pi_obj, "amount_received", None)
        if amt is None and isinstance(pi_obj, dict):
            amt = pi_obj.get("amount_received")

        out: dict = {
            "payment_intent_id": payment_intent_id,
            "stripe_status": st,
            "amount_received": amt,
        }
        fulfilled = load_fulfilled(cfg, payment_intent_id)
        if fulfilled:
            tok = fulfilled.get("download_token", "")
            dl = _public_url(cfg, f"/v1/fulfillment/download/{tok}", request)
            out["fulfilled"] = True
            out["download_url"] = dl
            out["order_reference"] = fulfilled.get("order_reference")
        else:
            out["fulfilled"] = False
            out["download_url"] = None
        return out

    @app.get("/v1/orders/{payment_intent_id}")
    async def order_status(request: Request, payment_intent_id: str):
        cfg = MarketplaceConfig.from_env()
        if not cfg.http_enabled:
            raise HTTPException(status_code=503, detail="MARKETPLACE_HTTP_ENABLED is not 1")
        mpp = StripeMppConfig.from_env()
        if not mpp.secret_key:
            raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY not set")
        try:
            import stripe
        except ImportError:
            raise HTTPException(status_code=503, detail="Install stripe")

        try:
            client = stripe.StripeClient(
                mpp.secret_key,
                stripe_version=mpp.api_version,
            )
            pi = client.v1.payment_intents.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        return _order_payload(cfg, payment_intent_id, pi, request)

    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        cfg = MarketplaceConfig.from_env()
        if not cfg.webhook_secret:
            raise HTTPException(
                status_code=503,
                detail="STRIPE_WEBHOOK_SECRET not set",
            )
        payload = await request.body()
        sig = request.headers.get("stripe-signature")
        try:
            import stripe

            event = parse_stripe_webhook_event(payload, sig, cfg.webhook_secret)
        except ImportError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail="Invalid webhook signature") from e

        etype = getattr(event, "type", None)
        if etype != "payment_intent.succeeded":
            return JSONResponse({"received": True, "ignored": etype})

        data = getattr(event, "data", None)
        obj = getattr(data, "object", None) if data else None
        pi_id = getattr(obj, "id", None) if obj else None
        if not pi_id:
            return JSONResponse({"received": True, "error": "missing pi id"})

        done = finalize_pending_order(cfg, str(pi_id))
        if done:
            return JSONResponse({"received": True, "fulfilled": True, "payment_intent_id": pi_id})
        if load_fulfilled(cfg, str(pi_id)):
            return JSONResponse({"received": True, "fulfilled": True, "idempotent": True})
        return JSONResponse({"received": True, "fulfilled": False, "note": "no matching pending order"})

    @app.get("/v1/fulfillment/download/{download_token}")
    async def download_bundle(download_token: str):
        cfg = MarketplaceConfig.from_env()
        if not cfg.http_enabled:
            raise HTTPException(status_code=503, detail="MARKETPLACE_HTTP_ENABLED is not 1")
        row = find_fulfillment_by_token(cfg, download_token)
        if not row:
            raise HTTPException(status_code=404, detail="Invalid or expired download token")
        if not cfg.bundle_zip_path or not cfg.bundle_zip_path.is_file():
            raise HTTPException(
                status_code=503,
                detail="MARKETPLACE_BUNDLE_ZIP_PATH not set or file missing",
            )
        fname = cfg.bundle_zip_path.name
        return FileResponse(
            path=str(cfg.bundle_zip_path),
            filename=fname,
            media_type="application/zip",
        )

    @app.get("/marketplace/success", response_class=HTMLResponse)
    async def buyer_portal(request: Request, pi: str | None = None):
        cfg = MarketplaceConfig.from_env()
        if not cfg.http_enabled:
            return HTMLResponse(
                "<p>Marketplace HTTP is disabled (MARKETPLACE_HTTP_ENABLED).</p>", status_code=503
            )
        if not pi or not pi.startswith("pi_"):
            return HTMLResponse(
                "<!DOCTYPE html><html><body><p>Missing or invalid <code>pi</code> query parameter.</p></body></html>",
                status_code=400,
            )
        poll_url = _public_url(cfg, f"/v1/orders/{pi}", request)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Order status — Agentic Swarm Marketplace</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0a0b0f; color: #e8ecf4; margin: 0; padding: 2rem; }}
    a {{ color: #38bdf8; }}
    .box {{ max-width: 36rem; margin: 0 auto; background: #12151c; border: 1px solid #1e2530; border-radius: 12px; padding: 1.5rem; }}
    .ok {{ color: #4ade80; }}
    .wait {{ color: #fbbf24; }}
    code {{ font-size: 0.85rem; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Payment status</h1>
    <p>PaymentIntent: <code id="pi">{pi}</code></p>
    <p id="msg" class="wait">Waiting for on-chain deposit confirmation…</p>
    <p id="dl" style="display:none" class="ok">Your download is ready.</p>
    <p><a id="link" href="#" style="display:none">Download bundle (ZIP)</a></p>
    <p style="margin-top:1.5rem;font-size:0.85rem;color:#8b95a8">
      Keep this page open. After Stripe confirms payment, your file unlocks automatically.
      If nothing happens, confirm the correct amount was sent to the Tempo address from checkout.
    </p>
  </div>
  <script>
    const pollUrl = {json.dumps(poll_url)};
    async function tick() {{
      try {{
        const r = await fetch(pollUrl, {{ cache: 'no-store' }});
        const j = await r.json();
        if (j.fulfilled && j.download_url) {{
          document.getElementById('msg').style.display = 'none';
          document.getElementById('dl').style.display = 'block';
          const a = document.getElementById('link');
          a.href = j.download_url;
          a.style.display = 'inline';
          return;
        }}
      }} catch (e) {{}}
      setTimeout(tick, 4000);
    }}
    tick();
  </script>
</body>
</html>"""
        return HTMLResponse(html)

    def _apply_mpp_discovery_extensions(schema: dict) -> None:
        """MPP (Machine Payment Protocol) discovery: OpenAPI 3.1 + x-payment-info + 402 on paid ops."""
        cfg = MarketplaceConfig.from_env()
        prod = product_dashboard_bundle()
        try:
            amount_cents = str(int(cfg.dashboard_bundle_price_usd * 100))
        except Exception:
            amount_cents = "4900"
        pub = (cfg.public_base_url or "").rstrip("/") or "https://api.agentic-swarm-marketplace.com"
        www_base = "https://www.agentic-swarm-marketplace.com/agentic-crypto-swarm-prototype"
        schema["openapi"] = "3.1.0"
        schema["x-service-info"] = {
            "categories": ["commerce", "payments", "agent-marketplace"],
            "docs": {
                "homepage": f"{www_base}/",
                "apiReference": f"{pub}/docs",
                "llms": f"{www_base}/llms.txt",
            },
        }
        paths = schema.get("paths") or {}
        orders_path = paths.get("/v1/orders")
        if isinstance(orders_path, dict):
            post_op = orders_path.get("post")
            if isinstance(post_op, dict):
                post_op["x-payment-info"] = {
                    "amount": amount_cents,
                    "currency": "usd",
                    "description": (
                        f"{prod.name}: Stripe MPP PaymentIntent with crypto deposit; "
                        "POST creates the intent and returns settlement instructions."
                    ),
                    "intent": "session",
                    "method": "stripe",
                }
                responses = post_op.setdefault("responses", {})
                responses.setdefault(
                    "402",
                    {
                        "description": (
                            "Payment required (MPP): agent must satisfy Payment-Authenticate / "
                            "funding challenge before the paid resource is issued, when applicable."
                        ),
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "additionalProperties": True,
                                }
                            }
                        },
                    },
                )

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        _apply_mpp_discovery_extensions(openapi_schema)
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    from services.access_log_middleware import attach_access_log

    attach_access_log(app, "marketplace_api")
    return app


def main():
    import uvicorn

    host = os.getenv("MARKETPLACE_HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("MARKETPLACE_HTTP_PORT", "8055"))
    uvicorn.run("marketplace_api:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
