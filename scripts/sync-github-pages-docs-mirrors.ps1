# Sync markdown mirrors under docs/ for GitHub Pages (matches docs/sitemap.xml URLs).
# Run from repo root after editing documentation/ or artifacts/reports/ sources.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

New-Item -ItemType Directory -Force -Path "docs\docs" | Out-Null

Copy-Item -Force "documentation\architecture\ARCHITECTURE.md" "docs\docs\ARCHITECTURE.md"
Copy-Item -Force "documentation\x402-t54-base\X402_MARKETPLACE_INTEGRATION.md" "docs\docs\X402_MARKETPLACE_INTEGRATION.md"
Copy-Item -Force "documentation\x402-t54-base\T54_SELLER.md" "docs\docs\T54_SELLER.md"

Copy-Item -Force "artifacts\reports\x402_agent_commerce_soak_report.md" "docs\x402_agent_commerce_soak_report.md"
Copy-Item -Force "artifacts\reports\live_xrpl_to_celo_proof_report.md" "docs\live_xrpl_to_celo_proof_report.md"
Copy-Item -Force "artifacts\reports\continuous_multi_rail_24h_report.md" "docs\continuous_multi_rail_24h_report.md"

$gh = "https://github.com/Hobie1Kenobi/agentic-crypto-swarm-prototype/blob/master"
$arch = Get-Content -Raw "docs\docs\ARCHITECTURE.md"
$arch = $arch.Replace(
    "See [``../celo-xrpl/XRPL_PAYMENTS.md``](../celo-xrpl/XRPL_PAYMENTS.md).",
    "See [XRPL_PAYMENTS.md]($gh/documentation/celo-xrpl/XRPL_PAYMENTS.md) (canonical in ``documentation/``)."
)
$arch = $arch.Replace(
    "Details: [``../operations/PUBLIC-ADAPTER.md``](../operations/PUBLIC-ADAPTER.md)",
    "Details: [PUBLIC-ADAPTER.md]($gh/documentation/operations/PUBLIC-ADAPTER.md)"
)
[System.IO.File]::WriteAllText("$root\docs\docs\ARCHITECTURE.md", $arch, [System.Text.UTF8Encoding]::new($false))

$x402 = Get-Content -Raw "docs\docs\X402_MARKETPLACE_INTEGRATION.md"
$x402 = $x402.Replace(
    "- See [``T54_XRPL_TESTNET_WORKAROUND.md``](T54_XRPL_TESTNET_WORKAROUND.md)",
    "- See [T54_XRPL_TESTNET_WORKAROUND.md]($gh/documentation/x402-t54-base/T54_XRPL_TESTNET_WORKAROUND.md)"
)
[System.IO.File]::WriteAllText("$root\docs\docs\X402_MARKETPLACE_INTEGRATION.md", $x402, [System.Text.UTF8Encoding]::new($false))

Write-Host "Synced GitHub Pages doc mirrors under docs/ and docs/docs/."
