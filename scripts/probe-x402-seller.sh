#!/usr/bin/env bash
# Unpaid probe: expect HTTP 402 from api_seller_x402 (requires seller running on PROBE URL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/packages/agents${PYTHONPATH:+:$PYTHONPATH}"
exec python "${ROOT}/scripts/probe-x402-seller.py" "$@"
