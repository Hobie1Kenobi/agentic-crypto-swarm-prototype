# Start Caddy unified reverse proxy (:9080). Requires Caddy on PATH.
# See: scripts/reverse-proxy/README.md

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$caddyfile = Join-Path $repo "scripts/reverse-proxy/Caddyfile"
if (-not (Test-Path $caddyfile)) { Write-Error "Missing $caddyfile"; exit 1 }

$caddy = Get-Command caddy -ErrorAction SilentlyContinue
if (-not $caddy) {
    Write-Host "Install Caddy: https://caddyserver.com/docs/install" -ForegroundColor Yellow
    Write-Host "  winget install CaddyServer.Caddy" -ForegroundColor Gray
    exit 1
}

Set-Location $repo
& caddy run --config $caddyfile
