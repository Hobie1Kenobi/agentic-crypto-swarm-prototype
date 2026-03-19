# Local-first test harness: Anvil + deploy + agent env + orchestration + report.
# No external faucet; deterministic Anvil key for all agents; repeatable; optional -Reset for clean state.
# Usage: .\scripts\local-harness.ps1 [-Reset]
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }

$env:FOUNDRY_DISABLE_NIGHTLY_WARNING = "1"
$anvilKey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
$rpc = "http://127.0.0.1:8545"

# Create distinct funded EOAs for the marketplace demo signers:
# - requester: ROOT_STRATEGIST_PRIVATE_KEY
# - worker: IP_GENERATOR_PRIVATE_KEY
# - validator/owner: DEPLOYER_PRIVATE_KEY (and PRIVATE_KEY)
# - finance distributor: FINANCE_DISTRIBUTOR_PRIVATE_KEY
# We derive these deterministically from the known Anvil funding key and fund them from `anvilAccount0`.
$keysJson = & python -c "from eth_account import Account; from web3 import Web3; import json
anvil_key = r'${anvilKey}'
rpc = r'${rpc}'
base = int(anvil_key, 16)
offs = {'requester': 11, 'worker': 22, 'validator': 33, 'finance': 44}
w3 = Web3(Web3.HTTPProvider(rpc))
sender = Account.from_key(anvil_key)
nonce = w3.eth.get_transaction_count(sender.address, 'pending')
gas_price = w3.eth.gas_price
out = {}
for name, off in offs.items():
    pk = '0x' + format(base + off, '064x')
    acct = Account.from_key(pk)
    out[name + '_private_key'] = pk
    out[name + '_address'] = acct.address
    tx = {'to': acct.address, 'value': w3.to_wei(50, 'ether'), 'gas': 21000, 'gasPrice': gas_price, 'nonce': nonce, 'chainId': w3.eth.chain_id}
    signed = sender.sign_transaction(tx)
    w3.eth.send_raw_transaction(signed.raw_transaction)
    nonce += 1
print(json.dumps(out))"
$keys = $keysJson | ConvertFrom-Json
$requesterPk = $keys.requester_private_key
$workerPk = $keys.worker_private_key
$validatorPk = $keys.validator_private_key
$financePk = $keys.finance_private_key
$requesterAddr = $keys.requester_address
$validatorAddr = $keys.validator_address
$financeAddr = $keys.finance_address

