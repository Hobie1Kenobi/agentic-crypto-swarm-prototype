# SSE MCP for remote clients (Agent.ai). Bind localhost; expose via Caddy :9080/mcp → tunnel.
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot
$port = if ($env:X402_MCP_SSE_PORT) { $env:X402_MCP_SSE_PORT } else { "9051" }
$hostBind = if ($env:X402_MCP_SSE_HOST) { $env:X402_MCP_SSE_HOST } else { "127.0.0.1" }
if ($env:SWARM_MCP_PYTHON) {
    & $env:SWARM_MCP_PYTHON -u (Join-Path $PSScriptRoot "mcp_server.py") --transport sse --host $hostBind --port $port @args
} else {
    $py = $null
    foreach ($line in (& where.exe python 2>$null)) {
        if ($line -and $line -notmatch "WindowsApps") {
            $py = $line.Trim()
            break
        }
    }
    if (-not $py) { $py = "python" }
    & $py -u (Join-Path $PSScriptRoot "mcp_server.py") --transport sse --host $hostBind --port $port @args
}
