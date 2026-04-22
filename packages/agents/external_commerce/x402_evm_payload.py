"""
EVM x402: parse 402 responses where V2 terms live in JSON (not only PAYMENT-REQUIRED header),
build PAYMENT-SIGNATURE via x402ClientSync + Exact EVM. Surfaces underlying web3/x402 errors.
"""
from __future__ import annotations

import logging
import os
import sys
import traceback
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE_MAINNET_CAIP2 = "eip155:8453"


def base_mainnet_allowed_networks() -> list[str]:
    """
    Base mainnet only for x402 EVM signing. Drops eip155:84532 (Sepolia) from X402_ALLOWED_NETWORKS.
    """
    raw = (os.getenv("X402_ALLOWED_NETWORKS") or "").strip()
    if not raw:
        return [BASE_MAINNET_CAIP2]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    out = [p for p in parts if p == BASE_MAINNET_CAIP2]
    return out if out else [BASE_MAINNET_CAIP2]


def settlement_failure_operator_hint() -> str:
    return (
        "If the server returns Settlement/settle errors after PAYMENT-SIGNATURE: "
        "(1) Set X402_ALLOWED_NETWORKS=eip155:8453 first (Base mainnet USDC) to match a funded mainnet wallet. "
        "(2) Ensure enough USDC on Base (and ETH for gas if not gasless). "
        "(3) Transient facilitator errors: a second attempt runs when X402_EVM_PAYMENT_ATTEMPTS>1."
    )


BASE_MAINNET_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def log_evm_402_diagnostics(body: dict[str, Any] | None, *, context: str = "") -> None:
    """Print server error + operator hint + client prep errors to stderr and logger (EVM 402 debugging)."""
    if not isinstance(body, dict):
        return
    server_err = body.get("error")
    hint = body.get("x402_settlement_hint")
    evm_err = body.get("x402_evm_error")
    if not (server_err or hint or evm_err):
        return
    prefix = f"[x402 EVM]{(' ' + context) if context else ''}"
    if server_err:
        logger.warning("%s server error field: %s", prefix, server_err)
        print(f"{prefix}\n  server error: {server_err}", file=sys.stderr, flush=True)
    if hint:
        logger.warning("%s operator hint (x402_settlement_hint): %s", prefix, hint)
        print(f"{prefix}\n  x402_settlement_hint: {hint}", file=sys.stderr, flush=True)
    if evm_err:
        logger.warning("%s client prep error (truncated): %s", prefix, str(evm_err)[:2500])
        print(f"{prefix}\n  x402_evm_error:\n{evm_err}", file=sys.stderr, flush=True)


def _validate_base_mainnet_usdc_accepts(pr: Any) -> None:
    """Require at least one accept for Base mainnet + native USDC contract (EIP-3009 exact)."""
    try:
        from x402.schemas import PaymentRequired
    except ImportError:
        return
    if not isinstance(pr, PaymentRequired):
        return
    acc = getattr(pr, "accepts", None) or []
    if not acc:
        raise RuntimeError("No valid Base USDC payment option found in accepts array (empty accepts)")
    want = BASE_MAINNET_USDC.lower()
    for r in acc:
        net = str(getattr(r, "network", ""))
        asset = str(getattr(r, "asset", "")).lower()
        if net == BASE_MAINNET_CAIP2 and (asset == want or want in asset):
            return
    nets = [str(getattr(r, "network", "")) for r in acc]
    assets = [str(getattr(r, "asset", "")) for r in acc]
    raise RuntimeError(
        "No valid Base USDC payment option found in accepts array "
        f"(networks={nets}, assets={assets})"
    )


def _enforce_max_usdc_spend_atomic(pr: Any) -> None:
    """Optional cap: MAX_USDC_SPEND_PER_TX (decimal USDC) or MAX_USDC_SPEND_PER_TX_ATOMIC (6-decimal units)."""
    try:
        from x402.schemas import PaymentRequired
    except ImportError:
        return
    if not isinstance(pr, PaymentRequired):
        return
    cap_atomic_raw = (os.getenv("MAX_USDC_SPEND_PER_TX_ATOMIC") or "").strip()
    cap_usdc_raw = (os.getenv("MAX_USDC_SPEND_PER_TX") or "").strip()
    if not cap_atomic_raw and not cap_usdc_raw:
        return
    if cap_atomic_raw:
        cap = int(cap_atomic_raw)
    else:
        cap = int(float(cap_usdc_raw) * 1e6)
    want = BASE_MAINNET_USDC.lower()
    for r in pr.accepts:
        net = str(getattr(r, "network", ""))
        asset = str(getattr(r, "asset", "")).lower()
        if net != BASE_MAINNET_CAIP2 or want not in asset:
            continue
        amt = int(str(getattr(r, "amount", "0")))
        if amt > cap:
            raise RuntimeError(
                "Amount exceeds max spend cap: "
                f"required_atomic={amt} cap_atomic={cap} "
                "(set MAX_USDC_SPEND_PER_TX or MAX_USDC_SPEND_PER_TX_ATOMIC)"
            )


