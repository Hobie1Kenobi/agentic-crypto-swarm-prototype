# Start xrpl-x402-facilitator on XRPL testnet for local x402 development.
# Requires: pip install xrpl-x402-facilitator redis
#           Redis running on 127.0.0.1:6379
#
# Usage: .\scripts\start-xrpl-facilitator-testnet.ps1

$env:MY_DESTINATION_ADDRESS = if ($env:XRPL_RECEIVER_ADDRESS) { $env:XRPL_RECEIVER_ADDRESS } else { "rN7n7otQDd6FczFgLdlqtyMVrn3e1DjxvV" }
$env:FACILITATOR_BEARER_TOKEN = if ($env:T54_FACILITATOR_TOKEN) { $env:T54_FACILITATOR_TOKEN } else { "dev-token-replace-in-prod" }
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6379/0" }
$env:NETWORK_ID = "xrpl:1"
$env:XRPL_RPC_URL = if ($env:XRPL_RPC_URL) { $env:XRPL_RPC_URL } else { "https://s.altnet.rippletest.net:51234" }
$env:GATEWAY_AUTH_MODE = if ($env:GATEWAY_AUTH_MODE) { $env:GATEWAY_AUTH_MODE } else { "single_token" }

Write-Host "Starting xrpl-x402-facilitator (testnet) at http://127.0.0.1:8010"
Write-Host "  MY_DESTINATION_ADDRESS=$env:MY_DESTINATION_ADDRESS"
Write-Host "  NETWORK_ID=$env:NETWORK_ID"
Write-Host ""
Write-Host "Set T54_XRPL_FACILITATOR_URL=http://127.0.0.1:8010 for t54 adapter"
Write-Host ""

xrpl-x402-facilitator --host 127.0.0.1 --port 8010
