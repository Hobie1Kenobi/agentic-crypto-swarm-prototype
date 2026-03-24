$ErrorActionPreference = "Continue"
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "SwarmEconomy-T54-Stack.lnk"
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host "Removed: $lnk"
} else {
    Write-Host "No shortcut at $lnk"
}
