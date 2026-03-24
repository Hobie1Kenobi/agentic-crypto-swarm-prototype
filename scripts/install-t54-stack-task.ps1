# Register Windows Scheduled Tasks (current user): start T54 stack at logon + watchdog every 15 minutes.
# Run: powershell -ExecutionPolicy Bypass -File scripts/install-t54-stack-task.ps1
# Uninstall: powershell -ExecutionPolicy Bypass -File scripts/uninstall-t54-stack-task.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $Root "scripts\start-t54-stack.ps1"
if (-not (Test-Path $startScript)) {
    throw "Missing $startScript"
}

$taskName = "SwarmEconomy-T54-Stack"
$taskNameWatch = "SwarmEconomy-T54-Watchdog"

$arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg

# Logon: run once when user signs in
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Watchdog: every 15 minutes (idempotent restarts if something died)
$startAt = (Get-Date).AddMinutes(1)
$triggerRepeat = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggerLogon -Settings $settings -Principal $principal -Force `
        -Description "Start Swarm T54 seller + ngrok at logon (detached processes)." | Out-Null

    Register-ScheduledTask -TaskName $taskNameWatch -Action $action -Trigger $triggerRepeat -Settings $settings -Principal $principal -Force `
        -Description "Ensure T54 seller + ngrok are running every 15 minutes." | Out-Null
} catch {
    Write-Host "Register-ScheduledTask failed: $_"
    Write-Host "Try: Run PowerShell as Administrator and re-run this script, OR use: scripts\install-t54-stack-startup.ps1 (Startup folder, no admin)."
    exit 1
}

Write-Host "Registered tasks:"
Write-Host "  - $taskName (At logon)"
Write-Host "  - $taskNameWatch (every 15 min)"
Write-Host "Run now: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "Logs: $Root\logs\"
