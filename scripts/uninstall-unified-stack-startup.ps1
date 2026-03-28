$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "SwarmEconomy-Unified-Stack.lnk"
if (Test-Path $lnkPath) {
    Remove-Item -LiteralPath $lnkPath -Force
    Write-Host "Removed: $lnkPath"
} else {
    Write-Host "No shortcut at $lnkPath"
}
