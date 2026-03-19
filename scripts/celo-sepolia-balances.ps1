# Print Celo Sepolia balances for key addresses from .env. Requires: .env with addresses, Foundry (cast).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"
if (-not (Test-Path $envPath)) {
    Write-Error ".env not found. Copy .env.example to .env and set addresses."
    exit 1
}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}
$rpc = $env:RPC_URL
if (-not $rpc) { $rpc = $env:CELO_SEPOLIA_RPC_URL }
if (-not $rpc) { $rpc = "https://rpc.ankr.com/celo_sepolia" }
$chainId = $env:CHAIN_ID
if (-not $chainId -or [int]$chainId -ne 11142220) {
    Write-Host "CHAIN_ID is not 11142220; ensure you are on Celo Sepolia."
}
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }

$addrs = @(
    @{ Name = "ROOT_STRATEGIST_ADDRESS"; Desc = "Root Strategist (payer)" },
    @{ Name = "FINANCE_DISTRIBUTOR_ADDRESS"; Desc = "Finance Distributor" },
    @{ Name = "REVENUE_SERVICE_ADDRESS"; Desc = "Revenue contract" },
    @{ Name = "BENEFICIARY_ADDRESS"; Desc = "Beneficiary" }
)
Write-Host "Celo Sepolia balances (RPC: $rpc)"
Write-Host ""
foreach ($a in $addrs) {
    $addr = [Environment]::GetEnvironmentVariable($a.Name, "Process")
    if (-not $addr -or $addr -match "0x0+$" -or $addr -match "your_") { continue }
    try {
        $bal = & cast balance $addr --rpc-url $rpc 2>&1
        $eth = [decimal]$bal / 1e18
        Write-Host "$($a.Desc) ($($a.Name)): $eth CELO"
    } catch {
        Write-Host "$($a.Desc) ($($a.Name)): (error)"
    }
}
Write-Host ""
Write-Host "Explorer: https://celo-sepolia.blockscout.com"
