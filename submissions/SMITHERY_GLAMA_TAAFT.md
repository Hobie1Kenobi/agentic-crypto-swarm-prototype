# Smithery, Glama, and TAAFT — setup runbook

Use this after **[DIRECTORY_SUBMISSION_KIT.md](../DIRECTORY_SUBMISSION_KIT.md)** copy is finalized. Repo: **`https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype`**.

---

## 1. Glama (do this first for Awesome MCP)

The [Awesome MCP Servers PR](awesome-mcp-servers-PR.md) badge URL only works after Glama lists the repo.

1. Open **[glama.ai/mcp/servers](https://glama.ai/mcp/servers)** → **Add Server** (top).
2. Submit the **GitHub repository URL** above (or follow their wizard for GitHub import).
3. Confirm the server page loads:  
   **`https://glama.ai/mcp/servers/Hobie1Kenobi/agentic-crypto-swarm-prototype`**  
   (score badge SVG should resolve for the PR line.)
4. If the page 404s, wait for indexing or contact Glama support with repo + `mcp-manifest.json` / `smithery.yaml` links.

**Artifacts:** root **`mcp-manifest.json`**, **`smithery.yaml`**, **`documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml`**.

---

## 2. Smithery

Smithery supports multiple publish paths; this repo has both **stdio** (`smithery.yaml`) and a **public HTTP MCP** endpoint.

### Option A — GitHub / stdio (matches `smithery.yaml`)

1. Sign in at **[smithery.ai](https://smithery.ai/)**.
2. Use **Build / Publish** flow to connect **this GitHub repo** (root `smithery.yaml` defines stdio + `uv` + `scripts/mcp_server.py`).
3. Complete any build logs; ensure the latest release succeeds.

Docs: **[smithery.ai/docs/build](https://smithery.ai/docs/build/index)** · config: **[smithery.ai/docs/config#smitheryyaml](https://smithery.ai/docs/config#smitheryyaml)**.

### Option B — Hosted URL (Streamable HTTP)

**Prerequisites on your host:** `mcp>=1.23`, **`npm run mcp:t54:streamable-http`** (port **9052**), **`npm run proxy:unified`** (Caddy routes exact **`/mcp`** → 9052; **`/mcp/sse`** → 9051 SSE). Without 9052 running, **`GET /mcp` returned 404** (SSE-only).

- **MCP URL for Smithery:** `https://api.agentic-swarm-marketplace.com/mcp`  
  (Initialize with **`Accept: application/json`** + **`Content-Type: application/json`** POST.)

1. Go to **[smithery.ai/new](https://smithery.ai/new)** (URL publish).
2. Enter **`https://api.agentic-swarm-marketplace.com/mcp`**; finish the wizard.

**Cloudflare:** Smithery scans with **`SmitheryBot/1.0`**. If the scan fails with **403**, allow that user-agent or follow **[Smithery publish troubleshooting](https://smithery.ai/docs/build/publish#troubleshooting)** (same guidance as **`documentation/operations/CLOUDFLARE_CACHE_AND_SECURITY.md`** for bots).

CLI (optional): `smithery mcp publish "https://api.agentic-swarm-marketplace.com/mcp" -n @your-namespace/agentic-crypto-swarm` (see Smithery CLI docs).

**Observability / health:** See **[documentation/operations/SMITHERY_OBSERVABILITY.md](../documentation/operations/SMITHERY_OBSERVABILITY.md)** and run **`python scripts/probe_smithery_upstream.py`** (uses **SmitheryBot** UA). Smithery **runtime logs** API: [list runtime logs](https://smithery.ai/docs/api-reference/servers/list-runtime-logs.md) (`GET /servers/{qualifiedName}/logs` with API key).

---

## 3. TAAFT (There's An AI For That)

1. Open **[theresanaiforthat.com/s/submit/](https://theresanaiforthat.com/s/submit/)**.
2. Paste fields from **[taaft-form-copy.md](taaft-form-copy.md)** (primary site: **`https://www.agentic-swarm-marketplace.com/`**).
3. Read **[theresanaiforthat.com/s/submission+guide/](https://theresanaiforthat.com/s/submission+guide/)** for category limits.
4. Search the site for **“Agentic Swarm”** first — **claim or update** an existing listing if present.

---

## 4. After all three

- [ ] Glama server page returns **200** (badge OK for Awesome MCP PR).
- [ ] Smithery shows your server (stdio and/or URL release green).
- [ ] TAAFT listing live with correct **www** URL.
- [ ] Open **[awesome-mcp-servers-PR.md](awesome-mcp-servers-PR.md)** PR to **punkpeye/awesome-mcp-servers** when Glama badge works.

---

## Quick links

| Registry | Action URL |
|----------|------------|
| **Glama** | [Add Server](https://glama.ai/mcp/servers) |
| **Smithery** | [smithery.ai](https://smithery.ai/) · [URL publish](https://smithery.ai/new) |
| **TAAFT** | [Submit](https://theresanaiforthat.com/s/submit/) |
