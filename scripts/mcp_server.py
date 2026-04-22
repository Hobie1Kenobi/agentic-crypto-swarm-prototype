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
import re
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field
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
                        "description": (p.get("description") or "").strip(),
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


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return s1.lower()


def _tool_name_for_operation(operation_id: str) -> str:
    return "t54_" + _camel_to_snake(operation_id)


def _python_param_name(openapi_name: str) -> str:
    if openapi_name == "context":
        return "context_note"
    return _camel_to_snake(openapi_name)


def _param_description(p: dict[str, Any], op: dict[str, Any]) -> str:
    d = (p.get("description") or "").strip()
    if d:
        return d
    schema = p.get("schema") or {}
    oid = op.get("operationId", "")
    extras: list[str] = []
    if schema.get("maxLength"):
        extras.append(f"max length {schema['maxLength']}")
    if schema.get("enum"):
        extras.append("allowed values: " + ", ".join(str(x) for x in schema["enum"]))
    if "default" in schema:
        extras.append(f"default: {schema['default']!r}")
    base = (
        f"Query parameter `{p['name']}` for operation `{oid}` "
        f"({op.get('method')} {op.get('path')})."
    )
    if extras:
        base += " " + "; ".join(extras) + "."
    return base


def _tool_docstring_for_registry(meta: dict[str, Any], oid: str) -> str:
    parts: list[str] = []
    if meta.get("summary"):
        parts.append(meta["summary"])
    if meta.get("description"):
        parts.append(meta["description"])
    parts.append(
        f"HTTP {meta['method']} `{meta['path']}` (`operationId` `{oid}`). "
        "Paid routes may return HTTP 402 until the x402 broker settles on the configured rail."
    )
    return "\n\n".join(parts)


def _annotations_t54_network() -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )


def _annotations_t54_local() -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


def _emit_per_op_tool_source(oid: str, meta: dict[str, Any]) -> str:
    doc_short = (meta.get("summary") or oid).replace('"', "'")
    params = meta["parameters"]
    sig_lines: list[str] = []
    body_lines: list[str] = ["    q: dict[str, str] = {}"]
    for p in params:
        api_name = p["name"]
        py_name = _python_param_name(api_name)
        desc = _param_description(p, meta)
        sch = p.get("schema") or {}
        enum = sch.get("enum")
        req = bool(p.get("required"))
        if enum:
            lit = ", ".join(repr(x) for x in enum)
            typ = f"Literal[{lit}]"
            if sch.get("default") is not None:
                d = repr(sch["default"])
                sig_lines.append(
                    f"    {py_name}: Annotated[{typ}, Field(default={d}, description={desc!r})]"
                )
                body_lines.append(f"    q[{api_name!r}] = str({py_name})")
            else:
                sig_lines.append(
                    f"    {py_name}: Annotated[{typ} | None, Field(default=None, description={desc!r})] = None"
                )
                body_lines.append(
                    f"    if {py_name} is not None:\n        q[{api_name!r}] = str({py_name})"
                )
        elif req:
            sig_lines.append(f"    {py_name}: Annotated[str, Field(description={desc!r})]")
            body_lines.append(f"    q[{api_name!r}] = str({py_name})")
        else:
            sig_lines.append(
                f"    {py_name}: Annotated[str | None, Field(default=None, description={desc!r})] = None"
            )
            body_lines.append(
                f"    if {py_name} is not None:\n        q[{api_name!r}] = str({py_name})"
            )
    sig_text = ",\n".join(sig_lines)
    body_text = "\n".join(body_lines)
    return f"""
async def _dyn_{oid}(
{sig_text},
    context: Context | None = None,
) -> str:
    \"\"\"{doc_short}\"\"\"
{body_text}
    return await _run_t54_operation(_registry, {oid!r}, q, context)
"""


def _make_no_param_per_op_tool(
    registry: dict[str, dict[str, Any]],
    _run_t54_operation: Any,
    oid_local: str,
    meta: dict[str, Any],
) -> Any:
    async def _fn(context: Context | None = None) -> str:
        return await _run_t54_operation(registry, oid_local, None, context)

    _fn.__name__ = f"t54_{_camel_to_snake(oid_local)}"
    _fn.__doc__ = (meta.get("summary") or oid_local).replace('"', "'")
    return _fn