def normalize_v2_challenge_dict(body: dict[str, Any]) -> dict[str, Any]:
    """Map common API variants (e.g. maxAmountRequired) onto x402 V2 schema fields."""
    out = dict(body)
    acc = out.get("accepts")
    if not isinstance(acc, list):
        return out
    fixed: list[dict[str, Any]] = []
    for item in acc:
        if not isinstance(item, dict):
            continue
        i = dict(item)
        if "amount" not in i:
            m = i.get("maxAmountRequired") if "maxAmountRequired" in i else i.get("max_amount_required")
            if m is not None:
                i["amount"] = str(m)
        fixed.append(i)
    out["accepts"] = fixed
    return out


def parse_payment_required_from_402_response(
    resp: requests.Response,
) -> Any | None:
    """
    Build PaymentRequired / PaymentRequiredV1 from a 402 response (header or JSON body).
    Supports V2 bodies with x402Version + accepts (fixes upstream client gap for body-only V2).
    """
    try:
        from x402.http.utils import decode_payment_required_header
    except ImportError:
        decode_payment_required_header = None  # type: ignore[assignment]

    if decode_payment_required_header:
        for key in ("PAYMENT-REQUIRED", "Payment-Required", "payment-required"):
            h = resp.headers.get(key)
            if h:
                try:
                    return decode_payment_required_header(h)
                except Exception:
                    pass

    try:
        from x402.schemas.helpers import parse_payment_required
    except ImportError:
        return None

    try:
        body = resp.json()
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    body = normalize_v2_challenge_dict(body)
    try:
        return parse_payment_required(body)
    except Exception as e:
        logger.debug("parse_payment_required failed: %s", e)
        return None


def build_payment_signature_headers(
    payment_required: Any,
    *,
    private_key: str,
) -> tuple[dict[str, str], str | None]:
    """
    Create PAYMENT-SIGNATURE (and related) headers. Returns (headers, error_string).
    On failure, error_string includes exception type, message, and traceback for debugging.
    """
    try:
        from eth_account import Account
        from x402 import x402ClientSync
        from x402.http.x402_http_client import x402HTTPClientSync
        from x402.mechanisms.evm import EthAccountSigner
        from x402.mechanisms.evm.exact.register import register_exact_evm_client
    except ImportError as e:
        return {}, f"ImportError: {e}"

    if not private_key or "0x" not in private_key:
        return {}, "missing_or_invalid_private_key"

    try:
        _validate_base_mainnet_usdc_accepts(payment_required)
        _enforce_max_usdc_spend_atomic(payment_required)
        account = Account.from_key(private_key)
        client = x402ClientSync()
        from x402.client_base import prefer_network

        nets = base_mainnet_allowed_networks()
        policies = [prefer_network(nets[0])]
        register_exact_evm_client(client, EthAccountSigner(account), policies=policies)
        http = x402HTTPClientSync(client)
        payload = client.create_payment_payload(payment_required)
        return http.encode_payment_signature_header(payload), None
    except RuntimeError as e:
        msg = str(e)
        logger.warning("x402 EVM payment blocked: %s", msg)
        print(f"[x402 EVM] payment blocked: {msg}", file=sys.stderr, flush=True)
        return {}, msg
    except Exception as e:
        tb = traceback.format_exc()
        err = f"{type(e).__name__}: {e}\n{tb}"
        logger.exception("x402 EVM payment payload build failed")
        print(f"[x402 EVM] payment build failed:\n{err}", file=sys.stderr, flush=True)
        return {}, err


def _evm_private_key_from_env() -> str:
    for k in (
        "AGENT_EVM_PRIVATE_KEY",
        "X402_BUYER_BASE_MAINNET_PRIVATE_KEY",
        "X402_BUYER_PRIVATE_KEY",
        "ROOT_STRATEGIST_PRIVATE_KEY",
    ):
        v = (os.getenv(k, "") or "").strip()
        if v and "0x" in v:
            return v
    return ""


def evm_exact_pay_invoice(challenge: dict[str, Any]) -> dict[str, str]:
    """
    Broker hook: 402 challenge dict (headers + body shape) -> PAYMENT-SIGNATURE for EVM exact (e.g. Base USDC).
    Uses the same parsing as X402Buyer (V2 JSON body + optional header).
    """
    try:
        from x402.schemas.helpers import parse_payment_required
    except ImportError as e:
        raise RuntimeError(f"x402 SDK not available: {e}") from e

    body = normalize_v2_challenge_dict(dict(challenge))
    pr = parse_payment_required(body)
    pk = _evm_private_key_from_env()
    headers, err = build_payment_signature_headers(pr, private_key=pk)
    if err:
        raise RuntimeError(err)
    return headers
