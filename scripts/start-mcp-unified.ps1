# Start both MCP processes for unified Caddy: SSE :9051 + Streamable HTTP :9052 (Smithery /mcp).
# Used by npm run mcp:t54:unified; also invoked from start-unified-stack.ps1 logic.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-NpmCmdPath {
    $g = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($g -and $g.Source -and (Test-Path $g.Source)) { return $g.Source }
    $w = & where.exe npm.cmd 2>$null | Select-Object -First 1
    if ($w -and (Test-Path $w)) { return $w.Trim() }
    $fallback = Join-Path $env:APPDATA "npm\npm.cmd"
    if (Test-Path $fallback) { return $fallback }
    throw "npm.cmd not found on PATH."
}

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$npm = Get-NpmCmdPath

$out1 = Join-Path $logDir "mcp-unified-sse.log"
$err1 = Join-Path $logDir "mcp-unified-sse.err.log"
$out2 = Join-Path $logDir "mcp-unified-streamable.log"
$err2 = Join-Path $logDir "mcp-unified-streamable.err.log"

Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "cd /d `"$Root`" && `"$npm`" run mcp:t54:sse") -WindowStyle Hidden `
    -RedirectStandardOutput $out1 -RedirectStandardError $err1
Start-Sleep -Seconds 1
Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "cd /d `"$Root`" && `"$npm`" run mcp:t54:streamable-http") -WindowStyle Hidden `
    -RedirectStandardOutput $out2 -RedirectStandardError $err2

Write-Host "[mcp-unified] started mcp:t54:sse (9051) and mcp:t54:streamable-http (9052). Logs: $logDir"
