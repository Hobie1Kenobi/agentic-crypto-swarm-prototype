# Enable full Celo settlement (five distinct addresses).
# Prereqs: .env with PRIVATE_KEY (deployer), existing agent keys. Fund deployer + TREASURY_ADDRESS.
# Steps: 1) create-accounts (adds TREASURY), 2) deploy --broadcast, 3) fetch addresses, 4) run task demo.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"

if (-not (Test-Path $envPath)) {
    Write-Error "No .env found. Copy .env.example to .env and set PRIVATE_KEY, FINANCE_DISTRIBUTOR_ADDRESS."
    exit 1
}

$envContent = Get-Content $envPath -Raw
if (-not ($envContent -match "PRIVATE_KEY\s*=\s*0x[a-fA-F0-9]{64}")) {
    Write-Error "Set PRIVATE_KEY in .env (deployer EOA with Celo Sepolia CELO)."
    exit 1
}

Write-Host "Step 1: Create/update accounts (adds TREASURY if missing)..."
Push-Location $root
try {
    npm run create-accounts 2>&1 | Out-Host
} finally {
    Pop-Location
}

$treasuryAddr = (Get-Content $envPath | Where-Object { $_ -match '^TREASURY_ADDRESS=(.+)$' }) -replace '^TREASURY_ADDRESS=',''
$treasuryAddr = ($treasuryAddr -split "`n")[0].Trim()
$financeAddr = (Get-Content $envPath | Where-Object { $_ -match '^FINANCE_DISTRIBUTOR_ADDRESS=(.+)$' }) -replace '^FINANCE_DISTRIBUTOR_ADDRESS=',''
$financeAddr = ($financeAddr -split "`n")[0].Trim()

if (-not $treasuryAddr -or $treasuryAddr.Length -lt 40) {
    Write-Error "TREASURY_ADDRESS not set. Run: npm run create-accounts"
    exit 1
}
if (-not $financeAddr -or $financeAddr.Length -lt 40) {
    Write-Error "FINANCE_DISTRIBUTOR_ADDRESS not set. Run: npm run create-accounts"
    exit 1
}

$rootStrategist = (Get-Content $envPath | Where-Object { $_ -match '^ROOT_STRATEGIST_ADDRESS=(.+)$' }) -replace '^ROOT_STRATEGIST_ADDRESS=',''
$rootStrategist = ($rootStrategist -split "`n")[0].Trim()
if ($treasuryAddr -eq $rootStrategist) {
    Write-Host "WARNING: TREASURY_ADDRESS equals ROOT_STRATEGIST_ADDRESS. create-accounts should have generated a new TREASURY. Check .env."
}

Write-Host ""
Write-Host "Step 2: Deploy contracts (TREASURY_ADDRESS=$treasuryAddr, FINANCE_DISTRIBUTOR_ADDRESS=$financeAddr)..."
Write-Host "Ensure deployer (PRIVATE_KEY) and TREASURY_ADDRESS are funded on Celo Sepolia."
$confirm = Read-Host "Deploy now? (y/n)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Skipped. Run manually: .\scripts\deploy.ps1 --broadcast"
    exit 0
}

Push-Location $root
try {
    & (Join-Path $root "scripts\deploy.ps1") --broadcast 2>&1 | Out-Host
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Step 3: Fetch and save addresses..."
Push-Location $root
try {
    powershell -ExecutionPolicy Bypass -File (Join-Path $root "scripts\fetch-and-save-addresses.ps1") 2>&1 | Out-Host
} finally {
    Pop-Location
}

$envContent = Get-Content $envPath -Raw
$envContent = $envContent -replace 'TASK_WORKER_ROLE=.*', 'TASK_WORKER_ROLE=IP_GENERATOR'
$envContent = $envContent -replace 'TASK_VALIDATOR_ROLE=.*', 'TASK_VALIDATOR_ROLE=DEPLOYER'
if (-not ($envContent -match 'TASK_WORKER_ROLE')) {
    $envContent += "`nTASK_WORKER_ROLE=IP_GENERATOR"
}
if (-not ($envContent -match 'TASK_VALIDATOR_ROLE')) {
    $envContent += "`nTASK_VALIDATOR_ROLE=DEPLOYER"
}
Set-Content -Path $envPath -Value $envContent.TrimEnd() -NoNewline:$false

Write-Host ""
Write-Host "Step 4: Run task market demo..."
Push-Location (Join-Path $root "packages\agents")
try {
    $env:COMPUTE_TASK_QUERY = "What is one ethical use of AI?"
    python -c "
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('../../.env'), override=True)
from task_market_demo import run_task_market_demo
r = run_task_market_demo()
print('ok:', r.get('ok'))
print('task_id:', (r.get('task') or {}).get('task_id'))
if not r.get('ok'):
    print('error:', r.get('error'))
"
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Check task_market_demo_report.md and deployed_address_manifest.json."
