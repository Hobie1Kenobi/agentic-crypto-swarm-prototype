# Deploy DAO (token, timelock, governor) and transfer AgentRevenueService ownership to Timelock.
# Requires: REVENUE_SERVICE_ADDRESS, FINANCE_DISTRIBUTOR_ADDRESS, PRIVATE_KEY in .env. Run after .\scripts\deploy.ps1 --broadcast
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
if (Test-Path (Join-Path $root ".env.local")) {
    Get-Content (Join-Path $root ".env.local") | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($k, $v, "Process")
        }
    }
}
$chainId = if ($env:CHAIN_ID) { [int]$env:CHAIN_ID } else { 11142220 }
$rpc = $env:RPC_URL
if (-not $rpc) {
    switch ($chainId) {
        31337 { $rpc = "http://127.0.0.1:8545" }
        11142220 { $rpc = $env:CELO_SEPOLIA_RPC_URL; if (-not $rpc) { $rpc = "https://rpc.ankr.com/celo_sepolia" } }
        42220 { $rpc = $env:CELO_MAINNET_RPC_URL; if (-not $rpc) { $rpc = "https://rpc.ankr.com/celo" } }
        84532 { if ($env:ALCHEMY_API_KEY) { $rpc = "https://base-sepolia.g.alchemy.com/v2/$($env:ALCHEMY_API_KEY)" }; if (-not $rpc) { $rpc = "https://sepolia.base.org" } }
        default { $rpc = "https://rpc.ankr.com/celo_sepolia" }
    }
}
if (-not $env:REVENUE_SERVICE_ADDRESS) { Write-Error "Set REVENUE_SERVICE_ADDRESS in .env (run deploy.ps1 --broadcast first)" }
if (-not $env:PRIVATE_KEY) { Write-Error "Set PRIVATE_KEY in .env for broadcast" }
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }
$env:FOUNDRY_DISABLE_NIGHTLY_WARNING = "1"
Push-Location $root
try {
    forge script script/DeployDAO.s.sol --rpc-url $rpc --broadcast --private-key $env:PRIVATE_KEY
} finally {
    Pop-Location
}
