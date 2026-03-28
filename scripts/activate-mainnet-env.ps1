# Build .env for mainnet by merging .env.mainnet over your existing .env.
# - Non-empty values in .env.mainnet override .env (chain, mainnet RPC, deployed addresses).
# - Empty values in .env.mainnet mean "keep whatever is already in .env" (so keys stay in one place).
# - If .env does not exist, copies .env.mainnet to .env.
# Usage: .\scripts\activate-mainnet-env.ps1   |   .\scripts\activate-mainnet-env.ps1 -Replace
param(
    [switch]$Replace
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$src = Join-Path $root ".env.mainnet"
$dst = Join-Path $root ".env"
$example = Join-Path $root ".env.mainnet.example"

if (-not (Test-Path $src)) {
    if (Test-Path $example) {
        Write-Host "No .env.mainnet found. Copying .env.mainnet.example -> .env.mainnet"
        Copy-Item $example $src
    } else {
        Write-Error "Missing .env.mainnet and .env.mainnet.example"
        exit 1
    }
}

if (-not (Test-Path $dst)) {
    Copy-Item $src $dst -Force
    Write-Host "Created .env from .env.mainnet (no prior .env)."
    Write-Host "Next: put shared secrets in .env OR in .env.mainnet; re-run without -Replace to merge."
    exit 0
}

if ($Replace) {
    if (Test-Path $dst) {
        $bak = Join-Path $root (".env.backup." + (Get-Date -Format "yyyyMMdd-HHmmss"))
        Copy-Item $dst $bak
        Write-Host "Backed up current .env to $bak"
    }
    Copy-Item $src $dst -Force
    Write-Host "Replaced .env with .env.mainnet (-Replace). Previous .env backed up."
    exit 0
}

if (Test-Path $dst) {
    $bak = Join-Path $root (".env.backup." + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Copy-Item $dst $bak
    Write-Host "Backed up current .env to $bak"
}

$overlay = @{}
Get-Content $src | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $overlay[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$lines = New-Object System.Collections.ArrayList
$keyLine = @{}
foreach ($line in Get-Content $dst) {
    if ($line -match '^([^#=]+)=(.*)$') {
        $k = $matches[1].Trim()
        $keyLine[$k] = $lines.Count
    }
    [void]$lines.Add($line)
}

foreach ($k in $overlay.Keys) {
    $val = $overlay[$k]
    if ($val -eq "") {
        continue
    }
    $newLine = "$k=$val"
    if ($keyLine.ContainsKey($k)) {
        $lines[$keyLine[$k]] = $newLine
    } else {
        [void]$lines.Add($newLine)
        $keyLine[$k] = $lines.Count - 1
    }
}

$content = ($lines | ForEach-Object { $_ }) -join "`n"
if (-not $content.EndsWith("`n")) { $content += "`n" }
Set-Content -Path $dst -Value $content -NoNewline:$false

Write-Host "Merged .env.mainnet into .env (non-empty overlay keys only; empty overlay = keep existing .env)."
Write-Host "Runtime (smoke, agents, forge): always load repo-root .env only - no second file at execution time."
Write-Host "Verify: npm run mainnet:preflight"
