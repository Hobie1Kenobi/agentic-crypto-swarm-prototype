# Stop processes bound to T54 seller port and local ngrok agent (best-effort).
param([int]$Port = 8765)
$ErrorActionPreference = "Continue"

$pids = @()
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conn) {
    if ($c.OwningProcess) { $pids += $c.OwningProcess }
}
$pids = $pids | Select-Object -Unique
foreach ($procId in $pids) {
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Stopped PID $procId (was listening on port $Port)"
    } catch {
        Write-Host "Could not stop PID $procId : $_"
    }
}

Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Stop-Process -Id $_.Id -Force
        Write-Host "Stopped ngrok PID $($_.Id)"
    } catch {}
}

Write-Host "stop-t54-stack: done."
