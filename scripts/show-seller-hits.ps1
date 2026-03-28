# Show request hit count and last lines from SELLER_ACCESS_LOG (JSONL).
param(
    [string]$LogPath = $env:SELLER_ACCESS_LOG,
    [int]$Tail = 15
)
$Root = Split-Path $PSScriptRoot -Parent
if (-not $LogPath) {
    $LogPath = Join-Path $Root "seller_access.log"
}
if (-not (Test-Path $LogPath)) {
    Write-Host "No log file at: $LogPath"
    Write-Host "Set SELLER_ACCESS_LOG in .env and restart both sellers, or export SELLER_ACCESS_LOG before starting uvicorn."
    Write-Host "Past runs without logging cannot be recovered."
    exit 1
}
$lines = Get-Content $LogPath -ErrorAction SilentlyContinue
$count = ($lines | Measure-Object -Line).Lines
Write-Host "Total requests logged: $count"
Write-Host "--- last $Tail lines ---"
Get-Content $LogPath -Tail $Tail
