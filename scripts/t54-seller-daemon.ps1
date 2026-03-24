# Restart loop for the T54 XRPL seller (npm run t54:seller). Use behind a stable public URL (ngrok, etc.).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
while ($true) {
    Write-Host "[t54 daemon] starting t54:seller..."
    npm run t54:seller
    Write-Host "[t54 daemon] exited; restarting in 5s..."
    Start-Sleep -Seconds 5
}
