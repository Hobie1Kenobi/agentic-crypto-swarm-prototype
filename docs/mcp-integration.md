# Connect your agent (MCP) — T54 x402

This guide shows how to attach **Cursor**, **Claude Desktop**, or any MCP-capable client to the **Swarm T54 x402** stdio server in this repository. The server exposes OpenAPI-driven tools that call your **T54 seller** HTTP API; on **402**, it uses **`x402_broker_client`** to pay the invoice (mock, XRPL testnet/mainnet, Xaman, or Base USDC — per your `.env`).

**You need a local clone** of [agentic-crypto-swarm-prototype](https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype) — the MCP process runs Python from your machine and reads `.env` for seller URL and broker mode.

## 1. Prerequisites

- **Python 3.12+** on your PATH (avoid the Windows Store stub; use a real install or `py` launcher).
- Dependencies (minimal): `pip install "mcp[cli]" pyyaml python-dotenv` plus whatever your checkout needs for `x402_broker_client` (see repo `packages/`).
- **Seller URL**: set `T54_SELLER_PUBLIC_BASE_URL` in `.env` to the public origin that serves T54 routes (often ends with `/t54`). Current values for tunnels are also listed in [endpoints.json](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/endpoints.json) after you run `npm run docs:sync-endpoints` from a configured machine.

Preflight (no stdio):

```bash
python scripts/mcp_server.py --check
```

Dry-run (no real payment):

```bash
set X402_MCP_DRY_RUN=1
```

(Unix: `export X402_MCP_DRY_RUN=1`)

Optional: `SWARM_MCP_PYTHON=C:\Path\To\python.exe` if Cursor must use a specific interpreter on Windows.

## 2. Cursor (project MCP)

**File:** `.cursor/mcp.json` in the repo root (or merge into your user MCP config without duplicating the same server name).

**Windows (recommended in this repo):** PowerShell launcher picks a real `python`, `cd`s to repo root, runs `mcp_server.py` unbuffered.

```json
{
  "mcpServers": {
    "swarm-t54-x402": {
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "${workspaceFolder}/scripts/run-mcp-t54.ps1"
      ]
    }
  }
}
```

**macOS / Linux (example):** if `scripts/run-mcp-t54.ps1` is not used, point `command` at your Python and the script (adjust paths):

```json
{
  "mcpServers": {
    "swarm-t54-x402": {
      "command": "/usr/local/bin/python3.12",
      "args": ["-u", "${workspaceFolder}/scripts/mcp_server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Reload the window after edits: **Developer: Reload Window**.

## 3. Claude Desktop

Edit Claude’s config file (location varies by OS; search for `claude_desktop_config.json`) and add a `mcpServers` entry with **absolute paths** to your clone — Claude does not expand `${workspaceFolder}`.

Example shape:

```json
{
  "mcpServers": {
    "swarm-t54-x402": {
      "command": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "D:\\path\\to\\agentic-crypto-swarm-prototype\\scripts\\run-mcp-t54.ps1"
      ]
    }
  }
}
```

Or call `python.exe` + `scripts/mcp_server.py` with `"cwd"` set to the repo root.

Restart Claude Desktop after saving.

## 4. What you get

- **Resource:** `openapi://agentic-swarm-t54-skus` — raw OpenAPI YAML.
- **Tools:** `t54_list_operations`, `t54_x402_request`, and one tool per operation id (e.g. `t54_airdropIntelligence`).
- Behavior: tool call → HTTP request → **402** → broker pays → retry → JSON result back to the model.

## 5. Public “one-line install” (future)

A small **`npx`** or **`uvx`**-style wrapper that downloads nothing secret but points at **your** public seller URL is **not** published in this repo yet. Until then, third parties should clone the repo, set `.env`, and use the JSON above. When a packaged client exists, it will be linked from [llms.txt](https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/llms.txt) and this page.

## 6. Related discovery files

| File | URL |
|------|-----|
| Machine-readable site overview | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/llms.txt |
| Live tunnel / seller origins | https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/endpoints.json |
| T54 OpenAPI (raw) | https://raw.githubusercontent.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/master/documentation/x402-t54-base/openapi/agentic-swarm-t54-skus.openapi.yaml |
