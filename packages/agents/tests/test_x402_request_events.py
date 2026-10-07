from __future__ import annotations

import base64
import json

from services.x402_request_events import (
    classify_payment_status,
    event_log_path,
    is_delivered,
    parse_payment_response,
)


def test_event_log_defaults_to_logs(monkeypatch):
    monkeypatch.delenv("X402_EVENT_LOG", raising=False)
    path = event_log_path()
    assert path is not None
    assert path.name == "x402-fulfillment.jsonl"
    assert path.parts[-2] == "logs"


def test_event_log_disabled(monkeypatch):
    monkeypatch.setenv("X402_EVENT_LOG", "0")
    assert event_log_path() is None


def test_event_log_explicit_path(monkeypatch, tmp_path):
    target = tmp_path / "events.jsonl"
    monkeypatch.setenv("X402_EVENT_LOG", str(target))
    assert event_log_path() == target


def test_parse_payment_response_base64():
    payload = {
        "success": True,
        "transaction": "0x" + "ab" * 32,
        "payer": "0x" + "11" * 20,
    }
    raw = base64.b64encode(json.dumps(payload).encode()).decode()
    parsed = parse_payment_response({"PAYMENT-RESPONSE": raw})
    assert parsed["success"] is True
    assert parsed["transaction"] == "0x" + "ab" * 32
    assert parsed["payer"] == "0x" + "11" * 20


def test_parse_payment_response_json():
    parsed = parse_payment_response(
        {
            "payment-response": json.dumps(
                {"success": True, "txHash": "0x" + "cd" * 32, "buyer": "0x" + "22" * 20}
            )
        }
    )
    assert parsed["transaction"].startswith("0xcd")
    assert parsed["payer"].startswith("0x22")


def test_fulfillment_middleware_writes_delivered(monkeypatch, tmp_path):
    log = tmp_path / "fulfillment.jsonl"
    monkeypatch.setenv("X402_EVENT_LOG", str(log))
    monkeypatch.setenv("SELLER_ACCESS_LOG", "0")
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient

    from services.x402_request_events import attach_fulfillment_log

    app = FastAPI()

    @app.get("/x402/v1/contract-triage")
    def triage():
        return {"sku": "contract-triage", "ok": True}

    @app.get("/x402/v1/unpaid")
    def unpaid():
        return JSONResponse(status_code=402, content={"error": "payment required"})

    attach_fulfillment_log(
        app,
        service="test_seller",
        sku_lookup=lambda path, _method: {
            "skuId": "contract-triage" if "triage" in path else "unknown",
            "quotedPriceUsd": 0.02,
            "asset": "USDC",
        },
    )
    client = TestClient(app)
    paid = client.get("/x402/v1/contract-triage")
    assert paid.status_code == 200
    assert paid.headers["x-asm-delivered"] == "1"
    unpaid_resp = client.get("/x402/v1/unpaid")
    assert unpaid_resp.status_code == 402
    assert unpaid_resp.headers["x-asm-delivered"] == "0"
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    assert events[0]["delivered"] is True
    assert events[0]["skuId"] == "contract-triage"
    assert events[0]["outputBytes"] > 0
    assert events[0]["outputHash"]
    assert events[1]["delivered"] is False
    assert events[1]["paymentStatus"] == "required"


def test_classify_and_delivered():
    tx = "0x" + "ef" * 32
    settled_headers = {
        "payment-response": json.dumps({"success": True, "transaction": tx})
    }
    assert classify_payment_status(200, settled_headers) == "settled"
    assert is_delivered("settled", 200) is True
    assert is_delivered("settled", 500) is False
    assert classify_payment_status(402, {}) == "required"
    assert is_delivered("required", 402) is False
    assert classify_payment_status(200, {}) == "verified"
    assert is_delivered("verified", 200) is True
    assert classify_payment_status(
        200, {"payment-response": json.dumps({"success": False})}
    ) == "rejected"
