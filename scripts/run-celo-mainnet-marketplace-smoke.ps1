# One-shot live smoke: private ComputeMarketplace task lifecycle on Celo mainnet (42220).
# Prereqs: contracts deployed; npm run fetch-addresses; role keys funded with real CELO; .env with CHAIN_ID=42220.
# Does NOT deploy. For deploy first: set CHAIN_ID=42220 and CELO_MAINNET_RPC_URL, then .\scripts\deploy.ps1 --broadcast
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"
if (-not (Test-Path $envPath)) {
    Write-Error "Missing .env at $envPath. Copy from .env.example and set mainnet values."
    exit 1
}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($k, $v, "Process")
    }
}

$mainnetId = 42220
if ([int]$env:CHAIN_ID -ne $mainnetId) {
    Write-Error "CHAIN_ID must be $mainnetId (celo-mainnet). Current: $($env:CHAIN_ID)"
    exit 1
}
$rpc = $env:RPC_URL
if (-not $rpc) { $rpc = $env:CELO_MAINNET_RPC_URL }
if (-not $rpc) {
    Write-Error "Set RPC_URL or CELO_MAINNET_RPC_URL to a reliable Celo mainnet HTTPS endpoint."
    exit 1
}
$env:RPC_URL = $rpc
if (-not $env:CHAIN_NAME) { $env:CHAIN_NAME = "celo-mainnet" }
if (-not $env:EXPLORER_URL) { $env:EXPLORER_URL = "https://explorer.celo.org" }
if (-not $env:PRIVATE_CHAIN_ID) { $env:PRIVATE_CHAIN_ID = [string]$mainnetId }
if (-not $env:PRIVATE_CHAIN_NAME) { $env:PRIVATE_CHAIN_NAME = "celo-mainnet" }
if (-not $env:PRIVATE_RPC_URL) { $env:PRIVATE_RPC_URL = $rpc }

$required = @(
    "COMPUTE_MARKETPLACE_ADDRESS",
    "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR_PRIVATE_KEY"
)
foreach ($k in $required) {
    $v = [Environment]::GetEnvironmentVariable($k, "Process")
    if (-not $v -or $v -match "your_") {
        Write-Error "Set $k in .env (see docs/PRODUCTION-READINESS.md)."
        exit 1
    }
}

Write-Host "Running task_market_demo on Celo mainnet (42220). Outputs: celo_mainnet_task_market_report.json / .md"
Push-Location (Join-Path $root "packages\agents")
try {
    python -c "from task_market_demo import run_task_market_demo; run_task_market_demo()"
    if ($LASTEXITCODE -ne 0) { throw "task_market_demo failed" }
} finally {
    Pop-Location
}
