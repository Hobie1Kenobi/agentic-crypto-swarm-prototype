"""
T54 XRPL x402 buyer — invoke x402 resources that require t54-mediated XRPL payment.
"""
from __future__ import annotations

from typing import Any

from integrations.t54_xrpl import T54XrplAdapter
from integrations.t54_xrpl.config import get_t54_xrpl_config


def invoke_t54_xrpl_402(
    resource_url: str,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    method: str = "GET",
    timeout: float = 60,
) -> tuple[int, dict[str, Any] | None, str | None]:
    """
    Call t54 XRPL x402 resource. Returns (status_code, response_json, error).
    """
    cfg = get_t54_xrpl_config()
    adapter = T54XrplAdapter(config=cfg)
    status, data, err, _rec = adapter.invoke(
        resource_url=resource_url,
        method=method,
        params=params,
        json_body=json_body,
        timeout=timeout,
    )
    return status, data, err
