$ErrorActionPreference = "Continue"
@("SwarmEconomy-Unified-Stack", "SwarmEconomy-Unified-Watchdog") | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_ -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $_"
}
