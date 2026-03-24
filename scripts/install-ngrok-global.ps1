# Installs ngrok 3.37.x to %LOCALAPPDATA%\Programs\Ngrok and makes it the default `ngrok` in shells.
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts/install-ngrok-global.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $Root ".tools\ngrok\ngrok.exe"
$DestDir = Join-Path $env:LOCALAPPDATA "Programs\Ngrok"
$DestExe = Join-Path $DestDir "ngrok.exe"

if (-not (Test-Path $Src)) {
    Write-Host "Downloading ngrok stable (Windows amd64)..."
    $zip = Join-Path $env:TEMP "ngrok-stable-win.zip"
    $url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    New-Item -ItemType Directory -Force -Path (Split-Path $Src) | Out-Null
    Expand-Archive -Path $zip -DestinationPath (Split-Path $Src) -Force
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
Copy-Item -Path $Src -Destination $DestExe -Force
Write-Host "Installed: $DestExe"
& $DestExe version

# Prepend to User PATH (helps some tools; Chocolatey may still win in cmd — see below)
$old = [Environment]::GetEnvironmentVariable("Path", "User")
if ($old -notlike "*$DestDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$DestDir;$old", "User")
    Write-Host "Prepended User PATH: $DestDir"
}

# PowerShell: prepend for every session (overrides Chocolatey order)
$profileDir = Split-Path -Parent $PROFILE
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
}
$marker = "# Swarm-Economy ngrok PATH"
$line = "`$env:Path = `"$DestDir;`$env:Path`""
if (Test-Path $PROFILE) {
    $c = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($c -notlike "*$marker*") {
        Add-Content -Path $PROFILE -Value "`n$marker`n$line`n"
        Write-Host "Updated PowerShell profile: $PROFILE"
    }
} else {
    Set-Content -Path $PROFILE -Value "$marker`n$line`n"
    Write-Host "Created PowerShell profile: $PROFILE"
}

# Optional: replace Chocolatey shim (needs Administrator)
$choco = "C:\ProgramData\chocolatey\bin\ngrok.exe"
if (Test-Path $choco) {
    Write-Host "`nChocolatey ngrok found at $choco (often 3.18.x). To make ALL terminals use 3.37+, run this script elevated once, or approve UAC below."
    $elevated = @"
Copy-Item -LiteralPath '$DestExe' -Destination '$choco' -Force
Write-Host 'Replaced Chocolatey ngrok with' (Get-Item '$choco').FullName
& '$choco' version
pause
"@
    $tmp = Join-Path $env:TEMP "replace-ngrok-admin.ps1"
    Set-Content -Path $tmp -Value $elevated -Encoding UTF8
    try {
        Start-Process powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tmp) -Verb RunAs -Wait
    } catch {
        Write-Host "UAC replace skipped or declined: $_"
    }
}

Write-Host "`nDone. Open a NEW terminal and run: ngrok version"
Write-Host "From this repo you can also run: npm run t54:ngrok"
