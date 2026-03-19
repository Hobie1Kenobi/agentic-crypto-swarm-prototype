# Deploy contracts to Anvil and write .env.local (no orchestration). For testing x402, marketplace, DAO.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }
$env:FOUNDRY_DISABLE_NIGHTLY_WARNING = "1"
$anvilKey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
$anvilAccount0 = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
$rpc = "http://127.0.0.1:8545"

function Test-AnvilRunning {
    try {
        $r = Invoke-WebRequest -Uri "$rpc" -Method POST -Body '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    } catch { return $false }
}

if (-not (Test-AnvilRunning)) {
    Write-Host "Starting Anvil..."
    Start-Process -FilePath "anvil" -ArgumentList "--port 8545" -WorkingDirectory $root -PassThru -WindowStyle Hidden | Out-Null
    $waited = 0
    while (-not (Test-AnvilRunning) -and $waited -lt 15) { Start-Sleep -Seconds 1; $waited++ }
    if (-not (Test-AnvilRunning)) { Write-Error "Anvil did not start"; exit 1 }
}
Write-Host "Anvil OK"

# Ensure forge script reads local Anvil-backed keys/addresses.
$env:RPC_URL = $rpc
$env:CHAIN_ID = "31337"
$env:PRIVATE_KEY = $anvilKey
$env:ROOT_STRATEGIST_PRIVATE_KEY = $anvilKey
$env:IP_GENERATOR_PRIVATE_KEY = $anvilKey
$env:DEPLOYER_PRIVATE_KEY = $anvilKey
$env:TREASURY_ADDRESS = $anvilAccount0
$env:FINANCE_DISTRIBUTOR_ADDRESS = $anvilAccount0
$env:FINANCE_DISTRIBUTOR_PRIVATE_KEY = $anvilKey
$env:BENEFICIARY_ADDRESS = $anvilAccount0

Push-Location $root
$forgeOut = & forge script script/Deploy.s.sol --rpc-url $rpc --broadcast --private-key $anvilKey 2>&1
$forgeOut | Out-Host
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }

$runLatest = Join-Path $root "broadcast\Deploy.s.sol\31337\run-latest.json"
if (-not (Test-Path $runLatest)) {
    $files = Get-ChildItem -Path (Join-Path $root "broadcast\Deploy.s.sol\31337") -Filter "run-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    if ($files) { $runLatest = $files[0].FullName }
}
$data = Get-Content $runLatest -Raw | ConvertFrom-Json
$revenueAddr = $null; $marketplaceAddr = $null
foreach ($tx in $data.transactions) {
    if ($tx.contractName -eq "AgentRevenueService") { $revenueAddr = $tx.contractAddress }
    if ($tx.contractName -eq "ComputeMarketplace") { $marketplaceAddr = $tx.contractAddress }
}
$revenueAddr = $revenueAddr.ToLower()
if ($marketplaceAddr) { $marketplaceAddr = $marketplaceAddr.ToLower() }

$envLocalLines = @(
    "RPC_URL=$rpc",
    "CHAIN_ID=31337",
    "REVENUE_SERVICE_ADDRESS=$revenueAddr",
    "PRIVATE_KEY=$anvilKey",
    "ROOT_STRATEGIST_PRIVATE_KEY=$anvilKey",
    "FINANCE_DISTRIBUTOR_ADDRESS=$anvilAccount0",
    "FINANCE_DISTRIBUTOR_PRIVATE_KEY=$anvilKey",
    "BENEFICIARY_ADDRESS=$anvilAccount0"
)
if ($marketplaceAddr) { $envLocalLines += "COMPUTE_MARKETPLACE_ADDRESS=$marketplaceAddr" }
$envLocalLines += "COMPUTE_MINER_URLS=http://127.0.0.1:8043"
$envLocalLines -join "`n" | Set-Content -Path (Join-Path $root ".env.local") -Encoding utf8 -NoNewline:$false
Pop-Location
Write-Host "Deployed. REVENUE_SERVICE_ADDRESS=$revenueAddr COMPUTE_MARKETPLACE_ADDRESS=$marketplaceAddr .env.local written."
