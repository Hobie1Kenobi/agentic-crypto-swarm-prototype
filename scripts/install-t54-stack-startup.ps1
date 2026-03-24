# Install T54 stack to run at Windows logon (Startup folder) — no Administrator required.
# Starts seller + ngrok in the background (see start-t54-stack.ps1).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $Root "scripts\start-t54-stack.ps1"
$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "SwarmEconomy-T54-Stack.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut($lnkPath)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`""
$sc.WorkingDirectory = $Root
$sc.Description = "Swarm Economy: T54 seller + ngrok"
$sc.Save()
Write-Host "Created Startup shortcut: $lnkPath"
Write-Host "It runs on every logon. To run once now: powershell -ExecutionPolicy Bypass -File `"$startScript`""
