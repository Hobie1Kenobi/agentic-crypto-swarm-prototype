$ErrorActionPreference = "Continue"
@("SwarmEconomy-T54-Stack", "SwarmEconomy-T54-Watchdog") | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_ -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $_"
}
