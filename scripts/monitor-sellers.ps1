# One-shot health check for both sellers (api_402 :8042, api_seller_x402 :8043).
# Run on a schedule:  schtasks /Create ...  or  while ($true) { .\scripts\monitor-sellers.ps1; Start-Sleep 60 }
param(
    [string]$Root = (Split-Path $PSScriptRoot -Parent)
)
$ErrorActionPreference = "Stop"
$ok = $true
foreach ($port in @(8042, 8043)) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $c) { Write-Host "FAIL: nothing listening on $port"; $ok = $false; continue }
    Write-Host "OK listen :$port PID=$($c[0].OwningProcess)"
}
try {
    $h2 = Invoke-WebRequest -Uri "http://127.0.0.1:8042/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "api_402 health:" $h2.Content
} catch { Write-Host "FAIL api_402 health:" $_.Exception.Message; $ok = $false }
try {
    $h3 = Invoke-WebRequest -Uri "http://127.0.0.1:8043/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "api_seller_x402 health:" $h3.Content
} catch { Write-Host "FAIL api_seller_x402 health:" $_.Exception.Message; $ok = $false }
$env:PYTHONPATH = Join-Path $Root "packages\agents"
$p = & python (Join-Path $Root "scripts\probe-x402-seller.py") 2>&1
Write-Host $p
if ($LASTEXITCODE -ne 0) { $ok = $false }
if (-not $ok) { exit 1 }
Write-Host "--- all checks passed ---"
exit 0
