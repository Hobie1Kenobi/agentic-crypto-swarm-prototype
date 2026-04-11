# Run on the machine where Cloudflare Tunnel points to Caddy :9080 (api.agentic-swarm-marketplace.com).
# Pulls the canonical Git branch so the live stack matches GitHub, then optionally restarts the unified stack.
param(
    [string]$Branch = "master",
    [string]$Remote = "origin",
    [switch]$RestartStack
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "[sync-api-host] repository: $Root"
Write-Host "[sync-api-host] fetching $Remote ..."
git fetch $Remote
git checkout $Branch
git pull $Remote $Branch

$sha = (git rev-parse HEAD).Trim()
$short = (git rev-parse --short HEAD).Trim()
$line = (git log -1 --oneline).Trim()
Write-Host "[sync-api-host] HEAD $sha ($short)"
Write-Host "[sync-api-host] $line"

if ($RestartStack) {
    Write-Host "[sync-api-host] restarting unified stack (Caddy, sellers, MCP, ngrok) ..."
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) { throw "npm.cmd not found on PATH." }
    & npm.cmd run stack:unified:stop
    & npm.cmd run stack:unified:start
    Write-Host "[sync-api-host] done. Confirm tunnel still targets http://127.0.0.1:9080 in Cloudflare Zero Trust."
}
