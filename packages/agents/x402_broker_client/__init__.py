from .client import (
    PaymentChallenge,
    execute_x402_request,
    get_pay_invoice_fn,
    mock_pay_invoice,
    parse_payment_challenge,
    xrpl_mainnet_pay_invoice,
    xrpl_testnet_pay_invoice,
)

__all__ = [
    "PaymentChallenge",
    "execute_x402_request",
    "get_pay_invoice_fn",
    "mock_pay_invoice",
    "parse_payment_challenge",
    "xumm_mainnet_pay_invoice",
    "xrpl_mainnet_pay_invoice",
    "xrpl_testnet_pay_invoice",
]


def __getattr__(name: str):
    if name == "xumm_mainnet_pay_invoice":
        from integrations.t54_xrpl.xumm_payment_builder import xumm_mainnet_pay_invoice

        return xumm_mainnet_pay_invoice
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
