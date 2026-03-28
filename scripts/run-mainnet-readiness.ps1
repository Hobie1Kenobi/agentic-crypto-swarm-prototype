# Run the suggested mainnet sequence: preflight -> (optional) deploy -> fetch-addresses -> (optional) marketplace smoke.
# Real deploy and smoke spend CELO. Defaults: dry-run deploy, no smoke (use -WithSmoke after broadcast + funding).
param(
    [switch]$DryRunDeploy,
    [switch]$Broadcast,
    [switch]$SkipDeploy,
    [switch]$SkipFetch,
    [switch]$WithSmoke,
    [switch]$StrictPreflight
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if ($DryRunDeploy -and $Broadcast) {
    Write-Error "Use either -DryRunDeploy or -Broadcast, not both."
    exit 1
}
if (-not $DryRunDeploy -and -not $Broadcast -and -not $SkipDeploy) {
    $DryRunDeploy = $true
}

Write-Host "=== 1. Mainnet preflight ===" -ForegroundColor Cyan
& (Join-Path $root "scripts\mainnet-preflight.ps1") -Strict:$StrictPreflight
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDeploy) {
    if ($Broadcast) {
        Write-Host ""
        Write-Host "You are about to BROADCAST a real mainnet deployment (CELO gas)." -ForegroundColor Yellow
        $confirm = Read-Host "Type YES to continue"
        if ($confirm -ne "YES") {
            Write-Host "Aborted."
            exit 1
        }
    }
    Write-Host ""
    Write-Host "=== 2. Forge deploy $(if ($Broadcast) { '(BROADCAST)' } else { '(dry-run)' }) ===" -ForegroundColor Cyan
    if ($Broadcast) {
        & (Join-Path $root "scripts\deploy.ps1") --broadcast
    } else {
        & (Join-Path $root "scripts\deploy.ps1")
    }
    if ($LASTEXITCODE -ne 0) { throw "deploy.ps1 failed" }
}

if (-not $SkipFetch) {
    Write-Host ""
    Write-Host "=== 3. Fetch and save addresses to .env ===" -ForegroundColor Cyan
    & (Join-Path $root "scripts\fetch-and-save-addresses.ps1")
    if ($LASTEXITCODE -ne 0) { throw "fetch-and-save-addresses failed" }
}

if ($WithSmoke) {
    Write-Host ""
    Write-Host "=== 4. Marketplace smoke (task_market_demo, spends CELO) ===" -ForegroundColor Cyan
    Write-Host "Confirms before submitting transactions." -ForegroundColor Yellow
    $confirm = Read-Host "Type YES to run marketplace smoke"
    if ($confirm -ne "YES") {
        Write-Host "Skipped smoke. Run later: npm run mainnet:marketplace-smoke"
    } else {
        & (Join-Path $root "scripts\run-celo-mainnet-marketplace-smoke.ps1")
        if ($LASTEXITCODE -ne 0) { throw "marketplace smoke failed" }
    }
}

Write-Host ""
Write-Host "Mainnet readiness sequence finished." -ForegroundColor Green
if ($DryRunDeploy -and -not $Broadcast) {
    Write-Host "Next: fund deployer with CELO, then: npm run mainnet:readiness -- -Broadcast"
    Write-Host "After deploy + fetch + funding agents: npm run mainnet:readiness -- -SkipDeploy -SkipFetch -WithSmoke"
}
