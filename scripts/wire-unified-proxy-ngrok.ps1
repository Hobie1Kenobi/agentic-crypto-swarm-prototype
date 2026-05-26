# Start Caddy on :9080 if needed, restart ngrok with scripts/ngrok-dual-stack.yml (t54 + x402 + unified),
# then sync .env / .env.mainnet public URLs and reload T54 discovery.
# Does NOT stop your sellers on 8765/8043/8055 (use with stack:24h daemons or manual npm runs).
#
# Usage (repo root): npm run stack:unified:wire
# Prerequisites: listeners on 8765, 8043, 8055; ngrok authtoken in %LOCALAPPDATA%\ngrok\ngrok.yml; Caddy on PATH.

param(
    [int]$NgrokApiWaitSeconds = 50
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-PortListen([int]$p) {
    return $null -ne (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Get-NpmCmdPath {
    $g = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($g -and $g.Source -and (Test-Path $g.Source)) { return $g.Source }
    $w = & where.exe npm.cmd 2>$null | Select-Object -First 1
    if ($w -and (Test-Path $w)) { return $w.Trim() }
    throw "npm.cmd not found on PATH."
}

function Add-CaddyToPathIfNeeded {
    if (Get-Command caddy -ErrorAction SilentlyContinue) { return }
    $candidates = @(
        (Join-Path $env:ProgramFiles "Caddy\caddy.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Caddy\caddy.exe")
    )
    $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetRoot) {
        Get-ChildItem -Path $wingetRoot -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*Caddy*' } | ForEach-Object {
            $found = Get-ChildItem -Path $_.FullName -Filter "caddy.exe" -Recurse -Depth 6 -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { $candidates += $found.FullName }
        }
    }
    foreach ($exe in $candidates) {
        if ($exe -and (Test-Path -LiteralPath $exe)) {
            $dir = Split-Path -Parent $exe
            $env:Path = "$dir;$env:Path"
            Write-Host "[wire] using Caddy at: $exe" -ForegroundColor DarkGray
            return
        }
    }
}

Add-CaddyToPathIfNeeded
if (-not (Get-Command caddy -ErrorAction SilentlyContinue)) {
    Write-Host "Install Caddy: winget install CaddyServer.Caddy" -ForegroundColor Yellow
    exit 1
}

foreach ($p in @(8765, 8042, 8043, 8055)) {
    if (-not (Test-PortListen $p)) {
        Write-Warning "[wire] nothing listening on port $p - start t54:seller, api:402, x402:seller, marketplace:serve first."
    }
}

if (-not (Test-PortListen 9080)) {
    Write-Host "[wire] starting Caddy unified proxy on :9080 (logs: logs/wire-unified-caddy.log)"
    $npm = Get-NpmCmdPath
    $out = Join-Path $logDir "wire-unified-caddy.log"
    $err = Join-Path $logDir "wire-unified-caddy.err.log"
    $cmdLine = "cd /d `"$Root`" && `"$npm`" run proxy:unified"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmdLine) -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err
    Start-Sleep -Seconds 4
    if (-not (Test-PortListen 9080)) {
        Write-Error "[wire] Caddy did not bind :9080 - see $err"
        exit 1
    }
}
else {
    Write-Host "[wire] :9080 already listening (Caddy assumed running)."
}

Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[wire] stopped ngrok PID $($_.Id)"
}
Start-Sleep -Seconds 2

$exe = Join-Path $env:LOCALAPPDATA "Programs\Ngrok\ngrok.exe"
if (-not (Test-Path $exe)) {
    $exe = Join-Path $Root ".tools\ngrok\ngrok.exe"
}
if (-not (Test-Path $exe)) {
    Write-Error "ngrok.exe not found. Run: scripts\install-ngrok-global.ps1"
    exit 1
}

$globalNgrok = Join-Path $env:LOCALAPPDATA "ngrok\ngrok.yml"
if (-not (Test-Path $globalNgrok)) {
    $globalNgrok = Join-Path $env:USERPROFILE ".ngrok2\ngrok.yml"
}
if (-not (Test-Path $globalNgrok)) {
    Write-Error "No ngrok authtoken config at $env:LOCALAPPDATA\ngrok\ngrok.yml - see https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
}

$cfg = Join-Path $Root "scripts\ngrok-dual-stack.yml"
$nOut = Join-Path $logDir "wire-unified-ngrok.log"
$nErr = Join-Path $logDir "wire-unified-ngrok.err.log"
Write-Host "[wire] starting ngrok (t54 + x402 + unified tunnels) -> logs/wire-unified-ngrok.log"
Start-Process -FilePath $exe -ArgumentList @("start", "--all", "--config", $globalNgrok, "--config", $cfg) -WorkingDirectory $Root -WindowStyle Hidden `
    -RedirectStandardOutput $nOut -RedirectStandardError $nErr

$deadline = (Get-Date).AddSeconds($NgrokApiWaitSeconds)
$apiOk = $false
while ((Get-Date) -lt $deadline) {
    try {
        $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
        if ($t.tunnels -and @($t.tunnels).Count -ge 1) {
            $apiOk = $true
            break
        }
    }
    catch {}
    Start-Sleep -Seconds 1
}

if (-not $apiOk) {
    Write-Warning "[wire] ngrok API not ready within ${NgrokApiWaitSeconds}s - check $nErr"
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "python" }

& $py "$Root\scripts\sync_t54_env_from_ngrok.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "[wire] sync T54 failed (exit $LASTEXITCODE)" }

& $py "$Root\scripts\sync_x402_env_from_ngrok.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "[wire] sync x402 failed (exit $LASTEXITCODE)" }

& $py "$Root\scripts\reload_t54_discovery.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "[wire] reload discovery failed (exit $LASTEXITCODE)" }

& $py "$Root\scripts\sync_endpoints_json.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "[wire] sync_endpoints_json.py failed (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "[wire] Public URLs (sync scripts prefer the unified :9080 tunnel when present):"
try {
    $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $t.tunnels | ForEach-Object {
        $addr = ""
        if ($_.config) { $addr = $_.config.addr }
        Write-Host "  $($_.name)  $($_.public_url)  ->  $addr"
    }
}
catch {
    Write-Host "  (could not list tunnels: $_)"
}

Write-Host ""
Write-Host "[wire] Done. T54 buyers use base ending in /t54 ; Base x402 uses /x402/... ; Celo native uses /celo/query ; marketplace uses origin without path prefix."
Write-Host "[wire] Docs: scripts/reverse-proxy/README.md"
