# Fetch deployed/predicted addresses from Forge broadcast and update .env
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"
$chainIds = @(11142220, 42220, 31337, 84532)
$broadcastPath = $null
foreach ($cid in $chainIds) {
    $p = Join-Path $root "broadcast\Deploy.s.sol\$cid"
    if (Test-Path $p) { $broadcastPath = $p; break }
}
if (-not $broadcastPath) { $broadcastPath = Join-Path $root "broadcast\Deploy.s.sol\11142220" }

$revenueAddr = $null
$constitutionAddr = $null
$marketplaceAddr = $null

$searchDirs = @(
    (Join-Path $broadcastPath "dry-run"),
    $broadcastPath
)
foreach ($dirPath in $searchDirs) {
    if (-not (Test-Path $dirPath)) { continue }
    $jsonPath = Join-Path $dirPath "run-latest.json"
    if (-not (Test-Path $jsonPath)) {
        $files = Get-ChildItem -Path $dirPath -Filter "run-*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
        if ($files) { $jsonPath = $files[0].FullName }
    }
    if (Test-Path $jsonPath) {
        $data = Get-Content $jsonPath -Raw | ConvertFrom-Json
        foreach ($tx in $data.transactions) {
            if ($tx.contractName -eq "AgentRevenueService") { $revenueAddr = $tx.contractAddress }
            if ($tx.contractName -eq "Constitution") { $constitutionAddr = $tx.contractAddress }
            if ($tx.contractName -eq "ComputeMarketplace") { $marketplaceAddr = $tx.contractAddress }
        }
        if ($revenueAddr) { break }
    }
}

if (-not $revenueAddr) {
    Write-Host "No broadcast artifact found. Run: .\scripts\deploy.ps1 (dry-run or --broadcast)"
    exit 1
}

$revenueAddr = $revenueAddr.ToLower()
if ($constitutionAddr) { $constitutionAddr = $constitutionAddr.ToLower() }
if ($marketplaceAddr) { $marketplaceAddr = $marketplaceAddr.ToLower() }

$lines = @()
$updated = @{}
$updated["REVENUE_SERVICE_ADDRESS"] = $revenueAddr
$updated["CONSTITUTION_ADDRESS"] = $constitutionAddr
if ($marketplaceAddr) { $updated["COMPUTE_MARKETPLACE_ADDRESS"] = $marketplaceAddr }

if (Test-Path $envPath) {
    $seen = @{}
    Get-Content $envPath | ForEach-Object {
        $line = $_
        if ($line -match '^([^#=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $seen[$key] = $true
            if ($updated.ContainsKey($key)) {
                $lines += "$key=$($updated[$key])"
                $updated.Remove($key) | Out-Null
            } else {
                $lines += $line
            }
        } else {
            $lines += $line
        }
    }
    foreach ($k in $updated.Keys) {
        $lines += "$k=$($updated[$k])"
    }
} else {
    $lines = @(
        "REVENUE_SERVICE_ADDRESS=$revenueAddr",
        "CONSTITUTION_ADDRESS=$constitutionAddr"
    )
    if ($marketplaceAddr) { $lines += "COMPUTE_MARKETPLACE_ADDRESS=$marketplaceAddr" }
}

$content = $lines -join "`n"
if (-not $content.EndsWith("`n")) { $content += "`n" }
Set-Content -Path $envPath -Value $content -NoNewline:$false

Write-Host "Updated .env with:"
Write-Host "  REVENUE_SERVICE_ADDRESS=$revenueAddr"
Write-Host "  CONSTITUTION_ADDRESS=$constitutionAddr"
if ($marketplaceAddr) { Write-Host "  COMPUTE_MARKETPLACE_ADDRESS=$marketplaceAddr" }

$beneficiaryKey = "BENEFICIARY_ADDRESS"
$hasBeneficiary = (Get-Content $envPath -Raw) -match "^\s*BENEFICIARY_ADDRESS\s*=\s*\S"
if (-not $hasBeneficiary) {
    $rootStrategist = (Get-Content $envPath | Where-Object { $_ -match '^ROOT_STRATEGIST_ADDRESS=(.+)$' }) -replace '^ROOT_STRATEGIST_ADDRESS=',''
    if ($rootStrategist) {
        $rootStrategist = $rootStrategist.Trim()
        (Get-Content $envPath) + "`nBENEFICIARY_ADDRESS=$rootStrategist" | Set-Content $envPath
        Write-Host "  BENEFICIARY_ADDRESS=$rootStrategist (set from ROOT_STRATEGIST_ADDRESS; change if needed)"
    }
}