function Test-AnvilRunning {
    try {
        $r = Invoke-WebRequest -Uri "$rpc" -Method POST -Body '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' -ContentType "application/json" -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Stop-AnvilIfRunning {
    try {
        $conn = Get-NetTCPConnection -LocalPort 8545 -ErrorAction SilentlyContinue
        if ($conn) {
            $conn | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
            Start-Sleep -Seconds 2
        }
    } catch {}
    $proc = Get-Process -Name "anvil" -ErrorAction SilentlyContinue
    if ($proc) {
        $proc | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

$reset = $false
foreach ($arg in $args) {
    if ($arg -eq "-Reset" -or $arg -eq "--Reset") { $reset = $true; break }
}

if ($reset) {
    Write-Host "Reset: stopping Anvil for clean state..."
    Stop-AnvilIfRunning
    Start-Sleep -Seconds 1
}

if (-not (Test-AnvilRunning)) {
    Write-Host "Starting Anvil on $rpc ..."
    $anvilProc = Start-Process -FilePath "anvil" -ArgumentList "--port 8545" -WorkingDirectory $root -PassThru -WindowStyle Hidden
    $maxWait = 15
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
$env:PRIVATE_KEY = $validatorPk
$env:TREASURY_ADDRESS = $validatorAddr
$env:ROOT_STRATEGIST_PRIVATE_KEY = $requesterPk
$env:IP_GENERATOR_PRIVATE_KEY = $workerPk
$env:DEPLOYER_PRIVATE_KEY = $validatorPk
$env:FINANCE_DISTRIBUTOR_ADDRESS = $financeAddr
$env:FINANCE_DISTRIBUTOR_PRIVATE_KEY = $financePk
$env:BENEFICIARY_ADDRESS = $requesterAddr
$env:LLM_DRY_RUN = "1"
$env:SIMULATION_NUM_USERS = "10"
$env:SIMULATION_PROFIT_THRESHOLD_ETH = "0.003"

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
        Write-Error "No broadcast artifact for chain 31337."
        exit 1
    }
    $data = Get-Content $runLatest -Raw | ConvertFrom-Json
    $revenueAddr = $null
    $marketplaceAddr = $null
    $constitutionAddr = $null
    foreach ($tx in $data.transactions) {
        if ($tx.contractName -eq "AgentRevenueService") { $revenueAddr = $tx.contractAddress }
        if ($tx.contractName -eq "ComputeMarketplace") { $marketplaceAddr = $tx.contractAddress }
        if ($tx.contractName -eq "Constitution") { $constitutionAddr = $tx.contractAddress }
    }
    if (-not $revenueAddr) {
        Write-Error "AgentRevenueService address not found in broadcast"
        exit 1
    }
    $revenueAddr = $revenueAddr.ToLower()
    if ($marketplaceAddr) { $marketplaceAddr = $marketplaceAddr.ToLower() }
    if ($constitutionAddr) { $constitutionAddr = $constitutionAddr.ToLower() }

    $envLocalPath = Join-Path $root ".env.local"
    $envLocalLines = @(
        "RPC_URL=$rpc",
        "CHAIN_ID=31337",
        "REVENUE_SERVICE_ADDRESS=$revenueAddr",
        "PRIVATE_KEY=$validatorPk",
        "ROOT_STRATEGIST_PRIVATE_KEY=$requesterPk",
        "IP_GENERATOR_PRIVATE_KEY=$workerPk",
        "DEPLOYER_PRIVATE_KEY=$validatorPk",
        "FINANCE_DISTRIBUTOR_ADDRESS=$financeAddr",
        "FINANCE_DISTRIBUTOR_PRIVATE_KEY=$financePk",
        "BENEFICIARY_ADDRESS=$requesterAddr",
        "LLM_DRY_RUN=1",
        "SIMULATION_NUM_USERS=10",
        "SIMULATION_PROFIT_THRESHOLD_ETH=0.003"
    )
    if ($marketplaceAddr) { $envLocalLines += "COMPUTE_MARKETPLACE_ADDRESS=$marketplaceAddr" }
    if ($constitutionAddr) { $envLocalLines += "CONSTITUTION_ADDRESS=$constitutionAddr" }
    $envLocalLines -join "`n" | Set-Content -Path $envLocalPath -Encoding utf8 -NoNewline:$false
    Write-Host "Wrote $envLocalPath (deterministic keys; no faucet)."

    foreach ($line in $envLocalLines) {
        if ($line -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }

    $maxSteps = if ($env:ORCHESTRATE_MAX_STEPS) { $env:ORCHESTRATE_MAX_STEPS } else { "10" }
    Write-Host "Running full orchestration (max $maxSteps steps)..."
    Push-Location (Join-Path $root "packages\agents")
    try {
        $orchOut = & python main.py --max-steps $maxSteps 2>&1
        $orchOut | Out-Host
    } finally {
        Pop-Location
    }

    Write-Host "Generating simulation report..."
    $reportOut = & python scripts/generate-simulation-report.py --output-dir $root 2>&1
    $reportOut | Out-Host
    $jsonPath = Join-Path $root "simulation_report.json"
    $mdPath = Join-Path $root "simulation_report.md"
    if (Test-Path $jsonPath) {
        Write-Host ""
        Write-Host "=== Local harness complete ==="
        Write-Host "Report: $jsonPath"
        Write-Host "Summary: $mdPath"
    }
} finally {
    Pop-Location
}
