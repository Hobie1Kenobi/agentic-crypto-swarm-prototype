"""
T54 XRPL x402 adapter — parse 402, build presigned payment, resubmit.
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

import requests

from .config import get_t54_xrpl_config, t54_testnet_blocked_reason
from .payment_builder import build_presigned_xrpl_payment
from .reconciliation import T54ReconciliationRecord, T54ReconciliationStore


def _ts() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _parse_payment_required(response: requests.Response) -> dict[str, Any] | None:
    pr = response.headers.get("PAYMENT-REQUIRED") or response.headers.get("X-Payment-Required")
    if pr:
        try:
            raw = base64.b64decode(pr)
            return json.loads(raw) if isinstance(raw, bytes) else json.loads(raw.decode("utf-8"))
        except Exception:
            pass
    try:
        body = response.json() if response.content else {}
        if isinstance(body, dict):
            return body.get("payment") or body.get("accepts") or body
    except Exception:
        pass
    return None


def _extract_accepted(pr: dict[str, Any]) -> dict[str, Any] | None:
    accepts = pr.get("accepts")
    if isinstance(accepts, list) and accepts:
        for a in accepts:
            if isinstance(a, dict) and (a.get("scheme") == "exact" or "xrpl" in str(a.get("network", "")).lower()):
                return a
    return pr.get("accepted") or pr


def _build_payment_signature_payload(
    signed_blob_hex: str,
    accepted: dict[str, Any],
    network: str,
    invoice_id: str,
) -> dict[str, Any]:
    return {
        "x402Version": 2,
        "accepted": {
            "scheme": accepted.get("scheme", "exact"),
            "network": network,
            "asset": accepted.get("asset", "XRP"),
            "payTo": accepted.get("payTo", accepted.get("pay_to", "")),
            "amount": accepted.get("amount", ""),
            "maxTimeoutSeconds": accepted.get("maxTimeoutSeconds", 600),
            "extra": {
                "sourceTag": accepted.get("extra", {}).get("sourceTag", 804681468) if isinstance(accepted.get("extra"), dict) else 804681468,
                "invoiceId": invoice_id,
            },
        },
        "payload": {"signedTxBlob": signed_blob_hex},
    }


class T54XrplAdapter:
    def __init__(self, config=None):
        self._config = config or get_t54_xrpl_config()
        self._store = T54ReconciliationStore()
        self._session = requests.Session()

    def invoke(
        self,
        resource_url: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> tuple[int, dict[str, Any] | None, str | None, T54ReconciliationRecord]:
        cfg = self._config
        rec = T54ReconciliationRecord(
            mode=cfg.mode,
            facilitator_url=cfg.facilitator_url,
            network=cfg.network,
            wallet_address=cfg.wallet_address or "(from_seed)",
        )
        if not cfg.enabled:
            rec.verification_status = "testnet_facilitator_unavailable"
            rec.reason = "T54_XRPL_ENABLED=false"
            rec.validated = False
            self._store.append(rec)
            return 0, None, "t54_disabled", rec
        blocked = t54_testnet_blocked_reason(cfg)
        if blocked:
            rec.verification_status = "testnet_facilitator_unavailable"
            rec.reason = blocked
            rec.validated = False
            rec.facilitator_response = "absent"
            self._store.append(rec)
            return 0, None, blocked, rec
        if cfg.dry_run:
            r = self._session.get(resource_url, params=params or {}, timeout=timeout or 30) if method.upper() == "GET" else self._session.post(resource_url, json=json_body or {}, timeout=timeout or 30)
            rec.verification_status = "local_dev_only"
            rec.reason = "T54_XRPL_DRY_RUN=true"
            rec.validated = False
            rec.facilitator_response = "dry_run_skip"
            self._store.append(rec)
            data = r.json() if "application/json" in (r.headers.get("content-type") or "") else {"raw": r.text[:500]}
            return r.status_code, data, None, rec
        if not cfg.wallet_seed or "sEd" not in cfg.wallet_seed:
            rec.verification_status = "payment_failed_pre_submit"
            rec.reason = "T54_XRPL_WALLET_SEED not set or invalid"
            rec.validated = False
            self._store.append(rec)
            return 402, None, "no_xrpl_wallet_seed", rec
        timeout_sec = (timeout or cfg.timeout_ms / 1000)
        start = time.time()
        try:
            if method.upper() == "GET":
                r = self._session.get(resource_url, params=params or {}, timeout=timeout_sec)
            else:
                r = self._session.post(resource_url, json=json_body or {}, timeout=timeout_sec)
            if r.status_code != 402:
                data = r.json() if "application/json" in (r.headers.get("content-type") or "") else {"raw": r.text[:500]}
                rec.submit_status = "no_payment_required"
                rec.verification_status = "real_t54_xrpl_payment" if r.status_code == 200 else "payment_failed_pre_submit"
                rec.completed_at = _ts()
                self._store.append(rec)
                return r.status_code, data, None, rec
            pr = _parse_payment_required(r)
            if not pr:
                rec.verification_status = "payment_failed_pre_submit"
                rec.reason = "no_payment_required_in_402"
                rec.validated = False
                self._store.append(rec)
                return 402, None, "unparseable_402", rec
            accepted = _extract_accepted(pr)
            if not accepted:
                rec.verification_status = "payment_failed_pre_submit"
                rec.reason = "no_accepted_terms"
                rec.validated = False
                self._store.append(rec)
                return 402, None, "no_accepted_terms", rec
            network_id = accepted.get("network", "xrpl:1")
            if "xrpl:" not in str(network_id):
                rec.verification_status = "payment_failed_pre_submit"
                rec.reason = f"unsupported_network:{network_id}"
                rec.validated = False
                self._store.append(rec)
                return 402, None, f"unsupported_network:{network_id}", rec
            net = "mainnet" if network_id == "xrpl:0" else "testnet"
            if net == "testnet" and blocked:
                rec.verification_status = "testnet_facilitator_unavailable"
                rec.reason = blocked
                rec.validated = False
                self._store.append(rec)
                return 402, None, blocked, rec
            pay_to = accepted.get("payTo") or accepted.get("pay_to", "")
            amount = str(accepted.get("amount", "1000000"))
            extra = accepted.get("extra") or {}
            if isinstance(extra, dict):
                invoice_id = extra.get("invoiceId") or extra.get("invoice_id") or f"inv-{int(time.time())}"
                source_tag = int(extra.get("sourceTag", extra.get("source_tag", 804681468)))
                dest_tag = extra.get("destinationTag") or extra.get("destination_tag")
            else:
                invoice_id = f"inv-{int(time.time())}"
                source_tag = 804681468
                dest_tag = None
            rec.invoice_id = invoice_id
            rec.receiver_address = pay_to
            rec.amount_drops = amount
            rec.destination_tag = int(dest_tag) if dest_tag is not None else None
            blob, err = build_presigned_xrpl_payment(
                wallet_seed=cfg.wallet_seed,
                pay_to=pay_to,
                amount_drops=amount,
                invoice_id=invoice_id,
                source_tag=source_tag,
                destination_tag=rec.destination_tag,
                network=net,
            )
            if err:
                rec.verification_status = "payment_failed_pre_submit"
                rec.reason = err
                rec.error_message = err
                rec.validated = False
                rec.signed_blob_present = False
                self._store.append(rec)
                return 402, None, err, rec
            rec.signed_blob_present = True
            payload = _build_payment_signature_payload(blob, accepted, network_id, invoice_id)
            payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
            headers = {"PAYMENT-SIGNATURE": payload_b64}
            if method.upper() == "GET":
                r2 = self._session.get(resource_url, params=params or {}, headers=headers, timeout=timeout_sec)
            else:
                r2 = self._session.post(resource_url, json=json_body or {}, headers=headers, timeout=timeout_sec)
            data = r2.json() if "application/json" in (r2.headers.get("content-type") or "") else {"raw": r2.text[:500]}
            pay_resp = r2.headers.get("PAYMENT-RESPONSE")
            if pay_resp:
                try:
                    dec = base64.b64decode(pay_resp)
                    pr_dec = json.loads(dec) if isinstance(dec, bytes) else json.loads(dec.decode("utf-8"))
                    rec.facilitator_response = json.dumps(pr_dec)[:500]
                    if pr_dec.get("success"):
                        rec.xrpl_tx_hash = pr_dec.get("transaction")
                        rec.verification_status = "real_t54_xrpl_payment"
                        rec.validated = True
                        rec.verify_status = "ok"
                        rec.settle_status = "ok"
                    else:
                        rec.verification_status = "facilitator_settle_failed"
                        rec.reason = pr_dec.get("error", "settle_failed")
                        rec.validated = False
                except Exception:
                    rec.facilitator_response = pay_resp[:200]
            else:
                if r2.status_code == 200:
                    rec.verification_status = "real_t54_xrpl_payment"
                    rec.validated = True
                else:
                    rec.verification_status = "facilitator_settle_failed"
                    rec.reason = f"http_{r2.status_code}"
                    rec.validated = False
            rec.completed_at = _ts()
            self._store.append(rec)
            return r2.status_code, data, None if r2.status_code == 200 else str(r2.status_code), rec
        except requests.RequestException as e:
            rec.verification_status = "payment_failed_pre_submit"
            rec.error_message = str(e)
            rec.reason = "request_failed"
            rec.validated = False
            self._store.append(rec)
            return 0, None, str(e), rec
        except Exception as e:
            rec.verification_status = "payment_failed_pre_submit"
            rec.error_message = str(e)
            rec.reason = "unknown_error"
            rec.validated = False
            self._store.append(rec)
            return 0, None, str(e), rec
