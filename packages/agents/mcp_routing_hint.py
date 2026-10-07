"""Redirect MCP paths away from the x402 seller port."""
from __future__ import annotations

from fastapi.responses import JSONResponse

_MCP_PREFIXES = ("/mcp", "/sse", "/.well-known/mcp")


def is_mcp_path(path: str) -> bool:
    p = path or ""
    return any(p == prefix or p.startswith(prefix + "/") for prefix in _MCP_PREFIXES)


def mcp_wrong_port_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "wrong_port",
            "detail": "MCP is served on port 9051/9052 (npm run mcp:t54:sse), not the x402 seller.",
        },
    )
