# Best-effort stop for unified local stack: ngrok, Caddy, listeners on T54/x402/marketplace/proxy ports.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot

Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force
        Write-Host "[unified-stack:stop] stopped ngrok PID $($_.Id)"
    } catch {}
}

Get-Process -Name "caddy" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force
        Write-Host "[unified-stack:stop] stopped caddy PID $($_.Id)"
    } catch {}
}

foreach ($port in @(8765, 8043, 8055, 9080)) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conn) {
        if (-not $c.OwningProcess) { continue }
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Host "[unified-stack:stop] stopped PID $($c.OwningProcess) (port $port)"
        } catch {
            Write-Host "[unified-stack:stop] could not stop PID $($c.OwningProcess) on $port : $_"
        }
    }
}

Write-Host "[unified-stack:stop] done."
