# MCP publish checklist (terminal-first)

Use this when you want **distribution** beyond your own host: official MCP Registry, Smithery (already primary for this repo), optional MCPize, and manual Glama. **A2A** discovery for agents is already covered by `https://api.agentic-swarm-marketplace.com/.well-known/agent-card.json` and related `/.well-known/*` routes; there is no single global `a2a register` CLI.

**Production MCP URL (Streamable HTTP):** `https://api.agentic-swarm-marketplace.com/mcp`  
**Smithery qualified name** (replace if your namespace differs): `hobiecunningham/agentic-swarm-marketplace` — see [SMITHERY_OBSERVABILITY.md](./SMITHERY_OBSERVABILITY.md).

---

## 1. Smithery (republish after changes)

Requires Node.js 20+ and a Smithery account.

```bash
npm install -g @smithery/cli@latest
smithery auth login
smithery mcp publish "https://api.agentic-swarm-marketplace.com/mcp" -n YOUR_NAMESPACE/YOUR_SERVER
```

Use the qualified name shown in the Smithery dashboard. For local debugging: `smithery --help`, `smithery mcp search …`.

Docs: [https://smithery.ai/docs/concepts/cli](https://smithery.ai/docs/concepts/cli)

---

## 2. Official MCP Registry (`mcp-publisher`)

The registry stores **metadata**; you typically need a published **npm** package that matches your `server.json` (see the quickstart).

**Install (pick one):**

- macOS / Linux (Homebrew): `brew install mcp-publisher`
- Or download a release binary from [https://github.com/modelcontextprotocol/registry/releases](https://github.com/modelcontextprotocol/registry/releases) (Windows: extract `mcp-publisher.exe` and put it on `PATH`).

**Workflow:**

```bash
cd path/to/your-mcp-package
mcp-publisher init
# Edit server.json: name, description, packages[].identifier must match npm, etc.
mcp-publisher login github
mcp-publisher publish --dry-run   # optional
mcp-publisher publish
```

Verify (adjust search string):

```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.YOURUSER"
```

Docs: [https://modelcontextprotocol.io/registry/quickstart](https://modelcontextprotocol.io/registry/quickstart), [https://modelcontextprotocol.io/registry/authentication](https://modelcontextprotocol.io/registry/authentication)

---

## 3. MCPize (optional hosted duplicate + marketplace)

This repo includes **`mcpize.yaml`** at the repository root: **install** is `pip install -r requirements.txt`. MCPize’s generated Dockerfile runs **`COPY requirements.txt* ./`** at the repo root, then pip, then **`COPY . .`**; the canonical list is **`requirements.txt`** at the repository root ( **`packages/agents/requirements.txt`** is a `-r ../../requirements.txt` shim for existing `pip install -r packages/agents/...` docs). **Build** runs `pip install ./packages/agents` (installs **`x402_broker_client`**, **`external_commerce`**, **`integrations`** from `packages/agents/pyproject.toml`) then `python scripts/mcp_server.py --check`. **Start** runs Streamable HTTP on **`0.0.0.0`** with port from **`PORT`**. Local preflight:

```bash
npx mcpize@latest doctor
```

Authenticate (opens browser), then deploy from repo root:

```bash
npm install -g mcpize@latest
mcpize login
mcpize deploy --yes
mcpize publish --auto
```

Set paid-tool secrets (T54 / Base URLs, keys, `X402_MCP_DRY_RUN`, etc.) in the MCPize dashboard if you need live settlement. Do not use a top-level `env:` key in `mcpize.yaml` (MCPize ignores it); use **`secrets`** / **`credentials`** per [mcpize.yaml wiki](https://github.com/mcpize/cli/wiki/How-to-configure-your-deployment-via-mcpize.yaml).

Docs: [https://github.com/mcpize/cli](https://github.com/mcpize/cli)

---

## 4. Glama (web submit + optional `glama.json`)

No official one-line global CLI for **submitting**; add the server from [https://glama.ai](https://glama.ai) (GitHub repo or **Connector** URL for remote Streamable HTTP). Optional: add `glama.json` at the repo root for display name, description, env vars — see Glama’s “Add MCP Server” help.

Read-only API example (after listed):

```bash
curl -sS "https://glama.ai/api/mcp/v1/servers/OWNER/PACKAGE"
```

---

## 5. Post-publish verification (this project’s public API)

From any machine:

```bash
npm run probe:well-known
# or
python scripts/probe_well_known.py
```

Spot-check MCP discovery:

```bash
curl -sS -H "Accept: application/json" "https://api.agentic-swarm-marketplace.com/.well-known/mcp/server-card.json" | head -c 400
```

Smithery calls should use the gateway URL you configured; ad-hoc `curl` to `/mcp` may need the **SmitheryBot** `User-Agent` if your edge blocks other bots (see [SMITHERY_OBSERVABILITY.md](./SMITHERY_OBSERVABILITY.md)).

---

## 6. What this checklist does not cover

- **Visa / Yellow.ai / enterprise CPaaS:** partner or “connect your MCP URL inside their product” flows, not a public `register` CLI.
- **Stellar / x402 / MPP:** payment and agentic HTTP layers ([https://developers.stellar.org/docs/build/agentic-payments](https://developers.stellar.org/docs/build/agentic-payments)); list your **API** in x402/MPP catalogs separately if you join those programs.

Keep `smithery.yaml`, `PUBLIC_API_ORIGIN` / tunnel routing, and WAF allowlists aligned with [SMITHERY_OBSERVABILITY.md](./SMITHERY_OBSERVABILITY.md) whenever you change the live MCP endpoint.
