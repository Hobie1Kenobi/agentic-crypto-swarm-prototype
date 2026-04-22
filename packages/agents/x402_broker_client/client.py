"""
Programmatic x402 broker for T54 XRPL sellers: 402 → parse challenge → pay (injectable) → retry with proof.

For real XRPL signing, use `xrpl_testnet_pay_invoice`, `xrpl_mainnet_pay_invoice`,
`integrations.t54_xrpl.xumm_payment_builder.xumm_mainnet_pay_invoice` (Xaman human-in-the-loop),
`integrations.t54_xrpl.adapter.T54XrplAdapter.invoke`, or `mock_pay_invoice`.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

import requests

PayInvoiceFn = Callable[[dict[str, Any]], dict[str, str]]


@dataclass
class PaymentChallenge:
    raw_status: int
    body: dict[str, Any] | None
    headers: dict[str, str] = field(default_factory=dict)
    accepted: dict[str, Any] | None = None


def parse_payment_challenge(resp: requests.Response) -> dict[str, Any] | None:
    """Extract machine-readable payment terms from a 402 response (headers + JSON body)."""
    pr = resp.headers.get("PAYMENT-REQUIRED") or resp.headers.get("X-Payment-Required")
    if pr:
        try:
            raw = base64.b64decode(pr)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            pass
    try:
        if resp.content:
            body = resp.json()
            if isinstance(body, dict):
                from external_commerce.x402_evm_payload import normalize_v2_challenge_dict

                body = normalize_v2_challenge_dict(body)
                nested = body.get("payment")
                if isinstance(nested, dict):
                    return nested
                if body.get("accepts") is not None or body.get("x402Version") is not None:
                    return body
                return body
    except Exception:
        pass
    return None


def _extract_accepted(pr: dict[str, Any]) -> dict[str, Any] | None:
    accepts = pr.get("accepts")
    if isinstance(accepts, list) and accepts:
        candidates = [a for a in accepts if isinstance(a, dict)]
        for a in candidates:
            net = str(a.get("network", "")).lower()
            if net == "eip155:8453":
                return a
        for a in candidates:
            if a.get("scheme") == "exact" or "xrpl" in str(a.get("network", "")).lower():
                return a
        return candidates[0]
    if isinstance(pr.get("accepted"), dict):
        return pr["accepted"]
    return None


def _agent_xrpl_seed() -> str:
    """
    Seed for autonomous XRPL Payment signing (x402 broker testnet/mainnet).

    Order: AGENT_XRPL_WALLET_SEED, XRPL_WALLET_SEED, SWARM_AGENT_XRPL_SEED, XRPL_PAYER_WALLET_SEED,
    XRPL_SETTLEMENT_WALLET_SEED, XRPL_RECEIVER_SEED (legacy name — automation payer only; not payTo).

    Must differ from T54 payTo (merchant receive). Typical split: payTo = Xaman (XRPL_RECEIVER_ADDRESS),
    payer = seeded hot wallet. Values only from env, never from source.
    """
    return (
        (os.getenv("AGENT_XRPL_WALLET_SEED") or "").strip()
        or (os.getenv("XRPL_WALLET_SEED") or "").strip()
        or (os.getenv("SWARM_AGENT_XRPL_SEED") or "").strip()
        or (os.getenv("XRPL_PAYER_WALLET_SEED") or "").strip()
        or (os.getenv("XRPL_SETTLEMENT_WALLET_SEED") or "").strip()
        or (os.getenv("XRPL_RECEIVER_SEED") or "").strip()
    )


def _max_spend_drops_per_tx() -> int | None:
    """
    Optional cap for XRPL payment amount (drops). None = no cap (Testnet only safe default).
    Set MAX_XRP_SPEND_PER_TX_DROPS (integer string) or MAX_XRP_SPEND_PER_TX (XRP decimal, e.g. 2.5).
    """
    raw_drops = (os.getenv("MAX_XRP_SPEND_PER_TX_DROPS") or "").strip()
    if raw_drops:
        return int(raw_drops)
    raw_xrp = (os.getenv("MAX_XRP_SPEND_PER_TX") or "").strip()
    if not raw_xrp:
        return None
    d = Decimal(raw_xrp)
    return int(d * Decimal(10**6))


def _enforce_max_spend(amount_drops: int, *, ledger_network: str) -> None:
    cap = _max_spend_drops_per_tx()
    if ledger_network == "mainnet" and cap is None:
        raise ValueError(
            "Mainnet requires MAX_XRP_SPEND_PER_TX (XRP) or MAX_XRP_SPEND_PER_TX_DROPS to prevent unbounded spend"
        )
    if cap is None:
        return
    if amount_drops > cap:
        raise ValueError(
            f"402 amount {amount_drops} drops exceeds cap {cap} drops (MAX_XRP_SPEND_PER_TX*)"
        )


def _build_payment_signature_b64(
    signed_blob_hex: str,
    accepted: dict[str, Any],
    network: str,
    invoice_id: str,
    tx_hash: str | None = None,
) -> str:
    payload = {
        "x402Version": 2,
        "accepted": {
            "scheme": accepted.get("scheme", "exact"),
            "network": network,
            "asset": accepted.get("asset", "XRP"),
            "payTo": accepted.get("payTo", accepted.get("pay_to", "")),
            "amount": str(accepted.get("amount", "0")),
            "maxTimeoutSeconds": accepted.get("maxTimeoutSeconds", 600),
            "extra": {
                **(accepted.get("extra") if isinstance(accepted.get("extra"), dict) else {}),
                "invoiceId": invoice_id,
            },
        },
        "payload": {
            "signedTxBlob": _normalize_signed_tx_blob_hex(signed_blob_hex),
            "invoiceId": invoice_id,
            **({"xrplTxHash": tx_hash} if tx_hash else {}),
        },
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def _normalize_signed_tx_blob_hex(h: str) -> str:
    """T54 facilitator expects raw hex (no 0x prefix) for signedTxBlob."""
    s = (h or "").strip()
    if s.startswith("0x"):
        return s[2:]
    return s


def xrpl_testnet_pay_invoice(challenge: dict[str, Any]) -> dict[str, str]:
    """
    Sign + submit an XRPL Testnet Payment from 402 `accepts`, then return PAYMENT-SIGNATURE (+ tx hash headers).

    Requires a funded Testnet wallet: AGENT_XRPL_WALLET_SEED (or XRPL_WALLET_SEED).
    Rejects **xrpl:0** (mainnet) — use `xrpl_mainnet_pay_invoice` / mode `xrpl_mainnet`.
    """
    from integrations.t54_xrpl.payment_builder import sign_submit_xrpl_payment

    accepted = _extract_accepted(challenge) or {}
    if not accepted:
        raise ValueError("xrpl_testnet_pay_invoice: no accepted terms in challenge")
    network_id = str(accepted.get("network", "xrpl:1"))
    if network_id == "xrpl:0":
        raise ValueError("xrpl_testnet_pay_invoice: xrpl:0 is mainnet — set X402_BROKER_PAY_MODE=xrpl_mainnet")
    pay_to = accepted.get("payTo") or accepted.get("pay_to", "")
    amount = str(accepted.get("amount", "0"))
    try:
        amount_drops = int(amount)
    except ValueError as e:
        raise ValueError(f"invalid amount drops: {amount}") from e
    _enforce_max_spend(amount_drops, ledger_network="testnet")
    seed = _agent_xrpl_seed()
    if not seed:
        raise ValueError(
            "Set AGENT_XRPL_WALLET_SEED, XRPL_WALLET_SEED, XRPL_PAYER_WALLET_SEED, XRPL_SETTLEMENT_WALLET_SEED, "
            "or XRPL_RECEIVER_SEED (legacy payer seed) to a funded wallet whose address is not T54 payTo."
        )
    extra = accepted.get("extra") if isinstance(accepted.get("extra"), dict) else {}
    invoice_id = (
        str(extra.get("invoiceId") or extra.get("invoice_id") or "") or f"inv-{int(time.time())}"
    )
    st = int(extra.get("sourceTag", extra.get("source_tag", 804681468)))
    dt = extra.get("destinationTag") or extra.get("destination_tag")
    dest_tag = int(dt) if dt is not None else None

    tx_hash, blob, err = sign_submit_xrpl_payment(
        wallet_seed=seed,
        pay_to=pay_to,
        amount_drops=amount,
        invoice_id=invoice_id,
        source_tag=st,
        destination_tag=dest_tag,
        network="testnet",
    )
    if err or not blob:
        raise RuntimeError(err or "sign_submit_failed")
    b64 = _build_payment_signature_b64(blob, accepted, network_id, invoice_id, tx_hash=tx_hash)
    headers: dict[str, str] = {"PAYMENT-SIGNATURE": b64}
    if tx_hash:
        headers["X-XRPL-TX-Hash"] = tx_hash
        headers["Authorization"] = f"X402-TxID {tx_hash}"
    return headers


def xrpl_mainnet_pay_invoice(challenge: dict[str, Any]) -> dict[str, str]:
    """
    Sign a **Mainnet** XRPL Payment blob (xrpl:0) for PAYMENT-SIGNATURE; do not submit on-chain here.
    T54 facilitator submits / settles — local submit + facilitator submit caused tefPAST_SEQ (double spend).

    Safety:
    - Requires **MAX_XRP_SPEND_PER_TX** or **MAX_XRP_SPEND_PER_TX_DROPS** (no unbounded pay).
    - Set **X402_BROKER_MAINNET_ACK=1** to confirm intentional mainnet spend from this process.
    """
    from integrations.t54_xrpl.payment_builder import build_presigned_xrpl_payment

    ack = (os.getenv("X402_BROKER_MAINNET_ACK") or "").strip().lower()
    if ack not in {"1", "true", "yes", "i_understand"}:
        raise ValueError(
            "Mainnet broker: set X402_BROKER_MAINNET_ACK=1 (or true) after reviewing spend caps and seed handling"
        )

    accepted = _extract_accepted(challenge) or {}
    if not accepted:
        raise ValueError("xrpl_mainnet_pay_invoice: no accepted terms in challenge")
    network_id = str(accepted.get("network", ""))
    if network_id != "xrpl:0":
        raise ValueError(f"xrpl_mainnet_pay_invoice: expected network xrpl:0, got {network_id}")

    pay_to = accepted.get("payTo") or accepted.get("pay_to", "")
    amount = str(accepted.get("amount", "0"))
    try:
        amount_drops = int(amount)
    except ValueError as e:
        raise ValueError(f"invalid amount drops: {amount}") from e
    _enforce_max_spend(amount_drops, ledger_network="mainnet")

    seed = _agent_xrpl_seed()
    if not seed:
        raise ValueError(
            "Set AGENT_XRPL_WALLET_SEED, XRPL_WALLET_SEED, XRPL_PAYER_WALLET_SEED, XRPL_SETTLEMENT_WALLET_SEED, "
            "or XRPL_RECEIVER_SEED (legacy payer seed) to a funded wallet whose address is not T54 payTo."
        )

    extra = accepted.get("extra") if isinstance(accepted.get("extra"), dict) else {}
    invoice_id = (
        str(extra.get("invoiceId") or extra.get("invoice_id") or "") or f"inv-{int(time.time())}"
    )
    st = int(extra.get("sourceTag", extra.get("source_tag", 804681468)))
    dt = extra.get("destinationTag") or extra.get("destination_tag")
    dest_tag = int(dt) if dt is not None else None

    blob, err = build_presigned_xrpl_payment(
        wallet_seed=seed,
        pay_to=pay_to,
        amount_drops=amount,
        invoice_id=invoice_id,
        source_tag=st,
        destination_tag=dest_tag,
        network="mainnet",
    )
    if err or not blob:
        raise RuntimeError(err or "build_presigned_failed")
    tx_hash = None
    b64 = _build_payment_signature_b64(blob, accepted, network_id, invoice_id, tx_hash=tx_hash)
    headers: dict[str, str] = {"PAYMENT-SIGNATURE": b64}
    if tx_hash:
        headers["X-XRPL-TX-Hash"] = tx_hash
        headers["Authorization"] = f"X402-TxID {tx_hash}"
    return headers


def get_pay_invoice_fn() -> PayInvoiceFn:
    mode = (os.getenv("X402_BROKER_PAY_MODE") or os.getenv("X402_PAY_MODE") or "mock").strip().lower()
    if mode in ("xumm_mainnet", "xaman_mainnet", "xumm"):
        from integrations.t54_xrpl.xumm_payment_builder import xumm_mainnet_pay_invoice

        return xumm_mainnet_pay_invoice
    if mode in ("xrpl_mainnet", "mainnet", "xrp_mainnet"):
        return xrpl_mainnet_pay_invoice
    if mode in ("xrpl_testnet", "testnet", "xrpl"):
        return xrpl_testnet_pay_invoice
    if mode in ("base_usdc", "evm_base", "base_evm", "base"):
        from external_commerce.x402_evm_payload import evm_exact_pay_invoice

        return evm_exact_pay_invoice
    return mock_pay_invoice


def mock_pay_invoice(challenge: dict[str, Any]) -> dict[str, str]:
    """
    Placeholder: returns a PAYMENT-SIGNATURE header value that will NOT settle on mainnet.
    Swap for real signing via Xaman / T54 presign (see `T54XrplAdapter`).
    """
    accepted = _extract_accepted(challenge) or {}
    payload = {
        "x402Version": 2,
        "accepted": {
            "scheme": accepted.get("scheme", "exact"),
            "network": accepted.get("network", "xrpl:0"),
            "asset": accepted.get("asset", "XRP"),
            "payTo": accepted.get("payTo", accepted.get("pay_to", "")),
            "amount": accepted.get("amount", "0"),
            "extra": accepted.get("extra") or {},
        },
        "payload": {"signedTxBlob": "0xMOCK", "note": "mock_pay_invoice — replace with real XRPL blob"},
    }
    b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {"PAYMENT-SIGNATURE": b64}


def _x402_http_call(
    sess: requests.Session,
    method: str,
    endpoint_url: str,
    *,
    params: dict[str, str] | None,
    json_body: dict[str, Any] | None,
    headers: dict[str, str] | None,
    timeout: float,
) -> requests.Response:
    m = method.upper()
    kw: dict[str, Any] = {"timeout": timeout}
    if params:
        kw["params"] = params
    if headers:
        kw["headers"] = headers
    if m == "GET":
        kw["params"] = params or {}
        return sess.get(endpoint_url, **kw)
    if m == "DELETE":
        if json_body:
            kw["json"] = json_body
        return sess.delete(endpoint_url, **kw)
    if m in {"POST", "PUT", "PATCH"}:
        kw["json"] = json_body or {}
        return getattr(sess, m.lower())(endpoint_url, **kw)
    return sess.request(m, endpoint_url, json=json_body if json_body else None, params=params or {}, timeout=timeout)


def execute_x402_request(
    endpoint_url: str,
    payload: dict[str, Any] | None = None,
    method: str = "GET",
    params: dict[str, str] | None = None,
    timeout: float = 120.0,
    pay_invoice: PayInvoiceFn | None = None,
    session: requests.Session | None = None,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """
    1) Initial request. 2) On 402, parse challenge. 3) Call `pay_invoice` for proof headers. 4) Retry.

    `payload` is the JSON body for POST/PUT/PATCH (and optional DELETE). GET ignores it.

    Returns (status_code, json_body_or_none, error_message).
    """
    sess = session or requests.Session()
    m = method.upper()
    r1 = _x402_http_call(sess, m, endpoint_url, params=params, json_body=payload, headers=None, timeout=timeout)

    def _json_body(r: requests.Response) -> dict[str, Any] | None:
        ct = r.headers.get("content-type") or ""
        if "application/json" not in ct:
            return {"raw": r.text[:2000]} if r.text else None
        try:
            out = r.json()
            return out if isinstance(out, dict) else {"value": out}
        except Exception:
            return {"raw": r.text[:2000]}

    if r1.status_code != 402:
        err = None if r1.status_code == 200 else f"http_{r1.status_code}"
        return r1.status_code, _json_body(r1), err

    pr = parse_payment_challenge(r1)
    if not pr:
        return 402, _json_body(r1), "unparseable_402"

    challenge = PaymentChallenge(
        raw_status=402,
        body=_json_body(r1),
        headers={k: v for k, v in r1.headers.items()},
        accepted=_extract_accepted(pr),
    )

    if pay_invoice is None:
        return (
            402,
            {
                "payment_challenge": pr,
                "hint": "Provide pay_invoice=mock_pay_invoice or wire T54XrplAdapter for real settlement",
            },
            "payment_required_no_pay_fn",
        )

    proof_headers = pay_invoice(pr)
    if m == "GET":
        r2 = _x402_http_call(
            sess, m, endpoint_url, params=params, json_body=None, headers=proof_headers, timeout=timeout
        )
        for _ in range(6):
            if r2.status_code == 200:
                break
            if r2.status_code not in (400, 408, 429, 502, 503):
                break
            time.sleep(2.5)
            r2 = _x402_http_call(
                sess, m, endpoint_url, params=params, json_body=None, headers=proof_headers, timeout=timeout
            )
    else:
        r2 = _x402_http_call(
            sess,
            m,
            endpoint_url,
            params=params,
            json_body=payload,
            headers=proof_headers,
            timeout=timeout,
        )
        for _ in range(6):
            if r2.status_code == 200:
                break
            if r2.status_code not in (400, 408, 429, 502, 503):
                break
            time.sleep(2.5)
            r2 = _x402_http_call(
                sess,
                m,
                endpoint_url,
                params=params,
                json_body=payload,
                headers=proof_headers,
                timeout=timeout,
            )

    err2 = None if r2.status_code == 200 else f"after_payment_http_{r2.status_code}"
    return r2.status_code, _json_body(r2), err2


def default_base_url() -> str:
    return (os.getenv("T54_SELLER_PUBLIC_BASE_URL") or "http://127.0.0.1:8765").rstrip("/")
