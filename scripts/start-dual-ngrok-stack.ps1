# Stop any existing ngrok agent, start dual tunnels (T54 8765 + x402 8043), sync .env from ngrok API.
# Requires: listeners on 8765 and 8043 (npm run t54:seller and npm run x402:seller).
param(
    [switch]$SkipStopNgrok
)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

foreach ($p in @(8765, 8043)) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $c) {
        Write-Host "dual-ngrok: WARNING - nothing listening on port $p (tunnel errors until server binds)."
    }
}

$exe = Join-Path $env:LOCALAPPDATA "Programs\Ngrok\ngrok.exe"
if (-not (Test-Path $exe)) {
    $exe = Join-Path $Root ".tools\ngrok\ngrok.exe"
}
if (-not (Test-Path $exe)) {
    Write-Error "ngrok.exe not found. Run: scripts\install-ngrok-global.ps1"
    exit 1
}

if (-not $SkipStopNgrok) {
    Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "dual-ngrok: stopped ngrok PID $($_.Id)"
    }
    Start-Sleep -Seconds 2
}

$cfg = Join-Path $Root "scripts\ngrok-dual-stack.yml"
if (-not (Test-Path $cfg)) {
    Write-Error "Missing $cfg"
    exit 1
}

$globalNgrok = Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml"
if (-not (Test-Path $globalNgrok)) {
    $globalNgrok = Join-Path $env:USERPROFILE ".ngrok2\ngrok.yml"
}
if (-not (Test-Path $globalNgrok)) {
    Write-Error "No ngrok authtoken config found. Install: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
}

$nOut = Join-Path $logDir "ngrok-dual.log"
$nErr = Join-Path $logDir "ngrok-dual.err.log"
Start-Process -FilePath $exe -ArgumentList @("start", "--all", "--config", $globalNgrok, "--config", $cfg) -WorkingDirectory $Root -WindowStyle Hidden `
    -RedirectStandardOutput $nOut -RedirectStandardError $nErr
Start-Sleep -Seconds 5

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }
& $py "$Root\scripts\sync_t54_env_from_ngrok.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "dual-ngrok: T54 sync failed (see ngrok logs: $nErr)"
}
& $py "$Root\scripts\sync_x402_env_from_ngrok.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "dual-ngrok: x402 sync failed (see ngrok logs: $nErr)"
    exit 1
}
Write-Host "dual-ngrok: done. Check .env for T54_SELLER_PUBLIC_BASE_URL and X402_SELLER_PUBLIC_URL."
