#!/usr/bin/env bash
# Forward Stripe webhooks to the local marketplace API (Stripe CLI).
# Usage: bash scripts/stripe-marketplace-webhook-dev.sh
set -euo pipefail
PORT="${MARKETPLACE_HTTP_PORT:-8055}"
URL="http://127.0.0.1:${PORT}/webhooks/stripe"
if ! command -v stripe >/dev/null 2>&1; then
  echo "stripe CLI not found. Install: https://stripe.com/docs/stripe-cli" >&2
  exit 1
fi
echo "Forwarding Stripe events to ${URL}"
echo "Paste the webhook signing secret (whsec_...) into STRIPE_WEBHOOK_SECRET in your .env"
exec stripe listen --forward-to "${URL}"
