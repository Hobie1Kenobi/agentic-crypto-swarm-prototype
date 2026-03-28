# Unpaid probe: expect HTTP 402 from api_seller_x402 (seller must be running).
$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "packages\agents"
python (Join-Path $Root "scripts\probe-x402-seller.py") @args
exit $LASTEXITCODE
