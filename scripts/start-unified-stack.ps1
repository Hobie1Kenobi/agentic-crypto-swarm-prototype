# Start full unified stack on Windows: T54 seller :8765, x402 seller :8043, marketplace :8055,
# Caddy :9080, ngrok dual config (t54 + x402 + unified). Uses cmd.exe + npm.cmd (reliable; Start-Process npm is not).
# After ngrok is up: sync_t54 + sync_x402 write public URLs to .env, then sellers restart so uvicorn loads them
# (full start always restarts sellers; -Ensure restarts only if T54/X402 URL lines changed - avoids watchdog flapping).
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

function Stop-UnifiedSellersOnly {
    foreach ($port in @(8765, 8043, 8055)) {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conn) {
            if (-not $c.OwningProcess) { continue }
            try {
                Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
                Write-Host "[unified-stack] stopped seller PID $($c.OwningProcess) (port $port)"
            } catch {
                Write-Host "[unified-stack] could not stop PID $($c.OwningProcess) on $port : $_"
            }
        }
    }
}

function Start-UnifiedSellers {
    param([string]$NpmCmd)
    Write-Host "[unified-stack] starting t54:seller -> logs/unified-stack-t54-seller.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "t54:seller" -LogBaseName "unified-stack-t54-seller"
    Start-Sleep -Seconds 2
    Write-Host "[unified-stack] starting x402:seller -> logs/unified-stack-x402-seller.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "x402:seller" -LogBaseName "unified-stack-x402-seller"
    Start-Sleep -Seconds 2
    Write-Host "[unified-stack] starting marketplace:serve -> logs/unified-stack-marketplace.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "marketplace:serve" -LogBaseName "unified-stack-marketplace"
    Start-Sleep -Seconds 6
}

function Start-McpForUnifiedProxy {
    param([string]$NpmCmd)
    Write-Host "[unified-stack] starting mcp:t54:sse (9051) -> logs/unified-stack-mcp-sse.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "mcp:t54:sse" -LogBaseName "unified-stack-mcp-sse"
    Start-Sleep -Seconds 1
    Write-Host "[unified-stack] starting mcp:t54:streamable-http (9052, Smithery /mcp) -> logs/unified-stack-mcp-streamable.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "mcp:t54:streamable-http" -LogBaseName "unified-stack-mcp-streamable"
    Start-Sleep -Seconds 1
}

function Get-EnvPublicUrlFingerprint {
    $path = Join-Path $Root ".env"
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    $raw = Get-Content -LiteralPath $path -Raw
    $t54 = ""
    $x402 = ""
    if ($raw -match '(?m)^T54_SELLER_PUBLIC_BASE_URL=(.*)$') { $t54 = $matches[1].Trim() }
    if ($raw -match '(?m)^X402_SELLER_PUBLIC_URL=(.*)$') { $x402 = $matches[1].Trim() }
    return "${t54}|${x402}"
}

$npm = Get-NpmCmdPath

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
            Write-Host "[unified-stack] using Caddy at: $exe" -ForegroundColor DarkGray
            return
        }
    }
}

Add-CaddyToPathIfNeeded
$caddy = Get-Command caddy -ErrorAction SilentlyContinue
if (-not $caddy) {
    Write-Host "Caddy not found on PATH. Install: winget install CaddyServer.Caddy" -ForegroundColor Yellow
    Write-Host "Then sign out/in or add the Caddy folder to your user PATH, or re-run this script (it also searches WinGet package dirs)." -ForegroundColor Yellow
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
    if (-not (Test-PortListen 9051)) {
        Write-Host "[unified-stack] ensure: starting mcp:t54:sse -> logs/unified-stack-mcp-sse.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "mcp:t54:sse" -LogBaseName "unified-stack-mcp-sse"
        Start-Sleep -Seconds 1
    }
    if (-not (Test-PortListen 9052)) {
        Write-Host "[unified-stack] ensure: starting mcp:t54:streamable-http -> logs/unified-stack-mcp-streamable.log"
        Start-NpmRunDetached -NpmCmd $npm -ScriptName "mcp:t54:streamable-http" -LogBaseName "unified-stack-mcp-streamable"
        Start-Sleep -Seconds 1
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

    Start-UnifiedSellers -NpmCmd $npm

    Start-McpForUnifiedProxy -NpmCmd $npm

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

if (-not $NoSync) {
    $fpBefore = Get-EnvPublicUrlFingerprint
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = "python" }
    & $py "$Root\scripts\sync_t54_env_from_ngrok.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync T54 exited $LASTEXITCODE" }
    & $py "$Root\scripts\sync_x402_env_from_ngrok.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync x402 exited $LASTEXITCODE" }
    $fpAfter = Get-EnvPublicUrlFingerprint
    $urlsChanged = $fpBefore -ne $fpAfter
    $doSellerRestart = (-not $Ensure) -or $urlsChanged
    if ($doSellerRestart) {
        if ($Ensure -and $urlsChanged) {
            Write-Host "[unified-stack] public URLs in .env changed - restarting sellers to load new T54/X402 origins"
        } else {
            Write-Host "[unified-stack] restarting sellers (8765/8043/8055) so uvicorn loads synced T54/X402 URLs from .env"
        }
        Stop-UnifiedSellersOnly
        Start-Sleep -Seconds 2
        Start-UnifiedSellers -NpmCmd $npm
    } else {
        Write-Host "[unified-stack] sync ok; public URLs unchanged - skipping seller restart (watchdog-friendly)"
    }
}

foreach ($port in @(8765, 8043, 8055, 9051, 9052, 9080, 4040)) {
    if (Test-PortListen $port) {
        Write-Host "[unified-stack] OK listen :$port"
    } else {
        Write-Host "[unified-stack] MISSING listener :$port (see logs under $logDir)"
    }
}

try {
    $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $t.tunnels | ForEach-Object { Write-Host "[unified-stack] tunnel $($_.name) $($_.public_url)" }
} catch {
    Write-Host "[unified-stack] could not list tunnels: $_"
}

Write-Host "[unified-stack] done. Caddy/ngrok left running. Full start reloads sellers after sync; ensure-mode only restarts sellers when T54/X402 URLs in .env change."
