"""
Durable, privacy-safe x402 request/settlement attribution events.

Writes logs/x402-fulfillment.jsonl unless X402_EVENT_LOG is set.
Set X402_EVENT_LOG=0 to disable. Never logs payment payloads or secrets.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal

PaymentStatus = Literal[
    "not_required",
    "required",
    "submitted",
    "verified",
    "settled",
    "rejected",
    "failed",
]

_lock = threading.Lock()


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _repo_root() -> Path:
    # services/ -> agents/ -> packages/ -> repo root
    return Path(__file__).resolve().parents[3]


def _resolve_log_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def event_log_enabled() -> bool:
    raw = _env("X402_EVENT_LOG")
    if raw.lower() in {"0", "off", "false", "no"}:
        return False
    return True


def event_log_path() -> Path | None:
    if not event_log_enabled():
        return None
    explicit = _env("X402_EVENT_LOG")
    if explicit and explicit.lower() not in {"1", "true", "yes"}:
        return _resolve_log_path(explicit)
    return _repo_root() / "logs" / "x402-fulfillment.jsonl"


def new_request_id() -> str:
    return uuid.uuid4().hex


def hash_body(raw: bytes | str | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="replace")
    if not raw:
        return None
    return hashlib.sha256(raw).hexdigest()


def normalize_address(addr: str | None) -> str | None:
    if not addr:
        return None
    a = addr.strip()
    if a.startswith("0x") and len(a) == 42:
        return a.lower()
    return a


def _header(headers: dict[str, str], *names: str) -> str:
    lower = {str(k).lower(): v for k, v in headers.items() if v}
    for name in names:
        val = lower.get(name.lower())
        if val:
            return str(val)
    return ""


def parse_payment_response(headers: dict[str, str]) -> dict[str, Any]:
    """Decode facilitator PAYMENT-RESPONSE without persisting the raw header."""
    raw = _header(headers, "payment-response", "x-payment-response")
    out: dict[str, Any] = {}
    if not raw:
        return out
    if raw.startswith("0x") and len(raw) == 42:
        out["payer"] = normalize_address(raw)
        return out
    text = raw
    if not raw.lstrip().startswith("{"):
        try:
            import base64

            text = base64.b64decode(raw).decode("utf-8", errors="replace")
        except Exception:
            return out
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return out
    if not isinstance(payload, dict):
        return out
    tx = (
        payload.get("transaction")
        or payload.get("transactionHash")
        or payload.get("txHash")
        or payload.get("tx_hash")
    )
    if isinstance(tx, str) and tx.startswith("0x") and len(tx) >= 66:
        out["transaction"] = tx.lower()
    elif isinstance(tx, str) and len(tx) >= 16:
        out["transaction"] = tx
    payer = payload.get("payer") or payload.get("buyer") or payload.get("from")
    if isinstance(payer, str):
        out["payer"] = normalize_address(payer)
    if "success" in payload:
        out["success"] = bool(payload.get("success"))
    return out


def extract_payer_hint(headers: dict[str, str]) -> str | None:
    parsed = parse_payment_response(headers)
    if parsed.get("payer"):
        return parsed["payer"]
    raw = _header(headers, "x-payer", "x-payment-payer")
    if raw.startswith("0x") and len(raw) == 42:
        return normalize_address(raw)
    return None


def extract_tx_hash_hint(headers: dict[str, str]) -> str | None:
    parsed = parse_payment_response(headers)
    if parsed.get("transaction"):
        return str(parsed["transaction"])
    raw = _header(
        headers,
        "x-payment-transaction-hash",
        "x-settlement-tx-hash",
        "payment-transaction-hash",
    )
    if raw.startswith("0x") and len(raw) >= 66:
        return raw.lower()
    return None


def classify_payment_status(status_code: int, headers: dict[str, str]) -> PaymentStatus:
    parsed = parse_payment_response(headers)
    if status_code == 402:
        return "required"
    if status_code >= 500:
        return "failed"
    if parsed.get("success") is False:
        return "rejected"
    if parsed.get("transaction") or extract_tx_hash_hint(headers) or "payment-response" in {
        k.lower() for k in headers
    }:
        return "settled"
    if 0 < status_code < 400:
        return "verified"
    return "rejected"


def is_delivered(payment_status: str, status_code: int) -> bool:
    return payment_status in {"settled", "verified"} and 200 <= status_code < 300


def append_event(event: dict[str, Any]) -> None:
    path = event_log_path()
    if path is None:
        return
    line = dict(event)
    line.setdefault("eventId", uuid.uuid4().hex)
    line.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    # Privacy: never persist raw payment headers
    for banned in ("PAYMENT-SIGNATURE", "payment-signature", "X-PAYMENT", "x-payment"):
        line.pop(banned, None)
    try:
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line, separators=(",", ":")) + "\n")
    except OSError:
        return


def summarize_events(max_lines: int = 5000) -> dict[str, Any]:
    path = event_log_path()
    empty = {
        "path": str(path) if path else None,
        "events": 0,
        "by_sku": {},
        "revenue_by_sku": {},
        "unique_payers": 0,
        "repeat_payers": 0,
        "success_rate": None,
        "avg_latency_ms": None,
        "p95_latency_ms": None,
        "delivered": 0,
        "failed_settlements": 0,
        "settled_but_failed_responses": 0,
        "user_agents": {},
        "hour_utc": {},
        "note": "Retention: operator-managed JSONL. Hashes only for bodies. No payment secrets.",
    }
    if path is None or not path.is_file():
        return empty

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    by_sku: dict[str, int] = {}
    revenue: dict[str, float] = {}
    payers: dict[str, int] = {}
    latencies: list[float] = []
    ua: dict[str, int] = {}
    hours: dict[int, int] = {}
    settled_ok = 0
    settled_fail = 0
    failed_pay = 0
    delivered = 0

    for r in rows:
        sku = str(r.get("skuId") or "unknown")
        by_sku[sku] = by_sku.get(sku, 0) + 1
        status = r.get("paymentStatus")
        if r.get("delivered") is True:
            delivered += 1
        if status == "settled":
            revenue[sku] = revenue.get(sku, 0.0) + float(r.get("quotedPriceUsd") or 0)
            code = r.get("responseStatus")
            if isinstance(code, int) and 200 <= code < 300:
                settled_ok += 1
            elif isinstance(code, int) and code >= 400:
                settled_fail += 1
        if status in ("rejected", "failed"):
            failed_pay += 1
        payer = r.get("payerAddress")
        if payer:
            payers[payer] = payers.get(payer, 0) + 1
        lat = r.get("responseLatencyMs")
        if isinstance(lat, (int, float)):
            latencies.append(float(lat))
        agent = r.get("userAgent") or "unknown"
        ua[agent] = ua.get(agent, 0) + 1
        ts = str(r.get("timestamp") or "")
        if len(ts) >= 13 and ts[11:13].isdigit():
            h = int(ts[11:13])
            hours[h] = hours.get(h, 0) + 1

    latencies.sort()
    p95 = None
    avg = None
    if latencies:
        avg = round(sum(latencies) / len(latencies), 2)
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]

    total_settled = settled_ok + settled_fail
    return {
        "path": str(path),
        "events": len(rows),
        "by_sku": by_sku,
        "revenue_by_sku": revenue,
        "unique_payers": len(payers),
        "repeat_payers": sum(1 for c in payers.values() if c > 1),
        "success_rate": (settled_ok / total_settled) if total_settled else None,
        "avg_latency_ms": avg,
        "p95_latency_ms": p95,
        "delivered": delivered,
        "failed_settlements": failed_pay,
        "settled_but_failed_responses": settled_fail,
        "user_agents": dict(sorted(ua.items(), key=lambda x: -x[1])[:20]),
        "hour_utc": {str(k): hours[k] for k in sorted(hours)},
        "note": empty["note"],
    }


_BODY_HASH_CAP = 256 * 1024


async def _response_body_bytes(response: Any) -> tuple[Any, bytes]:
    body = getattr(response, "body", None)
    if isinstance(body, (bytes, bytearray)):
        return response, bytes(body)
    iterator = getattr(response, "body_iterator", None)
    if iterator is None:
        return response, b""
    chunks: list[bytes] = []
    async for chunk in iterator:
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8", errors="replace")
        elif not isinstance(chunk, (bytes, bytearray)):
            chunk = bytes(chunk)
        chunks.append(bytes(chunk))
    data = b"".join(chunks)
    from starlette.responses import Response

    headers = dict(response.headers)
    headers.pop("content-length", None)
    rebuilt = Response(
        content=data,
        status_code=response.status_code,
        headers=headers,
        media_type=getattr(response, "media_type", None),
        background=getattr(response, "background", None),
    )
    return rebuilt, data


def attach_fulfillment_log(
    app: Any,
    *,
    service: str,
    sku_lookup: Any,
    receiver: str | None = None,
    facilitator: str | None = None,
    network: str | None = None,
    extra_sku_paths: set[str] | None = None,
) -> None:
    """Record SKU + HTTP outcome after every paid-path request. Outer middleware."""

    extra = extra_sku_paths or set()

    @app.middleware("http")
    async def x402_fulfillment_events(request: Any, call_next: Any) -> Any:
        start = time.perf_counter()
        response = await call_next(request)
        path = request.url.path
        sku = sku_lookup(path, request.method)
        if sku is None and path not in extra and not path.startswith("/x402/"):
            return response

        response, body = await _response_body_bytes(response)
        req_id = request.headers.get("x-request-id") or new_request_id()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        hdrs = {str(k).lower(): v for k, v in response.headers.items()}
        req_hdrs = {str(k).lower(): v for k, v in request.headers.items()}
        status_code = int(getattr(response, "status_code", 0) or 0)
        pay_status = classify_payment_status(status_code, hdrs)
        delivered = is_delivered(pay_status, status_code)
        sku_id = (sku or {}).get("skuId") or "unknown"
        query = str(request.url.query or "")[:500] or None

        append_event(
            {
                "requestId": req_id,
                "service": service,
                "method": request.method,
                "resource": path,
                "query": query,
                "skuId": sku_id,
                "quotedPriceUsd": (sku or {}).get("quotedPriceUsd"),
                "quotedPriceDrops": (sku or {}).get("quotedPriceDrops"),
                "payerAddress": extract_payer_hint(hdrs) or extract_payer_hint(req_hdrs),
                "receiverAddress": normalize_address(receiver),
                "facilitator": facilitator,
                "network": network,
                "asset": (sku or {}).get("asset"),
                "transactionHash": extract_tx_hash_hint(hdrs),
                "paymentStatus": pay_status,
                "delivered": delivered,
                "responseStatus": status_code,
                "responseLatencyMs": elapsed_ms,
                "retryCount": int(request.headers.get("x-retry-count") or 0),
                "userAgent": (request.headers.get("user-agent") or "")[:200] or None,
                "requestBodyHash": None,
                "outputHash": hash_body(body[:_BODY_HASH_CAP] if body else None),
                "outputBytes": len(body),
            }
        )
        try:
            response.headers["x-request-id"] = req_id
            if sku_id != "unknown":
                response.headers["x-asm-sku"] = sku_id
            response.headers["x-asm-delivered"] = "1" if delivered else "0"
        except Exception:
            raw = list(getattr(response, "raw_headers", []) or [])
            raw.append((b"x-request-id", req_id.encode("latin-1")))
            if sku_id != "unknown":
                raw.append((b"x-asm-sku", sku_id.encode("latin-1")))
            raw.append((b"x-asm-delivered", b"1" if delivered else b"0"))
            response.raw_headers = raw
        return response
