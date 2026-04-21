# Smithery observability — health checks and tracing tool calls

Your Smithery **Observability** tab shows RPC methods (`tools/list`, `tools/call`), error rates, and latency. This doc ties those metrics to your stack and shows how to see **how far a call got**.

## Request path

```text
Client / Smithery Gateway → https://api.agentic-swarm-marketplace.com/mcp
  → Cloudflare (WAF; SmitheryBot allowlist) → Tunnel → Caddy :9080 → 127.0.0.1:9052
  → scripts/mcp_server.py (FastMCP streamable HTTP)
  → tool handler → optional HTTP to T54 seller / Base x402 APIs (402 + pay + retry)
```

- **`tools/list`** is cheap (in-process): expect **low hundreds of ms** if the tunnel and process are warm.
- **`tools/call`** latency is dominated by **which tool** ran:
  - **Local / no network** (e.g. `t54_list_operations`): sub-second when healthy.
  - **Paid / network** (`t54_*` against a live seller, `contract_*`): often **many seconds** up to **`X402_MCP_TIMEOUT_SEC`** (default **120s** in `scripts/mcp_server.py` and `x402_broker_client`).

That matches a **high P50 / P95 on `tools/call`** in Smithery even when the server is “healthy”: the metric blends fast and slow tools.

## “Unavailable” on `tools/call` (no 5xx in your app)

Common causes:

1. **Gateway / proxy timeout** while the tool is still waiting on x402 or a slow audit.
2. **Tunnel or origin offline** intermittently — Smithery sees connection failure, not an HTTP 500.
3. **403 on `/mcp`** for traffic **without** an allowlisted `User-Agent` (e.g. ad‑hoc `curl` without `SmitheryBot`). Smithery’s own requests use the bot UA; random probes can look like failures if you forget the header.

## Health checks (run anytime)

| Check | Command / URL |
|--------|----------------|
| API + `.well-known` | `python scripts/verify_public_api.py` |
| MCP chain (Smithery-style) | `python scripts/probe_smithery_upstream.py` |
| Marketing site | GET `https://www.agentic-swarm-marketplace.com/` → expect **200** |

The probe script posts **`initialize` → `tools/list` → `tools/call`** on `t54_list_operations` with **`User-Agent: SmitheryBot/1.0 (+https://smithery.ai)`** so it matches production WAF rules.

## How far did a Smithery tool call get?

1. **Smithery Platform API — runtime logs** (per-invocation request/response, duration, log lines, exceptions):  
   - Docs: [List runtime logs](https://smithery.ai/docs/api-reference/servers/list-runtime-logs.md)  
   - `GET https://api.smithery.ai/servers/{qualifiedName}/logs` with **`Authorization: Bearer <SMITHERY_API_KEY>`**  
   - Example qualified name: `hobiecunningham%2Fagentic-swarm-marketplace` (encode `/` as `%2F`).  
   - **CLI:** `python scripts/fetch_smithery_runtime_logs.py` (reads **`SMITHERY_API_KEY`** from **`.env.local`**). Override server with `--qualified-name namespace/server`.

2. **Your origin** (if you host the MCP process):  
   - `logs/mcp-unified-streamable.log` / `.err.log` when started via `scripts/start-mcp-unified.ps1`  
   - Caddy / tunnel logs for **502 / timeout** between Cloudflare and `127.0.0.1:9052`

3. **Application**: tool handlers use `context.info(...)` for some paths; heavy debugging may require structured logging around `execute_x402_request` (not enabled by default).

## Interpreting your dashboard snapshot

- **`tools/list` ~0% errors, ~178 ms P50** → discovery path and WAF/tunnel are broadly fine.
- **`tools/call` ~5.7% unavailable, ~16 s P50`** → consistent with **timeouts or cold tunnel** plus **slow x402/audit tools** in the mix; use **Smithery runtime logs** to split “client gave up” vs “server still working.”

## Related

- `documentation/operations/CLOUDFLARE_CACHE_AND_SECURITY.md` — **SmitheryBot** WAF rule  
- `scripts/reverse-proxy/Caddyfile` — `/mcp` → **9052**