def _register_per_op_tools(
    mcp: Any,
    registry: dict[str, dict[str, Any]],
    _run_t54_operation: Any,
) -> None:
    for oid, meta in sorted(registry.items()):
        if not oid.isalnum():
            continue
        params_list = meta["parameters"]
        if not params_list:
            _no_params = _make_no_param_per_op_tool(registry, _run_t54_operation, oid, meta)
            mcp.add_tool(
                _no_params,
                name=_tool_name_for_operation(oid),
                title=meta.get("summary") or oid,
                description=_tool_docstring_for_registry(meta, oid),
                annotations=_annotations_t54_network(),
            )
            continue

        ns: dict[str, Any] = {
            "Annotated": Annotated,
            "Field": Field,
            "Literal": Literal,
            "Context": Context,
            "_run_t54_operation": _run_t54_operation,
            "_registry": registry,
        }
        src = _emit_per_op_tool_source(oid, meta)
        exec(src, ns)
        fn = ns[f"_dyn_{oid}"]
        mcp.add_tool(
            fn,
            name=_tool_name_for_operation(oid),
            title=meta.get("summary") or oid,
            description=_tool_docstring_for_registry(meta, oid),
            annotations=_annotations_t54_network(),
        )


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

    _known_operation_ids = ", ".join(sorted(registry.keys()))
    _t54_generic_op_id_desc = (
        "Exact OpenAPI operationId. Call t54_list_operations first. Known: "
        + _known_operation_ids
    )
    _t54_query_desc = (
        "Query string parameters as a JSON object. Keys must match OpenAPI query "
        "names for this operation (see resource openapi://agentic-swarm-t54-skus)."
    )
    globals()["_T54_MCP_GENERIC_OP_ID_DESC"] = _t54_generic_op_id_desc
    globals()["_T54_MCP_QUERY_DESC"] = _t54_query_desc

    @mcp.resource("openapi://agentic-swarm-t54-skus")
    def openapi_yaml() -> str:
        """Raw OpenAPI 3 YAML for T54 SKUs."""
        return openapi_text

    @mcp.tool(
        name="t54_list_operations",
        title="List T54 OpenAPI operations",
        description=(
            "Returns operationIds, HTTP methods, paths, and query parameter names from the bundled "
            "OpenAPI spec (no network). Use before t54_x402_request or per-SKU tools."
        ),
        annotations=_annotations_t54_local(),
    )
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
        try:
            openapi_display = str(openapi_path.resolve().relative_to(root))
        except ValueError:
            openapi_display = openapi_path.name
        return json.dumps(
            {
                "openapi_path": openapi_display,
                "base_url_env": "T54_SELLER_PUBLIC_BASE_URL",
                "operations": rows,
            },
            indent=2,
        )

    @mcp.tool(
        name="t54_x402_request",
        title="T54 x402 request (generic)",
        description=(
            "Execute any T54 seller operation by operationId with an optional query map. "
            "Prefer per-operation t54_* tools when available for clearer arguments. "
            "On HTTP 402, x402_broker_client pays then retries."
        ),
        annotations=_annotations_t54_network(),
    )
    async def t54_x402_request(
        operation_id: Annotated[str, Field(description=_T54_MCP_GENERIC_OP_ID_DESC)],
        query: Annotated[
            dict[str, Any] | None,
            Field(default=None, description=_T54_MCP_QUERY_DESC),
        ] = None,
        context: Context | None = None,
    ) -> str:
        """Execute one T54 HTTP operation by operationId. On 402, pays via x402_broker_client then retries."""
        return await _run_t54_operation(registry, operation_id, query, context)

    _register_per_op_tools(mcp, registry, _run_t54_operation)

    def _base_seller_origin() -> str:
        o = (os.getenv("MARKETPLACE_PUBLIC_BASE_URL") or os.getenv("X402_SELLER_PUBLIC_URL") or "").strip()
        if not o:
            return ""
        return o.rstrip("/").split("/x402")[0]

    async def _run_base_x402(
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> str:
        from x402_broker_client.client import execute_x402_request, get_pay_invoice_fn

        origin = _base_seller_origin()
        if not origin:
            return json.dumps(
                {
                    "error": "set MARKETPLACE_PUBLIC_BASE_URL or X402_SELLER_PUBLIC_URL to the Base seller origin",
                },
                indent=2,
            )
        url = _join_url(origin, path)
        pay = _pay_fn()
        status, body, err = execute_x402_request(
            url,
            payload=json_body,
            method=method,
            params=params,
            timeout=float((os.getenv("X402_MCP_TIMEOUT_SEC") or "120").strip() or "120"),
            pay_invoice=pay,
        )
        return json.dumps(
            {"status": status, "body": body, "error": err, "url": url},
            indent=2,
            default=str,
        )

    @mcp.tool(
        name="contract_triage",
        title="EVM contract triage (Base USDC x402)",
        description=(
            "Screen an EVM smart contract address for malicious patterns, honeypots, rug mechanics, "
            "and known scam frameworks. Returns risk score (0-100), verdict (SAFE/SUSPICIOUS/MALICIOUS), "
            "and top threat flags. Completes in under 30 seconds."
        ),
        annotations=_annotations_t54_network(),
    )
    async def contract_triage(
        contract_address: Annotated[str, Field(description="0x-prefixed EVM contract address to screen")],
        chain_id: Annotated[
            str,
            Field(description="CAIP-2 chain id (default Base mainnet eip155:8453)"),
        ] = "eip155:8453",
        context: Context | None = None,
    ) -> str:
        if context:
            await context.info(f"contract_triage {contract_address}")
        return await _run_base_x402(
            "GET",
            "/x402/v1/contract-triage",
            params={"contractAddress": contract_address, "chainId": chain_id},
        )

    @mcp.tool(
        name="contract_audit",
        title="Full contract audit (Base USDC x402)",
        description=(
            "Run a full 5-phase security audit on up to 3 EVM contract addresses. Handles EIP-1167 "
            "proxy/implementation pairs. Returns complete intelligence card including Slither findings, "
            "Echidna fuzz results, deployer profiling, EIP-7702 delegate detection, money flow trace, "
            "and holder analysis."
        ),
        annotations=_annotations_t54_network(),
    )
    async def contract_audit(
        addresses: Annotated[str, Field(description="Comma-separated 0x addresses (max 3 proxy/implementation pairs)")],
        chain_id: Annotated[
            str,
            Field(description="CAIP-2 chain id (default Base mainnet eip155:8453)"),
        ] = "eip155:8453",
        context: Context | None = None,
    ) -> str:
        if context:
            await context.info("contract_audit")
        return await _run_base_x402(
            "GET",
            "/x402/v1/contract-audit",
            params={"addresses": addresses, "chainId": chain_id},
        )

    @mcp.tool(
        name="contract_monitor_subscribe",
        title="Contract monitoring subscription (Base USDC x402)",
        description=(
            "Subscribe to 30-day continuous monitoring of up to 10 EVM contract addresses. "
            "Fires webhook alerts on admin key movement, liquidity drops, claim condition changes, "
            "or new critical Slither findings."
        ),
        annotations=_annotations_t54_network(),
    )
    async def contract_monitor_subscribe(
        addresses: Annotated[list[str], Field(description="Up to 10 0x-prefixed EVM addresses to watch")],
        webhook_url: Annotated[str, Field(description="HTTPS URL that receives POST alerts when risk thresholds breach")],
        thresholds: Annotated[
            dict[str, Any] | None,
            Field(
                default=None,
                description=(
                    "Optional JSON object for alert sensitivity (e.g. liquidity drop %, admin key moves). "
                    "Omit or {} for seller defaults."
                ),
            ),
        ] = None,
        duration_days: Annotated[
            int,
            Field(
                default=30,
                description="Subscription length in days (default 30; max per seller policy).",
            ),
        ] = 30,
        context: Context | None = None,
    ) -> str:
        if context:
            await context.info("contract_monitor_subscribe")
        body = {
            "addresses": addresses[:10],
            "webhookUrl": webhook_url,
            "durationDays": duration_days,
            "thresholds": thresholds or {},
        }
        return await _run_base_x402("POST", "/x402/v1/contract-monitor", json_body=body)

    @mcp.prompt(
        name="t54_swarm_intro",
        title="T54 x402 MCP — intro",
        description="Explains how to use this MCP server with Agentic Swarm.",
    )
    def prompt_t54_swarm_intro() -> str:
        return (
            "You are connected to Agentic Swarm T54 x402 MCP tools. "
            "1) Call t54_list_operations to see operationIds and HTTP paths. "
            "2) Prefer per-operation tools (t54_* snake_case) with explicit parameters. "
            "3) Or use t54_x402_request(operation_id, query) for generic calls. "
            "4) Paid routes return HTTP 402 until the broker settles; set T54_SELLER_PUBLIC_BASE_URL "
            "and X402_BROKER_PAY_MODE in the environment. "
            "5) Open openapi://agentic-swarm-t54-skus for full OpenAPI."
        )

    @mcp.prompt(
        name="t54_call_sku",
        title="T54 — call a SKU",
        description="Structured prompt for a specific operationId.",
    )
    def prompt_t54_call_sku(
        operation_id: Annotated[
            str,
            Field(
                description=(
                    "OpenAPI operationId (e.g. structuredQuery, getHealth, researchBrief, "
                    "constitutionAuditLite, agentCommerceData, airdropIntelligence, helloPing)."
                ),
            ),
        ] = "structuredQuery",
    ) -> str:
        return (
            f"Call the T54 seller operation `{operation_id}`. "
            "First use t54_list_operations to confirm query parameters, then invoke the matching "
            f"t54_* tool or t54_x402_request with operation_id={operation_id!r}. "
            "If the response is HTTP 402, the x402 broker must pay before the body returns."
        )

    @mcp.prompt(
        name="t54_x402_troubleshooting",
        title="T54 x402 — troubleshooting",
        description="When 402, env, or broker issues appear.",
    )
    def prompt_t54_troubleshoot() -> str:
        return (
            "If tools return JSON with status 402: the seller requires payment. Ensure "
            "X402_BROKER_PAY_MODE and keys match your rail (mock for dry runs). "
            "Set T54_SELLER_PUBLIC_BASE_URL to the public seller origin (no trailing slash). "
            "Use X402_MCP_DRY_RUN=1 only for mock settlement. Check openapi://agentic-swarm-t54-skus "
            "for parameter names and paths."
        )

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
        pe = (os.getenv("PORT") or "").strip()
        if pe.isdigit():
            port = int(pe)
        elif args.transport == "streamable-http":
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
