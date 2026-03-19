# Celo Sepolia E2E: deploy contracts, save addresses, then run orchestration.
# No bundler required; uses signer-based executor (ROOT_STRATEGIST_PRIVATE_KEY).
# Prereqs: .env with PRIVATE_KEY, FINANCE_DISTRIBUTOR_ADDRESS (from npm run create-accounts); fund deployer with Celo Sepolia faucet.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($k, $v, "Process")
        }
    }
}

$chainId = 11142220
if ($env:CHAIN_ID -and [int]$env:CHAIN_ID -ne $chainId) {
    Write-Host "CHAIN_ID is $($env:CHAIN_ID); setting to $chainId for Celo Sepolia E2E."
}
$env:CHAIN_ID = [string]$chainId
if (-not $env:RPC_URL) {
    $env:RPC_URL = $env:CELO_SEPOLIA_RPC_URL
    if (-not $env:RPC_URL) { $env:RPC_URL = "https://rpc.ankr.com/celo_sepolia" }
}

if (-not $env:PRIVATE_KEY -or $env:PRIVATE_KEY -match "your_") {
    Write-Error "Set PRIVATE_KEY in .env (deployer EOA with Celo Sepolia CELO). Run: npm run create-accounts"
    exit 1
}
if (-not $env:FINANCE_DISTRIBUTOR_ADDRESS -or $env:FINANCE_DISTRIBUTOR_ADDRESS -match "your_") {
    Write-Error "Set FINANCE_DISTRIBUTOR_ADDRESS in .env. Run: npm run create-accounts and copy FINANCE_DISTRIBUTOR_ADDRESS"
    exit 1
}

$env:ETH_GAS_PRICE = if ($env:ETH_GAS_PRICE) { $env:ETH_GAS_PRICE } else { "200gwei" }
$env:ETH_PRIORITY_GAS_PRICE = if ($env:ETH_PRIORITY_GAS_PRICE) { $env:ETH_PRIORITY_GAS_PRICE } else { "2gwei" }

$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }

Push-Location $root
try {
    Write-Host "Deploying to Celo Sepolia (chain $chainId)..."
    & (Join-Path $root "scripts\deploy.ps1") --broadcast
    if ($LASTEXITCODE -ne 0) { throw "Deploy failed" }

    Write-Host "Saving deployed addresses to .env..."
    & (Join-Path $root "scripts\fetch-and-save-addresses.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Fetch addresses failed" }

    $rootStrategist = $env:ROOT_STRATEGIST_ADDRESS
    if (-not $rootStrategist) {
        $line = Get-Content $envPath | Where-Object { $_ -match '^ROOT_STRATEGIST_ADDRESS=' }
        if ($line) { $rootStrategist = ($line -split "=", 2)[1].Trim() }
    }
    Write-Host ""
    Write-Host "=== Celo Sepolia E2E: next steps ==="
    Write-Host "1. Fund the payer (Root Strategist) with testnet CELO:"
    Write-Host "   Faucet: https://faucet.celo.org/celo-sepolia"
    if ($rootStrategist) { Write-Host "   Address: $rootStrategist" }
    Write-Host "2. Run full orchestration (strategist -> simulation -> finance):"
    Write-Host "   npm run orchestrate"
    Write-Host "   Or simulation only: npm run simulation"
    Write-Host "3. Check tx hashes: simulation_log.txt and Celo Sepolia explorer: https://celo-sepolia.blockscout.com"
} finally {
    Pop-Location
}
