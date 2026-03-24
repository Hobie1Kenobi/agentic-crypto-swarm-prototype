"""
Unified invoker — route by provider payment_flow to correct buyer (Celo / facilitator / t54).
Supports Celo-native: when X402_USE_FACILITATOR=1 and provider has celo_native, use Celo network.
"""
from __future__ import annotations

import os
from typing import Any

from .schemas import ExternalProvider
from .celo_native_buyer import invoke_celo_native_402
from .t54_xrpl_buyer import invoke_t54_xrpl_402
from .x402_buyer import X402Buyer


def _use_celo_facilitator(provider: ExternalProvider) -> bool:
    use = (os.getenv("X402_USE_FACILITATOR", "1") or "").strip().lower() in {"1", "true", "yes"}
    meta = provider.metadata or {}
    return use and meta.get("celo_native") is True


def invoke_by_provider(
    provider: ExternalProvider,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    method: str = "GET",
    timeout: float = 60,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """
    Invoke provider resource. Routes to celo_native, facilitator (Base), or t54_xrpl by payment_flow.
    Returns (status_code, response_json, error).
    """
    url = (provider.resource_url or "").strip()
    if not url:
        return 0, None, "provider_missing_resource_url"
    if not (url.startswith("http://") or url.startswith("https://")):
        return 0, None, f"invalid_resource_url:{url[:50]}"

    meta = provider.metadata or {}
    flow = meta.get("payment_flow")
    flow = str(flow or "").strip().lower()

    if flow == "celo_native":
        return invoke_celo_native_402(url, params=params, json_body=json_body, method=method, timeout=timeout)
    if flow == "t54_xrpl":
        return invoke_t54_xrpl_402(url, params=params, json_body=json_body, method=method, timeout=timeout)
    if flow in ("facilitator", "none", ""):
        if flow == "none":
            import requests
            try:
                r = requests.get(url, params=params or {}, timeout=timeout) if method.upper() == "GET" else requests.post(url, json=json_body or {}, timeout=timeout)
                data = r.json() if "application/json" in (r.headers.get("content-type") or "") else {"raw": r.text[:500]}
                return r.status_code, data, None
            except Exception as e:
                return 0, None, str(e)
        fac = provider.facilitator_url or "https://x402.org/facilitator"
        net = provider.network or "eip155:84532"
        if _use_celo_facilitator(provider):
            celo_fac = os.getenv("X402_FACILITATOR_MAINNET", "https://facilitator.ultravioletadao.xyz")
            celo_net = "eip155:42220"
            if "84532" in (net or ""):
                celo_fac = os.getenv("X402_FACILITATOR_TESTNET", "https://x402.org/facilitator")
                celo_net = "eip155:11142220"
            fac, net = celo_fac, celo_net
        buyer = X402Buyer(facilitator_url=fac, network=net)
        return buyer.invoke(url, method=method, params=params, json_body=json_body, timeout=timeout)
    return invoke_celo_native_402(url, params=params, json_body=json_body, method=method, timeout=timeout)
