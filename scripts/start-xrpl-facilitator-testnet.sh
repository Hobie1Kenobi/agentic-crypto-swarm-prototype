#!/usr/bin/env bash
# Start xrpl-x402-facilitator on XRPL testnet for local x402 development.
# Requires: pip install xrpl-x402-facilitator redis
#           Redis running on 127.0.0.1:6379
#
# Usage: ./scripts/start-xrpl-facilitator-testnet.sh

export MY_DESTINATION_ADDRESS="${XRPL_RECEIVER_ADDRESS:-rN7n7otQDd6FczFgLdlqtyMVrn3e1DjxvV}"
export FACILITATOR_BEARER_TOKEN="${T54_FACILITATOR_TOKEN:-dev-token-replace-in-prod}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export NETWORK_ID=xrpl:1
export XRPL_RPC_URL="${XRPL_RPC_URL:-https://s.altnet.rippletest.net:51234}"
export GATEWAY_AUTH_MODE="${GATEWAY_AUTH_MODE:-single_token}"

echo "Starting xrpl-x402-facilitator (testnet) at http://127.0.0.1:8010"
echo "  MY_DESTINATION_ADDRESS=$MY_DESTINATION_ADDRESS"
echo "  NETWORK_ID=$NETWORK_ID"
echo ""
echo "Set T54_XRPL_FACILITATOR_URL=http://127.0.0.1:8010 for t54 adapter"
echo ""

exec xrpl-x402-facilitator --host 127.0.0.1 --port 8010
