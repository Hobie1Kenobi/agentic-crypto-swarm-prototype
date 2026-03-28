# Reset 24h soak artifacts for a clean retry
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$reportDir = Join-Path $root "artifacts\reports"
$artifacts = @(
    "continuous_multi_rail_24h_cycle_log.json",
    "continuous_multi_rail_24h_cycle_log.md",
    "continuous_multi_rail_24h_failures.json",
    "continuous_multi_rail_24h_6h_checkpoint.md",
    "continuous_multi_rail_24h_12h_checkpoint.md",
    "continuous_multi_rail_24h_18h_checkpoint.md",
    "continuous_multi_rail_24h_report.json",
    "continuous_multi_rail_24h_report.md",
    "continuous_multi_rail_metrics_summary.md"
)

foreach ($f in $artifacts) {
    $p = Join-Path $reportDir $f
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Host "Removed: $f"
    }
}

$traceDir = Join-Path $root "artifacts\traces\soak-24h"
if (Test-Path $traceDir) {
    Remove-Item $traceDir -Recurse -Force
    Write-Host "Removed: artifacts/traces/soak-24h/"
}

Write-Host ""
Write-Host "24h soak artifacts reset. Ready for clean retry."
