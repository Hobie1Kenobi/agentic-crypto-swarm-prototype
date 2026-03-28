$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$manifestPath = Join-Path $root "deployed_address_manifest.json"
$envPath = Join-Path $root ".env"

if (-not (Test-Path $manifestPath)) {
    Write-Host "deployed_address_manifest.json not found"
    exit 1
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$marketplace = $manifest.compute_marketplace_address

if (-not $marketplace) {
    Write-Host "No compute_marketplace_address in manifest"
    exit 1
}

$updated = @{
    "COMPUTE_MARKETPLACE_ADDRESS" = $marketplace
    "PRIVATE_MARKETPLACE_ADDRESS" = $marketplace
}

$lines = @()
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
    foreach ($k in $updated.Keys) {
        $lines += "$k=$($updated[$k])"
    }
}

$content = $lines -join "`n"
if (-not $content.EndsWith("`n")) { $content += "`n" }
Set-Content -Path $envPath -Value $content -NoNewline:$false

Write-Host "Updated .env with COMPUTE_MARKETPLACE_ADDRESS and PRIVATE_MARKETPLACE_ADDRESS = $marketplace"
