# Start T54 seller (uvicorn) + ngrok detached, then sync .env from ngrok API.
# Idempotent: skips seller if port is listening; skips ngrok if tunnel API already has tunnels.
# Logs: logs/t54-seller.log, logs/t54-ngrok.log
param(
    [int]$Port = 8765
)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-PortListen([int]$p) {
    return $null -ne (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Get-NgrokExe {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ngrok\ngrok.exe"),
        (Join-Path $Root ".tools\ngrok\ngrok.exe"),
        (Join-Path $Root "scripts\ngrok.cmd")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

# --- Seller ---
if (Test-PortListen $Port) {
    Write-Host "[t54-stack] Port $Port already listening - seller assumed running."
} else {
    $out = Join-Path $logDir "t54-seller.log"
    $err = Join-Path $logDir "t54-seller.err.log"
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = "python" }
    Start-Process -FilePath $py -ArgumentList "`"$Root\scripts\t54_seller_server.py`"" -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err
    Start-Sleep -Seconds 3
    if (-not (Test-PortListen $Port)) {
        Write-Host "[t54-stack] WARNING: Seller may have failed to bind $Port - see $err"
    } else {
        Write-Host "[t54-stack] Seller started (logs: $out)"
    }
}

# --- ngrok ---
$ngrokOk = $false
try {
    $t = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 3
    if ($t.tunnels -and $t.tunnels.Count -gt 0) {
        Write-Host "[t54-stack] ngrok already has a tunnel - skipping ngrok start."
        $ngrokOk = $true
    }
} catch {
    $ngrokOk = $false
}

if (-not $ngrokOk) {
    $exe = Get-NgrokExe
    if (-not $exe) {
        Write-Host "[t54-stack] ERROR: ngrok not found. Run: scripts\install-ngrok-global.ps1"
        exit 1
    }
    $nOut = Join-Path $logDir "t54-ngrok.log"
    $nErr = Join-Path $logDir "t54-ngrok.err.log"
    if ($exe -like "*.cmd") {
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", "`"$exe`" http $Port") -WindowStyle Hidden -RedirectStandardOutput $nOut -RedirectStandardError $nErr
    } else {
        Start-Process -FilePath $exe -ArgumentList @("http", "$Port") -WindowStyle Hidden -RedirectStandardOutput $nOut -RedirectStandardError $nErr
    }
    Start-Sleep -Seconds 5
    Write-Host "[t54-stack] ngrok started (logs: $nOut)"
}

# --- Sync .env ---
try {
    & python "$Root\scripts\sync_t54_env_from_ngrok.py"
} catch {
    Write-Host "[t54-stack] sync_t54_env_from_ngrok.py failed (ngrok may still be starting): $_"
}

Write-Host "[t54-stack] Done. Health: http://127.0.0.1:$Port/health  ngrok UI: http://127.0.0.1:4040"
