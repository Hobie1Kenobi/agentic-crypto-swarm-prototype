# Read-only checks before Celo mainnet deploy / smoke (CHAIN_ID=42220).
# Does not send transactions. Uses cast (Foundry) when available for RPC/chain/balance/code checks.
param(
    [switch]$Strict,
    [decimal]$MinCeloPerAccount = 0.02
)

$ErrorActionPreference = "Stop"
$env:FOUNDRY_DISABLE_NIGHTLY_WARNING = "1"
$mainnetId = 42220
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envPath = Join-Path $root ".env"

function Test-EnvVar {
    param([string]$Name, [string]$Value)
    if (-not $Value) { return "missing" }
    if ($Value -match "your_") { return "placeholder" }
    return "ok"
}

function Get-Cast {
    $foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
    if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }
    $c = Get-Command cast -ErrorAction SilentlyContinue
    if (-not $c) { return $null }
    return $c.Source
}

if (-not (Test-Path $envPath)) {
    Write-Host "FAIL: No .env at $envPath (copy .env.example)"
    exit 1
}

Get-Content $envPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($k, $v, "Process")
    }
}

$issues = @()
$warn = @()

if ([string]$env:CHAIN_ID -ne [string]$mainnetId) {
    $issues += "CHAIN_ID must be $mainnetId (celo-mainnet). Got: $($env:CHAIN_ID)"
}

$rpc = $env:RPC_URL
if (-not $rpc) { $rpc = $env:CELO_MAINNET_RPC_URL }
if (-not $rpc) {
    $issues += "Set RPC_URL or CELO_MAINNET_RPC_URL for Celo mainnet."
}

$pkVars = @(
    "PRIVATE_KEY",
    "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR_PRIVATE_KEY"
)
foreach ($k in $pkVars) {
    $st = Test-EnvVar $k ([Environment]::GetEnvironmentVariable($k, "Process"))
    if ($st -ne "ok") { $issues += "$k : $st" }
}

$addrVars = @(
    "ROOT_STRATEGIST_ADDRESS",
    "IP_GENERATOR_ADDRESS",
    "DEPLOYER_ADDRESS",
    "FINANCE_DISTRIBUTOR_ADDRESS"
)
foreach ($k in $addrVars) {
    $v = [Environment]::GetEnvironmentVariable($k, "Process")
    $st = Test-EnvVar $k $v
    if ($st -ne "ok") { $issues += "$k : $st" }
    elseif ($v -match '^0x0{39}[0-1]$') { $warn += "$k is zero address" }
}

$castExe = Get-Cast
if (-not $castExe) {
    $warn += "cast not in PATH (install Foundry); skipping chain/balance/code checks."
} elseif ($rpc) {
    try {
        $rawCid = & $castExe chain-id --rpc-url $rpc 2>&1
        if ($LASTEXITCODE -ne 0) { throw ($rawCid | Out-String) }
        $cid = ($rawCid | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d+$' } | Select-Object -First 1)
        if (-not $cid) { throw "Could not parse chain id from cast output" }
        if ([string]$cid -ne [string]$mainnetId) {
            $issues += "RPC chain-id is $cid (expected $mainnetId). Wrong RPC_URL?"
        }
    } catch {
        $issues += "RPC unreachable or invalid: $_"
    }

    function Get-BalanceWei([string]$Addr) {
        $out = & $castExe balance $Addr --rpc-url $rpc 2>&1
        if ($LASTEXITCODE -ne 0) { return $null }
        $line = ($out | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d+(\.\d+)?$' } | Select-Object -First 1)
        if (-not $line) { return $null }
        return [decimal]$line
    }

    function Get-CodeLen([string]$Addr) {
        $hex = & $castExe code $Addr --rpc-url $rpc 2>&1
        if ($LASTEXITCODE -ne 0) { return -1 }
        $hexLine = ($hex | ForEach-Object { "$_" } | Where-Object { $_ -match '^0x' } | Select-Object -First 1)
        if (-not $hexLine) { $hexLine = "$hex" }
        if ($hexLine -eq "0x") { return 0 }
        return ($hexLine.Length - 2) / 2
    }

    $minWei = $MinCeloPerAccount * [decimal]([Math]::Pow(10, 18))

    try {
        $pk = [Environment]::GetEnvironmentVariable("PRIVATE_KEY", "Process")
        if ($pk -and $pk -notmatch "your_") {
            $depRaw = & $castExe wallet address $pk 2>&1
            $dep = ($depRaw | ForEach-Object { "$_" } | Where-Object { $_ -match '^0x[a-fA-F0-9]{40}$' } | Select-Object -First 1)
            if ($LASTEXITCODE -eq 0 -and $dep) {
                $b = Get-BalanceWei $dep
                Write-Host "Deployer (from PRIVATE_KEY): $dep  balance: $b wei"
                if ($null -ne $b -and $b -lt $minWei) {
                    $warn += "Deployer balance below $MinCeloPerAccount CELO (may not be enough for deploy gas)."
                }
            }
        }
    } catch { $warn += "Could not read deployer balance: $_" }

    foreach ($k in $addrVars) {
        $a = [Environment]::GetEnvironmentVariable($k, "Process")
        if (-not $a -or $a -match "your_") { continue }
        try {
            $b = Get-BalanceWei $a
            Write-Host "$k : $a  balance: $b wei"
            if ($null -ne $b -and $b -lt $minWei) {
                $warn += "$k balance below $MinCeloPerAccount CELO."
            }
        } catch { $warn += "Balance check failed for $k : $_" }
    }

    $deployed = @(
        @{ Name = "REVENUE_SERVICE_ADDRESS"; Var = "REVENUE_SERVICE_ADDRESS" },
        @{ Name = "COMPUTE_MARKETPLACE_ADDRESS"; Var = "COMPUTE_MARKETPLACE_ADDRESS" }
    )
    foreach ($d in $deployed) {
        $a = [Environment]::GetEnvironmentVariable($d.Var, "Process")
        if (-not $a -or $a -notmatch '^0x[a-fA-F0-9]{40}$') { continue }
        try {
            $len = Get-CodeLen $a
            if ($len -eq 0) {
                $warn += "$($d.Name) $a has no contract code on mainnet (deploy or fix address)."
            } elseif ($len -gt 0) {
                Write-Host "OK: $($d.Name) has on-chain code (bytecode len ~ $len)."
            }
        } catch { $warn += "Code check failed for $($d.Name): $_" }
    }
}

if ($issues.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Issues ===" -ForegroundColor Red
    $issues | ForEach-Object { Write-Host " - $_" }
}
if ($warn.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Warnings ===" -ForegroundColor Yellow
    $warn | ForEach-Object { Write-Host " - $_" }
}

if ($issues.Count -gt 0) {
    Write-Host ""
    Write-Host "Preflight FAILED."
    exit 1
}

if ($Strict -and $warn.Count -gt 0) {
    Write-Host ""
    Write-Host "Preflight FAILED (-Strict: warnings treated as errors)."
    exit 1
}

Write-Host ""
Write-Host "Preflight OK (mainnet $mainnetId). Next: npm run mainnet:readiness (dry-run deploy + fetch) or add -- -Broadcast after funding deployer."
exit 0
