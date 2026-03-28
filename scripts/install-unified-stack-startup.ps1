# Install unified stack to run at Windows logon (Startup folder) — no Administrator required.
# Uses -Ensure so a second logon does not kill an already-running stack.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $Root "scripts\start-unified-stack.ps1"
$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "SwarmEconomy-Unified-Stack.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut($lnkPath)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Ensure"
$sc.WorkingDirectory = $Root
$sc.Description = "Swarm Economy: T54 + x402 + marketplace + Caddy + ngrok"
$sc.Save()
Write-Host "Created Startup shortcut: $lnkPath"
Write-Host "Runs at every logon. For clean restart use: npm run stack:unified:start"
