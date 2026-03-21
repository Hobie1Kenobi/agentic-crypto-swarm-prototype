from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from services.payment_provider import PaymentProvider, PaymentQuote, PaymentReceipt, PaymentRequest


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _xrpl_enabled() -> bool:
    return (_env("XRPL_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}


def _payment_mode() -> str:
    return (_env("XRPL_PAYMENT_MODE", "mock") or "mock").strip().lower()


def _settlement_asset() -> str:
    return (_env("XRPL_SETTLEMENT_ASSET", "XRP") or "XRP").strip().upper()


def _receiver_address() -> str:
    return _env("XRPL_RECEIVER_ADDRESS", "")


def _xrpl_rpc_url() -> str:
    return _env("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234")


_XRPL_LIVE_AVAILABLE: bool | None = None
_XRPL_LIVE_BLOCKER: str | None = None


def _check_xrpl_live() -> tuple[bool, str | None]:
    global _XRPL_LIVE_AVAILABLE, _XRPL_LIVE_BLOCKER
    if _XRPL_LIVE_AVAILABLE is not None:
        return _XRPL_LIVE_AVAILABLE, _XRPL_LIVE_BLOCKER
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.models.requests import ServerInfo

        client = JsonRpcClient(_xrpl_rpc_url())
        client.request(ServerInfo())
        _XRPL_LIVE_AVAILABLE = True
        _XRPL_LIVE_BLOCKER = None
    except ImportError as e:
        _XRPL_LIVE_AVAILABLE = False
        _XRPL_LIVE_BLOCKER = f"xrpl-py not installed: {e}"
    except Exception as e:
        _XRPL_LIVE_AVAILABLE = False
        _XRPL_LIVE_BLOCKER = f"XRPL RPC unreachable: {e}"
    return _XRPL_LIVE_AVAILABLE, _XRPL_LIVE_BLOCKER


class XRPLPaymentProvider(PaymentProvider):
    def quote_payment(self, task_request: dict[str, Any]) -> PaymentQuote | None:
        asset = _settlement_asset()
        receiver = _receiver_address() or "rN7n7otQDd6FczFgLdlqtyMVrn3e1DjxvV"
        try:
            from services.pricing import pricing_catalog_lookup
            catalog = pricing_catalog_lookup("task_execution", task_request)
            if catalog and asset == "RLUSD":
                amount = str(catalog.get("amount_rlusd", "1"))
            elif catalog:
                amount = str(catalog.get("amount_xrp", catalog.get("amount", "1")))
            else:
                amount = "1"
        except ImportError:
            amount = "1"
        return PaymentQuote(
            amount=amount,
            asset=asset,
            receiver=receiver,
            chain_or_ledger="xrpl",
            metadata={"task_request": task_request},
        )

    def request_payment(self, task_request: dict[str, Any], quote: PaymentQuote) -> PaymentRequest | None:
        payment_id = str(uuid.uuid4())
        return PaymentRequest(
            task_request=task_request,
            quote=quote,
            payment_id=payment_id,
        )

    def verify_payment_receipt(self, receipt_data: dict[str, Any]) -> PaymentReceipt | None:
        return self.normalize_payment_result(receipt_data)

    def normalize_payment_result(self, raw: Any) -> PaymentReceipt | None:
        if raw is None:
            return None
        if isinstance(raw, PaymentReceipt):
            return raw
        d = raw if isinstance(raw, dict) else {}
        return PaymentReceipt(
            payment_rail="xrpl",
            payment_asset=str(d.get("payment_asset", _settlement_asset())),
            external_payment_id=d.get("external_payment_id") or d.get("payment_id"),
            tx_hash=d.get("tx_hash") or d.get("xrpl_tx_hash"),
            payer_address=d.get("payer_address") or d.get("payer"),
            receiver_address=d.get("receiver_address") or d.get("receiver"),
            amount=d.get("amount", "0"),
            verified=bool(d.get("verified", False)),
            verification_boundary=str(d.get("verification_boundary", "unknown")),
            internal_task_id=d.get("internal_task_id"),
            metadata=d.get("metadata"),
        )


def create_mock_xrpl_receipt(
    task_request: dict[str, Any] | None = None,
    payment_id: str | None = None,
) -> PaymentReceipt:
    return PaymentReceipt(
        payment_rail="xrpl",
        payment_asset=_settlement_asset(),
        external_payment_id=payment_id or f"mock-{int(time.time())}",
        tx_hash=f"mock_tx_{uuid.uuid4().hex[:16]}",
        payer_address="rMockPayer123456789012345678901234",
        receiver_address=_receiver_address() or "rN7n7otQDd6FczFgLdlqtyMVrn3e1DjxvV",
        amount="1",
        verified=True,
        verification_boundary="mock_xrpl_payment",
        internal_task_id=None,
        metadata={"task_request": task_request} if task_request else None,
    )


def create_replay_xrpl_receipt(replay_payload: dict[str, Any]) -> PaymentReceipt:
    return PaymentReceipt(
        payment_rail="xrpl",
        payment_asset=str(replay_payload.get("payment_asset", _settlement_asset())),
        external_payment_id=replay_payload.get("external_payment_id") or replay_payload.get("payment_id"),
        tx_hash=replay_payload.get("tx_hash") or replay_payload.get("xrpl_tx_hash"),
        payer_address=replay_payload.get("payer_address") or replay_payload.get("payer"),
        receiver_address=replay_payload.get("receiver_address") or replay_payload.get("receiver"),
        amount=replay_payload.get("amount", "0"),
        verified=bool(replay_payload.get("verified", True)),
        verification_boundary="replayed_xrpl_payment",
        internal_task_id=replay_payload.get("internal_task_id"),
        metadata=replay_payload.get("metadata"),
    )


def attempt_live_xrpl_payment(
    amount: str,
    receiver: str,
    memo: str,
) -> tuple[PaymentReceipt | None, str | None]:
    ok, blocker = _check_xrpl_live()
    if not ok:
        return None, blocker
    seed = _env("XRPL_WALLET_SEED", "")
    if not seed or "your_" in seed or "sEd" not in seed:
        return None, "XRPL_WALLET_SEED not set or invalid"
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import Wallet
        from xrpl.models import Payment
        from xrpl.transaction import submit_and_wait

        client = JsonRpcClient(_xrpl_rpc_url())
        wallet = Wallet.from_seed(seed)
        payment = Payment(
            account=wallet.address,
            amount=amount,
            destination=receiver,
        )
        response = submit_and_wait(payment, client, wallet)
        if not response.is_successful():
            return None, f"XRPL tx failed: {response.result}"
        tx_hash = response.result.get("hash")
        return PaymentReceipt(
            payment_rail="xrpl",
            payment_asset=_settlement_asset(),
            external_payment_id=tx_hash,
            tx_hash=tx_hash,
            payer_address=wallet.address,
            receiver_address=receiver,
            amount=amount,
            verified=True,
            verification_boundary="real_xrpl_payment",
            internal_task_id=None,
            metadata={"memo": memo},
        ), None
    except ImportError as e:
        return None, f"xrpl-py not installed: {e}"
    except Exception as e:
        return None, str(e)


def get_xrpl_payment_receipt(
    mode: str,
    task_request: dict[str, Any] | None = None,
    replay_payload: dict[str, Any] | None = None,
) -> tuple[PaymentReceipt, str]:
    mode = (mode or "mock").strip().lower()
    if replay_payload and mode == "replay":
        return create_replay_xrpl_receipt(replay_payload), "replayed_xrpl_payment"
    if mode == "live" and task_request:
        quote = XRPLPaymentProvider().quote_payment(task_request or {})
        if quote:
            receipt, err = attempt_live_xrpl_payment(
                amount=str(quote.amount),
                receiver=quote.receiver,
                memo=str(task_request.get("query", task_request.get("prompt", "agent-commerce")))[:256],
            )
            if receipt:
                return receipt, "real_xrpl_payment"
            return create_mock_xrpl_receipt(task_request), f"mock_xrpl_payment (live blocked: {err})"
    return create_mock_xrpl_receipt(task_request), "mock_xrpl_payment"
