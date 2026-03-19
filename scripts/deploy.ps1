# Load .env and run Forge deploy. Usage: .\scripts\deploy.ps1 [--broadcast]
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
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }
$broadcast = if ($args -contains "--broadcast") { "--broadcast" } else { "" }
$pk = $env:PRIVATE_KEY
if ($broadcast -and -not $pk) {
    Write-Error "Set PRIVATE_KEY in .env for broadcast (EOA with testnet ETH)"
}
#
# Some Celo RPC/forwarders enforce strict EIP-1559 fee-cap constraints.
# Allow switching to legacy tx type for higher compatibility during testnet ops.
#
$useLegacy = $env:USE_LEGACY_TXS
if ($useLegacy -and ($useLegacy -match '^(1|true|yes)$')) {
    $useLegacyFlag = "--legacy"
} else {
    $useLegacyFlag = ""
}
Push-Location $root
try {
    $forgeArgs = @("script/Deploy.s.sol", "--rpc-url", $rpc)
    if ($broadcast) { $forgeArgs += "--broadcast" }
    if ($broadcast -and $useLegacyFlag) { $forgeArgs += $useLegacyFlag }
    if ($broadcast -and $pk) {
        $forgeArgs += "--private-key"
        $forgeArgs += $pk
    }
    if ($env:ETH_GAS_PRICE) {
        $forgeArgs += "--with-gas-price"
        $forgeArgs += $env:ETH_GAS_PRICE
    }
    if ($env:ETH_PRIORITY_GAS_PRICE) {
        $forgeArgs += "--priority-gas-price"
        $forgeArgs += $env:ETH_PRIORITY_GAS_PRICE
    }
    forge script @forgeArgs
} finally {
    Pop-Location
}
