$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$venv = Join-Path $root ".venv-olas"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python not found on PATH"
}

if (-not (Test-Path $venv)) {
  Write-Host "Creating isolated venv at $venv ..."
  python -m venv $venv
}

$py = Join-Path $venv "Scripts\\python.exe"
if (-not (Test-Path $py)) {
  throw "Venv python not found at $py"
}

Write-Host "Upgrading pip in isolated venv..."
& $py -m pip install --upgrade pip

# Install mech-client + its pinned dependencies inside the isolated venv.
Write-Host "Installing mech-client in isolated venv..."
& $py -m pip install "mech-client==0.20.0"

$mechx = Join-Path $venv "Scripts\\mechx.exe"
if (Test-Path $mechx) {
  Write-Host ""
  Write-Host "Installed mechx:"
  Write-Host "  $mechx"
  Write-Host ""
  Write-Host "Next:"
  Write-Host "  Set OLAS_MECHX_PATH=$mechx in your .env (optional), or the adapter will auto-detect .venv-olas."
} else {
  Write-Host "Warning: mechx.exe not found in $venv\\Scripts (install may have failed)."
}

