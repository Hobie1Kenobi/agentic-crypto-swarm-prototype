#!/usr/bin/env python3
"""
x402-style HTTP API: 402 Payment Required with AgentRevenueService.
GET/POST /query?q=... → 402 + payment headers; retry with X-Payment-Tx-Hash → verify tx and return LLM response.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[2]
for _ in range(5):
    if (root / "foundry.toml").exists() or (root / ".env.example").exists():
        break
    root = root.parent
load_dotenv(root / ".env", override=True)

def _should_load_env_local() -> bool:
    chain_id = os.getenv("CHAIN_ID", "").strip()
    rpc = os.getenv("RPC_URL", "").strip().lower()
    if os.getenv("USE_ENV_LOCAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if chain_id == "31337":
        return True
    if rpc.startswith("http://127.0.0.1") or rpc.startswith("http://localhost") or "localhost" in rpc:
        return True
    return False

if _should_load_env_local() and (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)
import sys
sys.path.insert(0, str(root / "packages" / "agents"))
from config.chains import get_rpc as _get_rpc_config, get_chain_id as _get_chain_id_config, get_native_symbol
from services.payment import get_min_payment_wei, verify_payment_tx, REVENUE_ABI


def get_rpc() -> str:
    return _get_rpc_config()


def generate_response_for_query(query: str) -> str:
    from swarm.llm import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    CONSTITUTION = "Only ethical, non-harmful services; no gambling, no illegal content; sustainable compute usage simulation."
    llm = get_llm()
    resp = llm.invoke([
        SystemMessage(content=CONSTITUTION),
        HumanMessage(content=f"Answer this query in one or two sentences (ethical AI service). Query: {query}. Output only the answer."),
    ])
    return resp.content.strip() or "Response generated."


def create_app():
    from fastapi import FastAPI, Request, Header, HTTPException
    from fastapi.responses import JSONResponse, PlainTextResponse

    app = FastAPI(title="Agentic Swarm x402 API", version="0.1.0")
    revenue_addr = os.getenv("REVENUE_SERVICE_ADDRESS")
    chain_id = str(_get_chain_id_config())
    min_payment_wei = get_min_payment_wei()
    native_symbol = get_native_symbol()
    value_eth = min_payment_wei / 1e18

    @app.get("/query")
    @app.post("/query")
    async def query(
        request: Request,
        q: str | None = None,
        x_payment_tx_hash: str | None = Header(None, alias="X-Payment-Tx-Hash"),
    ):
        body = None
        if request.method == "POST":
            try:
                body = await request.json()
            except Exception:
                pass
        query_text = q or (body.get("query") if isinstance(body, dict) else None) or ""
        if not query_text.strip():
            raise HTTPException(status_code=400, detail="Missing query (use ?q=... or JSON body {\"query\": \"...\"})")

        if not revenue_addr:
            raise HTTPException(status_code=503, detail="REVENUE_SERVICE_ADDRESS not set")

        payment_metadata = f"x402:{query_text[:200]}"
        if not x_payment_tx_hash:
            return JSONResponse(
                status_code=402,
                content={
                    "message": "Payment Required",
                    "payment": {
                        "contract": revenue_addr,
                        "amount_wei": str(min_payment_wei),
                        "chain_id": chain_id,
                        "method": "fulfillQuery(string resultMetadata)",
                        "result_metadata": payment_metadata,
                        "value_eth": str(round(value_eth, 6)),
                        "native_symbol": native_symbol,
                    },
                },
                headers={
                    "X-Payment-Contract": revenue_addr,
                    "X-Payment-Amount-Wei": str(min_payment_wei),
                    "X-Payment-Chain-Id": chain_id,
                    "X-Payment-Metadata": payment_metadata,
                    "X-Payment-Native-Symbol": native_symbol,
                },
            )

        if not verify_payment_tx(x_payment_tx_hash.strip(), revenue_addr, payment_metadata):
            raise HTTPException(status_code=402, detail="Invalid or unconfirmed payment tx")

        response_text = generate_response_for_query(query_text)
        return JSONResponse(content={"query": query_text, "response": response_text})

    @app.get("/health")
    async def health():
        return {"status": "ok", "revenue_contract": revenue_addr or "not set"}

    return app


def main():
    import uvicorn
    host = os.getenv("API_402_HOST", "127.0.0.1")
    port = int(os.getenv("API_402_PORT", "8042"))
    uvicorn.run("api_402:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    main()
