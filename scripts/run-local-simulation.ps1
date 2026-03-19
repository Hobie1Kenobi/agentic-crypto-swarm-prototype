# Run full live simulation on local Anvil — no testnet ETH needed.
# Uses Anvil's pre-funded account (10,000 ETH). Deploys contracts, then runs simulation.
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
    Write-Host "Starting Anvil on $rpc ..."
    $anvilProc = Start-Process -FilePath "anvil" -ArgumentList "--port 8545" -WorkingDirectory $root -PassThru -WindowStyle Hidden
    $maxWait = 10
    $waited = 0
    while (-not (Test-AnvilRunning) -and $waited -lt $maxWait) {
        Start-Sleep -Seconds 1
        $waited++
    }
    if (-not (Test-AnvilRunning)) {
        Write-Error "Anvil did not start in time"
        exit 1
    }
    Write-Host "Anvil started (PID $($anvilProc.Id))."
} else {
    Write-Host "Anvil already running on $rpc"
}

$env:RPC_URL = $rpc
$env:CHAIN_ID = "31337"
$env:PRIVATE_KEY = $anvilKey
$env:FINANCE_DISTRIBUTOR_ADDRESS = $anvilAccount0
$env:BENEFICIARY_ADDRESS = $anvilAccount0

Push-Location $root
try {
    Write-Host "Deploying contracts to Anvil..."
    $forgeOut = & forge script script/Deploy.s.sol --rpc-url $rpc --broadcast --private-key $anvilKey 2>&1
    $forgeOut | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Forge script exited with $LASTEXITCODE" }

    $broadcastDir = Join-Path $root "broadcast\Deploy.s.sol\31337"
    $runLatest = Join-Path $broadcastDir "run-latest.json"
    if (-not (Test-Path $runLatest)) {
        $files = Get-ChildItem -Path $broadcastDir -Filter "run-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
        if ($files) { $runLatest = $files[0].FullName }
    }
    if (-not (Test-Path $runLatest)) {
        Write-Error "No broadcast artifact for chain 31337. Deploy may have failed."
        exit 1
    }
    $data = Get-Content $runLatest -Raw | ConvertFrom-Json
    $revenueAddr = $null
    foreach ($tx in $data.transactions) {
        if ($tx.contractName -eq "AgentRevenueService") { $revenueAddr = $tx.contractAddress; break }
    }
    if (-not $revenueAddr) {
        Write-Error "AgentRevenueService address not found in broadcast"
        exit 1
    }
    $revenueAddr = $revenueAddr.ToLower()
    Write-Host "REVENUE_SERVICE_ADDRESS=$revenueAddr"

    $envLocalPath = Join-Path $root ".env.local"
    @"
RPC_URL=$rpc
CHAIN_ID=31337
REVENUE_SERVICE_ADDRESS=$revenueAddr
PRIVATE_KEY=$anvilKey
ROOT_STRATEGIST_PRIVATE_KEY=$anvilKey
IP_GENERATOR_PRIVATE_KEY=$anvilKey
DEPLOYER_PRIVATE_KEY=$anvilKey
FINANCE_DISTRIBUTOR_ADDRESS=$anvilAccount0
FINANCE_DISTRIBUTOR_PRIVATE_KEY=$anvilKey
BENEFICIARY_ADDRESS=$anvilAccount0
"@ | Set-Content -Path $envLocalPath -Encoding utf8 -NoNewline:$false
    Write-Host "Wrote $envLocalPath"

    Write-Host "Running simulation (10 users x 0.001 ETH)..."
    Push-Location (Join-Path $root "packages\agents")
    try {
        $simOut = & python simulation_run.py 2>&1
        $simOut | Out-Host
    } finally {
        Pop-Location
    }
    Write-Host "Generating simulation report..."
    Push-Location $root
    & python scripts/generate-simulation-report.py --output-dir $root 2>&1 | Out-Host
    Pop-Location
    if (Test-Path $envLocalPath) { Remove-Item $envLocalPath -Force }
} finally {
    Pop-Location
}

Write-Host "Local simulation complete. See simulation_report.json and simulation_report.md (no faucet)."
