#!/usr/bin/env python3
"""
MCP server: T54 / x402 SKUs from OpenAPI, brokered via x402_broker_client (XRPL/USDC invoice → PAYMENT-SIGNATURE → data).

Run (stdio, for Cursor / Claude Desktop / OpenClaw):
  pip install "mcp[cli]" pyyaml
  python scripts/mcp_server.py

Remote SSE (Agent.ai, hosted clients) — bind localhost, put Caddy/ngrok in front:
  python scripts/mcp_server.py --transport sse --host 127.0.0.1 --port 9051
  Paths: GET /sse (stream), POST /messages/ (MCP). Public URL with unified proxy: https://<origin>/mcp/sse

Streamable HTTP (Smithery, Glama URL publish) — requires mcp>=1.23; separate port behind Caddy:
  python scripts/mcp_server.py --transport streamable-http --host 127.0.0.1 --port 9052
  Public URL: https://<origin>/mcp (Caddy routes exact /mcp → 9052; /mcp/sse → 9051 SSE).

Validate without starting stdio (CI / preflight):
  python scripts/mcp_server.py --check

Cursor: project MCP is wired in .cursor/mcp.json (stdio → this file). Reload the window or restart
Cursor after changing MCP config. If ${workspaceFolder} is not expanded, set cwd + args to absolute paths.

Env (see .env.example):
  T54_SELLER_PUBLIC_BASE_URL — public seller origin (no trailing slash)
  X402_BROKER_PAY_MODE — mock | xrpl_testnet | xrpl_mainnet | xumm | base_usdc (see x402_broker_client)
  XRPL seeds / caps for real XRPL payment
  X402_MCP_DRY_RUN=1 — use mock_pay_invoice (no real settlement)

OpenAPI catalog:
  documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml
  Override: X402_MCP_OPENAPI_PATH
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.transport_security import TransportSecuritySettings

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=False)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)

DEFAULT_OPENAPI_REL = "documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml"


def _default_openapi_path() -> Path:
    p = (os.getenv("X402_MCP_OPENAPI_PATH") or "").strip()
    if p:
        return Path(p) if Path(p).is_absolute() else root / p
    return root / DEFAULT_OPENAPI_REL


def _load_openapi() -> dict[str, Any]:
    import yaml

    path = _default_openapi_path()
    if not path.is_file():
        raise FileNotFoundError(f"OpenAPI file not found: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _operations_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    paths = spec.get("paths") or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(op, dict):
                continue
            oid = op.get("operationId")
            if not oid:
                continue
            params: list[dict[str, Any]] = []
            for p in op.get("parameters") or []:
                if not isinstance(p, dict):
                    continue
                if p.get("in") != "query":
                    continue
                name = p.get("name")
                if not name:
                    continue
                params.append(
                    {
                        "name": name,
                        "required": bool(p.get("required")),
                        "schema": p.get("schema") or {},
                    }
                )
            out.append(
                {
                    "operationId": oid,
                    "path": path,
                    "method": method.upper(),
                    "summary": (op.get("summary") or "").strip(),
                    "description": (op.get("description") or "").strip(),
                    "parameters": params,
                }
            )
    return out


def _join_url(base: str, path: str) -> str:
    b = base.rstrip("/")
    p = path if path.startswith("/") else "/" + path
    return b + p


def _pay_fn():
    from x402_broker_client.client import get_pay_invoice_fn, mock_pay_invoice

    if (os.getenv("X402_MCP_DRY_RUN") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return mock_pay_invoice
    return get_pay_invoice_fn()


def _build_registry(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    reg: dict[str, dict[str, Any]] = {}
    for op in _operations_from_spec(spec):
        reg[op["operationId"]] = op
    return reg


async def _run_t54_operation(
    registry: dict[str, dict[str, Any]],
    operation_id: str,
    query: dict[str, Any] | None,
    context: Any,
) -> str:
    from x402_broker_client.client import default_base_url, execute_x402_request

    op = registry.get(operation_id.strip())
    if not op:
        known = ", ".join(sorted(registry.keys()))
        raise ValueError(f"Unknown operation_id={operation_id!r}. Known: {known}")

    base = default_base_url()
    url = _join_url(base, op["path"])
    method = op["method"]
    allowed = {p["name"] for p in op["parameters"]}
    qraw = query or {}
    params: dict[str, str] = {}
    for k, v in qraw.items():
        if k not in allowed:
            continue
        if v is None:
            continue
        params[str(k)] = str(v)

    if context:
        await context.info(f"t54 {operation_id} {method} {url} params={params}")

    pay = _pay_fn()
    status, body, err = execute_x402_request(
        url,
        payload=None,
        method=method,
        params=params if method == "GET" else None,
        timeout=float((os.getenv("X402_MCP_TIMEOUT_SEC") or "120").strip() or "120"),
        pay_invoice=pay,
    )
    return json.dumps(
        {"status": status, "body": body, "error": err, "url": url, "operation_id": operation_id},
        indent=2,
        default=str,
    )


def check_mcp_stack() -> int:
    """Load OpenAPI, registry, and imports; print JSON summary. Exits 0 on success."""
    try:
        import importlib

        importlib.import_module("mcp.server.fastmcp")

        spec = _load_openapi()
        registry = _build_registry(spec)
        from x402_broker_client.client import default_base_url, get_pay_invoice_fn

        base = default_base_url()
        pay_mode = (os.getenv("X402_BROKER_PAY_MODE") or os.getenv("X402_PAY_MODE") or "mock").strip()
        if not callable(get_pay_invoice_fn()):
            raise RuntimeError("get_pay_invoice_fn() did not return a callable")
        out = {
            "ok": True,
            "openapi_path": str(_default_openapi_path().resolve()),
            "operation_count": len(registry),
            "operation_ids": sorted(registry.keys()),
            "tool_count_estimate": 2 + len(registry),
            "t54_seller_base_url": base,
            "x402_broker_pay_mode": pay_mode,
            "mcp_package": "mcp",
        }
        print(json.dumps(out, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


def _mcp_transport_security() -> TransportSecuritySettings | None:
    """Behind Cloudflare+Caddy, Host is the public API hostname, not 127.0.0.1."""
    raw = (os.getenv("MCP_HTTP_DNS_REBINDING") or "").strip().lower()
    if raw in {"0", "false", "off", "no"}:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    hosts = (os.getenv("MCP_HTTP_ALLOWED_HOSTS") or "").strip()
    if not hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    allowed = []
    for h in hosts.split(","):
        h = h.strip()
        if not h:
            continue
        allowed.append(h if ":" in h else f"{h}:*")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed,
        allowed_origins=[],
    )


def _build_fastmcp(**settings: Any):
    from mcp.server.fastmcp import FastMCP

    spec = _load_openapi()
    registry = _build_registry(spec)
    openapi_path = _default_openapi_path()
    openapi_text = openapi_path.read_text(encoding="utf-8")

    mcp = FastMCP(
        "Swarm T54 x402",
        instructions=(
            "Tools call the Agentic Swarm T54 seller HTTP API. Paid routes return HTTP 402 until "
            "x402_broker_client pays the XRPL (or configured rail) invoice and retries. "
            "Use t54_list_operations before invoking. Set T54_SELLER_PUBLIC_BASE_URL and broker env."
        ),
        **settings,
    )

    @mcp.resource("openapi://agentic-swarm-t54-skus")
    def openapi_yaml() -> str:
        """Raw OpenAPI 3 YAML for T54 SKUs."""
        return openapi_text

    @mcp.tool()
    async def t54_list_operations() -> str:
        """List T54 seller operationIds, paths, and query parameters from the loaded OpenAPI spec (no HTTP)."""
        rows = []
        for op in _operations_from_spec(spec):
            rows.append(
                {
                    "operationId": op["operationId"],
                    "method": op["method"],
                    "path": op["path"],
                    "summary": op["summary"],
                    "query_parameters": [p["name"] for p in op["parameters"]],
                }
            )
        return json.dumps(
            {
                "openapi_path": str(openapi_path.resolve()),
                "base_url_env": "T54_SELLER_PUBLIC_BASE_URL",
                "operations": rows,
            },
            indent=2,
        )

    @mcp.tool()
    async def t54_x402_request(
        operation_id: str,
        query: dict[str, Any] | None = None,
        context: Context | None = None,
    ) -> str:
        """Execute one T54 HTTP operation by operationId. On 402, pays via x402_broker_client then retries."""
        return await _run_t54_operation(registry, operation_id, query, context)

    def _make_per_op_tool(oid: str):
        async def _per_op_tool(
            query: dict[str, Any] | None = None,
            context: Context | None = None,
        ) -> str:
            return await _run_t54_operation(registry, oid, query, context)

        return _per_op_tool

    for _oid, _meta in sorted(registry.items()):
        _summary = (_meta.get("summary") or "").strip()
        _path_line = f"T54 x402 `{_oid}` → HTTP {_meta['method']} `{_meta['path']}` (brokered)."
        _fn = _make_per_op_tool(_oid)
        _fn.__doc__ = (_summary + "\n\n" if _summary else "") + _path_line
        mcp.add_tool(_fn, name=f"t54_{_oid}")

    return mcp


def run_stdio_server() -> None:
    mcp = _build_fastmcp()
    mcp.run(transport="stdio")


def run_sse_server(host: str, port: int) -> None:
    mcp = _build_fastmcp(host=host, port=port)
    mcp.run(transport="sse")


def run_streamable_http_server(host: str, port: int) -> None:
    mcp = _build_fastmcp(
        host=host,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=_mcp_transport_security(),
    )
    mcp.run(transport="streamable-http")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="MCP server for T54 x402: stdio (default), SSE (remote), or streamable-http (Smithery)"
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Validate OpenAPI, registry, and imports; do not start a server",
    )
    ap.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="stdio for Cursor/Claude; sse for Agent.ai; streamable-http for Smithery/Glama URL (mcp>=1.23)",
    )
    ap.add_argument(
        "--host",
        default=(os.getenv("X402_MCP_SSE_HOST") or "127.0.0.1").strip(),
        help="Bind address for SSE (default 127.0.0.1; env X402_MCP_SSE_HOST)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP port (SSE default 9051 via X402_MCP_SSE_PORT; streamable-http default 9052 via X402_MCP_STREAMABLE_PORT)",
    )
    args = ap.parse_args()
    if args.check:
        raise SystemExit(check_mcp_stack())
    port = args.port
    if port is None:
        if args.transport == "streamable-http":
            port = int((os.getenv("X402_MCP_STREAMABLE_PORT") or "9052").strip() or "9052")
        else:
            port = int((os.getenv("X402_MCP_SSE_PORT") or "9051").strip() or "9051")
    if args.transport == "stdio":
        run_stdio_server()
    elif args.transport == "sse":
        run_sse_server(host=args.host, port=port)
    else:
        run_streamable_http_server(host=args.host, port=port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
