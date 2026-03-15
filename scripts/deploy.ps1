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
$rpc = $env:RPC_URL
if (-not $rpc -and $env:ALCHEMY_API_KEY) {
    $rpc = "https://base-sepolia.g.alchemy.com/v2/$($env:ALCHEMY_API_KEY)"
}
if (-not $rpc) { $rpc = "https://sepolia.base.org" }
$foundryBin = Join-Path $env:USERPROFILE ".foundry\bin"
if (Test-Path $foundryBin) { $env:Path = "$foundryBin;$env:Path" }
$broadcast = if ($args -contains "--broadcast") { "--broadcast" } else { "" }
$pk = $env:PRIVATE_KEY
if ($broadcast -and -not $pk) {
    Write-Error "Set PRIVATE_KEY in .env for broadcast (EOA with testnet ETH)"
}
Push-Location $root
try {
    forge script script/Deploy.s.sol --rpc-url $rpc $broadcast
} finally {
    Pop-Location
}
