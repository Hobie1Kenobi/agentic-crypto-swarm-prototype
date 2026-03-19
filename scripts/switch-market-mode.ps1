[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$Mode,

  [string]$EnvPath = ""
)

$ErrorActionPreference = "Stop"

$Mode = ("" + $Mode).ToString().Trim().ToLower()
if ($Mode -notin @("private_celo", "public_olas", "hybrid")) {
  throw "Invalid -Mode '$Mode'. Allowed: private_celo, public_olas, hybrid."
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $EnvPath) { $EnvPath = Join-Path $root ".env" }

if (-not (Test-Path $EnvPath)) {
  throw "Env file not found: $EnvPath"
}

function Upsert-Line([string[]]$lines, [string]$key, [string]$value) {
  $prefix = "$key="
  $found = $false
  $out = @()
  foreach ($l in $lines) {
    if ($l -match "^\s*#") { $out += $l; continue }
    if ($l -match "^\s*$") { $out += $l; continue }
    if ($l.StartsWith($prefix)) {
      $out += "$key=$value"
      $found = $true
    } else {
      $out += $l
    }
  }
  if (-not $found) {
    $out += ""
    $out += "$key=$value"
  }
  return ,$out
}

$raw = Get-Content -Path $EnvPath -Raw
# Preserve existing newlines; normalize to array of lines.
$lines = $raw -split "`r?`n"

$lines = Upsert-Line $lines "MARKET_MODE" $Mode

# Safety defaults: keep chain default as Celo Sepolia unless user explicitly changes it.
if (-not ($lines -join "`n" | Select-String -SimpleMatch "CHAIN_NAME=")) {
  $lines = Upsert-Line $lines "CHAIN_NAME" "celo-sepolia"
}
if (-not ($lines -join "`n" | Select-String -SimpleMatch "CHAIN_ID=")) {
  $lines = Upsert-Line $lines "CHAIN_ID" "11142220"
}

# Dual-chain defaults: PRIVATE_* always point to Celo Sepolia.
if (-not ($lines -join "`n" | Select-String -SimpleMatch "PRIVATE_CHAIN_NAME=")) {
  $lines = Upsert-Line $lines "PRIVATE_CHAIN_NAME" "celo-sepolia"
}
if (-not ($lines -join "`n" | Select-String -SimpleMatch "PRIVATE_CHAIN_ID=")) {
  $lines = Upsert-Line $lines "PRIVATE_CHAIN_ID" "11142220"
}

$backup = "$EnvPath.bak"
Copy-Item -Path $EnvPath -Destination $backup -Force

($lines -join "`n") | Set-Content -Path $EnvPath -Encoding utf8 -NoNewline:$false

Write-Host "Switched MARKET_MODE=$Mode"
Write-Host "Updated: $EnvPath"
Write-Host "Backup:  $backup"

if ($Mode -eq "public_olas") {
  # Live external requests should target Gnosis in this repo.
  if (-not ($lines -join "`n" | Select-String -SimpleMatch "OLAS_CHAIN_CONFIG=")) {
    $raw = Get-Content -Path $EnvPath -Raw
    $lines2 = $raw -split "`r?`n"
    $lines2 = Upsert-Line $lines2 "OLAS_CHAIN_CONFIG" "gnosis"
    $lines2 = Upsert-Line $lines2 "PUBLIC_OLAS_CHAIN_NAME" "gnosis"
    $lines2 = Upsert-Line $lines2 "PUBLIC_OLAS_CHAIN_ID" "100"
    ($lines2 -join "`n") | Set-Content -Path $EnvPath -Encoding utf8 -NoNewline:$false
  }
  Write-Host ""
  Write-Host "Note: public_olas is an adapter mode. Until the Olas connection is fully implemented and configured,"
  Write-Host "the system may run in partial/mock adapter mode with explicit reporting boundaries."
}

