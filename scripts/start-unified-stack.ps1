# Start full unified stack on Windows: T54 seller :8765, x402 seller :8043, Celo x402 seller :8044, marketplace :8055,
# Caddy :9080, ngrok dual config (t54 + x402 + unified). Uses cmd.exe + npm.cmd (reliable; Start-Process npm is not).
# After ngrok is up: sync_t54 + sync_x402 write public URLs to .env, then sellers restart so uvicorn loads them
# (full start always restarts sellers; -Ensure restarts only if T54/X402 URL lines changed).
#
# -Ensure: idempotent full start used by the logon task - starts every component whose port is down, skips ones
# already listening (safe to run twice; never stops running processes). Logs to logs/unified-autostart.log.
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
    foreach ($port in @(8765, 8042, 8043, 8044, 8055)) {
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
    Write-Host "[unified-stack] starting api:402 (Celo native) -> logs/unified-stack-celo-402.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "api:402" -LogBaseName "unified-stack-celo-402"
    Start-Sleep -Seconds 2
    Write-Host "[unified-stack] starting x402:seller -> logs/unified-stack-x402-seller.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "x402:seller" -LogBaseName "unified-stack-x402-seller"
    Start-Sleep -Seconds 2
    Write-Host "[unified-stack] starting x402:seller:celo -> logs/unified-stack-celo-x402-seller.log"
    Start-NpmRunDetached -NpmCmd $NpmCmd -ScriptName "x402:seller:celo" -LogBaseName "unified-stack-celo-x402-seller"
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

$autoLog = Join-Path $logDir "unified-autostart.log"
function Write-AutoLog([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$(if ($Ensure) {'ensure'} else {'full'})] $msg"
    Add-Content -LiteralPath $autoLog -Value $line
    Write-Host "[unified-stack] $msg"
}
Write-AutoLog "run begin (pid $PID)"

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
    Write-AutoLog "FAILED: caddy not found on PATH"
    Write-Host "Caddy not found on PATH. Install: winget install CaddyServer.Caddy" -ForegroundColor Yellow
    Write-Host "Then sign out/in or add the Caddy folder to your user PATH, or re-run this script (it also searches WinGet package dirs)." -ForegroundColor Yellow
    exit 1
}

if ($Ensure) {
    # Idempotent full start: launch every component whose port is not already listening.
    $components = @(
        @{ Port = 8765; Script = "t54:seller";              Log = "unified-stack-t54-seller";        Wait = 2 },
        @{ Port = 8042; Script = "api:402";                 Log = "unified-stack-celo-402";          Wait = 2 },
        @{ Port = 8043; Script = "x402:seller";             Log = "unified-stack-x402-seller";       Wait = 2 },
        @{ Port = 8044; Script = "x402:seller:celo";        Log = "unified-stack-celo-x402-seller";  Wait = 2 },
        @{ Port = 8055; Script = "marketplace:serve";       Log = "unified-stack-marketplace";       Wait = 6 },
        @{ Port = 9051; Script = "mcp:t54:sse";             Log = "unified-stack-mcp-sse";           Wait = 1 },
        @{ Port = 9052; Script = "mcp:t54:streamable-http"; Log = "unified-stack-mcp-streamable";    Wait = 1 },
        @{ Port = 9080; Script = "proxy:unified";           Log = "unified-stack-caddy";             Wait = 3 },
        @{ Port = 4040; Script = "ngrok:dual";              Log = "unified-stack-ngrok";             Wait = 0 }
    )
    foreach ($c in $components) {
        if (Test-PortListen $c.Port) {
            Write-AutoLog ("skipped " + $c.Script + " (:" + $c.Port + " already listening)")
            continue
        }
        try {
            Start-NpmRunDetached -NpmCmd $npm -ScriptName $c.Script -LogBaseName $c.Log
            Write-AutoLog ("started " + $c.Script + " (:" + $c.Port + ") -> logs/" + $c.Log + ".log")
        } catch {
            Write-AutoLog ("FAILED to start " + $c.Script + " (:" + $c.Port + "): " + $_)
        }
        if ($c.Wait -gt 0) { Start-Sleep -Seconds $c.Wait }
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
    & $py "$Root\scripts\apply_public_api_origin.py"
    $prodUrls = ($LASTEXITCODE -eq 2)
    if ($prodUrls) {
        Write-Host '[unified-stack] PUBLIC_API_ORIGIN set in .env - skipped ngrok URL sync (production-cohesive URLs)'
    } else {
        & $py "$Root\scripts\sync_t54_env_from_ngrok.py"
        if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync T54 exited $LASTEXITCODE" }
        & $py "$Root\scripts\sync_x402_env_from_ngrok.py"
        if ($LASTEXITCODE -ne 0) { Write-Host "[unified-stack] sync x402 exited $LASTEXITCODE" }
    }
    $fpAfter = Get-EnvPublicUrlFingerprint
    $urlsChanged = $fpBefore -ne $fpAfter
    $doSellerRestart = (-not $Ensure) -or $urlsChanged
    if ($doSellerRestart) {
        if ($Ensure -and $urlsChanged) {
            Write-Host "[unified-stack] public URLs in .env changed - restarting sellers to load new T54/X402 origins"
        } else {
            Write-Host "[unified-stack] restarting sellers (8765/8042/8043/8044/8055) so uvicorn loads synced public URLs from .env"
        }
        Stop-UnifiedSellersOnly
        Start-Sleep -Seconds 2
        Start-UnifiedSellers -NpmCmd $npm
    } else {
        Write-Host "[unified-stack] sync ok; public URLs unchanged - skipping seller restart (watchdog-friendly)"
    }
}

foreach ($port in @(8765, 8042, 8043, 8044, 8055, 9051, 9052, 9080, 4040)) {
    if (Test-PortListen $port) {
        Write-AutoLog ('OK listen :' + $port)
    } else {
        Write-AutoLog ('FAILED: MISSING listener :' + $port + ' (see logs under ' + $logDir + ')')
    }
}

try {
    $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 5
    $t.tunnels | ForEach-Object { Write-Host ('[unified-stack] tunnel ' + $_.name + ' ' + $_.public_url) }
} catch {
    Write-Host ('[unified-stack] could not list tunnels: ' + $_)
}

Write-Host '[unified-stack] done. Caddy/ngrok left running. Full start reloads sellers after sync; ensure-mode only restarts sellers when T54/X402 URLs in .env change.'
