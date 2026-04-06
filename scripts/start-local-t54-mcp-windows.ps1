# Open two PowerShell windows: T54 seller 24h daemon + MCP SSE (127.0.0.1:9050).
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local-t54-mcp-windows.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
Write-Host "Launching from: $root"

$t1 = "Set-Location -LiteralPath '$root'; try { `$Host.UI.RawUI.WindowTitle = 'Swarm: T54 seller (24h daemon)' } catch {}; npm run t54:seller:daemon"
$t2 = "Set-Location -LiteralPath '$root'; try { `$Host.UI.RawUI.WindowTitle = 'Swarm: MCP SSE (9050)' } catch {}; npm run mcp:t54:sse"

Start-Process powershell.exe -ArgumentList @("-NoExit", "-NoProfile", "-Command", $t1)
Start-Sleep -Milliseconds 400
Start-Process powershell.exe -ArgumentList @("-NoExit", "-NoProfile", "-Command", $t2)
Write-Host "Opened: (1) T54 seller 24h daemon  (2) MCP SSE. Close windows to stop."
