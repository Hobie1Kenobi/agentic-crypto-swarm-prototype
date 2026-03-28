# Register Windows Scheduled Tasks (current user): unified stack at logon + ensure every 15 minutes.
# Run: powershell -ExecutionPolicy Bypass -File scripts/install-unified-stack-task.ps1
# Uninstall: powershell -ExecutionPolicy Bypass -File scripts/uninstall-unified-stack-task.ps1
#
# If you still have SwarmEconomy-T54-* tasks from install-t54-stack-task.ps1, uninstall those first
# to avoid two ngrok agents fighting for :4040.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $Root "scripts\start-unified-stack.ps1"
if (-not (Test-Path $startScript)) {
    throw "Missing $startScript"
}

$taskName = "SwarmEconomy-Unified-Stack"
$taskNameWatch = "SwarmEconomy-Unified-Watchdog"

$argLogon = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Ensure"
$argWatch = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`" -Ensure"
$actionLogon = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLogon
$actionWatch = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argWatch

$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$startAt = (Get-Date).AddMinutes(1)
$triggerRepeat = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $taskName -Action $actionLogon -Trigger $triggerLogon -Settings $settings -Principal $principal -Force `
        -Description "Start Swarm unified stack (T54 + x402 + marketplace + Caddy + ngrok) at logon if ports are free." | Out-Null

    Register-ScheduledTask -TaskName $taskNameWatch -Action $actionWatch -Trigger $triggerRepeat -Settings $settings -Principal $principal -Force `
        -Description "Ensure unified stack is running every 15 minutes (idempotent; does not stop healthy processes)." | Out-Null
} catch {
    Write-Host "Register-ScheduledTask failed: $_"
    Write-Host "Try: Run PowerShell as Administrator and re-run this script."
    Write-Host "Or use no-admin logon startup: npm run stack:unified:install-startup"
    exit 1
}

Write-Host "Registered tasks:"
Write-Host "  - $taskName (At logon, -Ensure)"
Write-Host "  - $taskNameWatch (every 15 min, -Ensure)"
Write-Host "Run now: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "Logs: $Root\logs\"
