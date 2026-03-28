# Start full unified stack on Windows: T54 seller :8765, x402 seller :8043, marketplace :8055,
# Caddy :9080, ngrok dual config (t54 + x402 + unified). Uses cmd.exe + npm.cmd (reliable; Start-Process npm is not).
# After tunnels are up, runs sync_t54 + sync_x402 so .env matches the unified ngrok origin.
#
# -Ensure: only start services whose listen port is down (for logon/watchdog; does not stop running processes).
param(
    [switch]$NoStop,
    [switch]$NoSync,
    [switch]$Ensure,
    [int]$NgrokApiWaitSeconds = 45
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Get-NpmCmdPath {
    $g = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($g -and $g.Source -and (Test-Path $g.Source)) { return $g.Source }
    $w = & where.exe npm.cmd 2>$null | Select-Object -First 1
    if ($w -and (Test-Path $w)) { return $w.Trim() }
    $fallback = Join-Path $env:APPDATA "npm\npm.cmd"
    if (Test-Path $fallback) { return $fallback }
    throw "npm.cmd not found on PATH. Install Node.js / npm."
}

function Test-PortListen([int]$p) {
    return $null -ne (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Start-NpmRunDetached {
    param(
        [string]$NpmCmd,
        [string]$ScriptName,
        [string]$LogBaseName
    )
    $out = Join-Path $logDir "$LogBaseName.log"
    $err = Join-Path $logDir "$LogBaseName.err.log"
    $cmdLine = "cd /d `"$Root`" && `"$NpmCmd`" run $ScriptName"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmdLine) -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err
}

$npm = Get-NpmCmdPath

$caddy = Get-Command caddy -ErrorAction SilentlyContinue
if (-not $caddy) {
    Write-Host "Install Caddy and add to PATH: winget install CaddyServer.Caddy" -ForegroundColor Yellow
    exit 1
}

if ($Ensure) {
    if (-not (Test-PortListen 8765)) {
        Write-Host "[unified-stack] ensure: starting t54:seller -> logs/unified-stack-t54-seller.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "t54:seller" -LogBaseName "unified-stack-t54-seller"
        Start-Sleep -Seconds 2
    }
    if (-not (Test-PortListen 8043)) {
        Write-Host "[unified-stack] ensure: starting x402:seller -> logs/unified-stack-x402-seller.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "x402:seller" -LogBaseName "unified-stack-x402-seller"
        Start-Sleep -Seconds 2
    }
    if (-not (Test-PortListen 8055)) {
        Write-Host "[unified-stack] ensure: starting marketplace:serve -> logs/unified-stack-marketplace.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "marketplace:serve" -LogBaseName "unified-stack-marketplace"
        Start-Sleep -Seconds 6
    }
    if (-not (Test-PortListen 9080)) {
        Write-Host "[unified-stack] ensure: starting proxy:unified (Caddy) -> logs/unified-stack-caddy.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "proxy:unified" -LogBaseName "unified-stack-caddy"
        Start-Sleep -Seconds 3
    }
    if (-not (Test-PortListen 4040)) {
        Write-Host "[unified-stack] ensure: starting ngrok:dual -> logs/unified-stack-ngrok.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "ngrok:dual" -LogBaseName "unified-stack-ngrok"
    }
} else {
    if (-not $NoStop) {
        & (Join-Path $PSScriptRoot "stop-unified-stack.ps1")
        Start-Sleep -Seconds 2
    }

    Write-Host "[unified-stack] starting t54:seller -> logs/unified-stack-t54-seller.log"
    Start-NpmRunDetached -NpmCmd $npm -ScriptName "t54:seller" -LogBaseName "unified-stack-t54-seller"
    Start-Sleep -Seconds 2

    Write-Host "[unified-stack] starting x402:seller -> logs/unified-stack-x402-seller.log"
    Start-NpmRunDetached -NpmCmd $npm -ScriptName "x402:seller" -LogBaseName "unified-stack-x402-seller"
    Start-Sleep -Seconds 2

    Write-Host "[unified-stack] starting marketplace:serve -> logs/unified-stack-marketplace.log"
    Start-NpmRunDetached -NpmCmd $npm -ScriptName "marketplace:serve" -LogBaseName "unified-stack-marketplace"
    Start-Sleep -Seconds 6

    Write-Host "[unified-stack] starting proxy:unified (Caddy) -> logs/unified-stack-caddy.log"
    Start-NpmRunDetached -NpmCmd $npm -ScriptName "proxy:unified" -LogBaseName "unified-stack-caddy"
    Start-Sleep -Seconds 3

    Write-Host "[unified-stack] starting ngrok:dual -> logs/unified-stack-ngrok.log"
    Start-NpmRunDetached -NpmCmd $npm -ScriptName "ngrok:dual" -LogBaseName "unified-stack-ngrok"
}

$deadline = (Get-Date).AddSeconds($NgrokApiWaitSeconds)
$apiOk = $false
while ((Get-Date) -lt $deadline) {
    try {
        $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
        if ($t.tunnels -and @($t.tunnels).Count -ge 1) {
            $apiOk = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}

if (-not $apiOk) {
    Write-Host "[unified-stack] WARNING: ngrok API on :4040 not ready within ${NgrokApiWaitSeconds}s. Check logs/unified-stack-ngrok.err.log"
}

foreach ($port in @(8765, 8043, 8055, 9080, 4040)) {
    if (Test-PortListen $port) {
        Write-Host "[unified-stack] OK listen :$port"
    } else {
        Write-Host "[unified-stack] MISSING listener :$port (see logs under $logDir)"
    }
}

if (-not $NoSync) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = "python" }
    & $py "$Root\scripts\sync_t54_env_from_ngrok.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync T54 exited $LASTEXITCODE" }
    & $py "$Root\scripts\sync_x402_env_from_ngrok.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync x402 exited $LASTEXITCODE" }
}

try {
    $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $t.tunnels | ForEach-Object { Write-Host "[unified-stack] tunnel $($_.name) $($_.public_url)" }
} catch {
    Write-Host "[unified-stack] could not list tunnels: $_"
}

Write-Host "[unified-stack] done. If you changed .env, restart uvicorn sellers/marketplace so they reload env."
