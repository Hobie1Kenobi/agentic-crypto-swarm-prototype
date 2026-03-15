# Install Foundry on Windows (precompiled binaries).
# Run: .\scripts\install-foundry.ps1
$ErrorActionPreference = "Stop"
$baseUrl = "https://github.com/foundry-rs/foundry/releases/download"
$zipUrls = @(
    "$baseUrl/nightly/foundry_nightly_win32_amd64.zip",
    "$baseUrl/v1.5.4/foundry_win32_amd64.zip"
)
$zipName = Split-Path -Leaf $zipUrls[0]
$targetDir = Join-Path $env:USERPROFILE ".foundry"
$binDir = Join-Path $targetDir "bin"

if (Get-Command forge -ErrorAction SilentlyContinue) {
    Write-Host "Foundry already installed: $(forge --version)"
    exit 0
}

$zipPath = Join-Path $env:TEMP $zipName
$downloaded = $false
foreach ($zipUrl in $zipUrls) {
    try {
        Write-Host "Downloading $zipUrl ..."
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
        $downloaded = $true
        break
    } catch {
        Write-Host "Failed, trying next..."
    }
}
if (-not $downloaded) { throw "Could not download Foundry from any URL" }

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Expand-Archive -Path $zipPath -DestinationPath $binDir -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

$pathAdd = ";$binDir"
if ($env:PATH -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", $env:Path + $pathAdd, "User")
    $env:Path += $pathAdd
    Write-Host "Added $binDir to PATH (User). Restart terminal or run: `$env:Path += `"$pathAdd`""
}

Write-Host "Foundry installed at $binDir"
& (Join-Path $binDir "forge.exe") --version
