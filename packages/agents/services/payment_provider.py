from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaymentQuote:
    amount: str | int
    asset: str
    receiver: str
    chain_or_ledger: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PaymentReceipt:
    payment_rail: str
    payment_asset: str
    external_payment_id: str | None
    tx_hash: str | None
    payer_address: str | None
    receiver_address: str | None
    amount: str | int
    verified: bool
    verification_boundary: str
    internal_task_id: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PaymentRequest:
    task_request: dict[str, Any]
    quote: PaymentQuote
    payment_id: str


class PaymentProvider(ABC):
    @abstractmethod
    def quote_payment(self, task_request: dict[str, Any]) -> PaymentQuote | None:
        pass

    @abstractmethod
    def request_payment(self, task_request: dict[str, Any], quote: PaymentQuote) -> PaymentRequest | None:
        pass

    @abstractmethod
    def verify_payment_receipt(self, receipt_data: dict[str, Any]) -> PaymentReceipt | None:
        pass

    @abstractmethod
    def normalize_payment_result(self, raw: Any) -> PaymentReceipt | None:
        pass
