# Forward Stripe webhooks to the local marketplace API (Stripe CLI).
# 1) Install: https://stripe.com/docs/stripe-cli
# 2) stripe login
# 3) Run this script; copy the "whsec_..." signing secret into STRIPE_WEBHOOK_SECRET in .env
# 4) npm run marketplace:serve (MARKETPLACE_HTTP_ENABLED=1)

$ErrorActionPreference = "Stop"
$port = if ($env:MARKETPLACE_HTTP_PORT) { $env:MARKETPLACE_HTTP_PORT } else { "8055" }
$url = "http://127.0.0.1:$port/webhooks/stripe"

$stripe = Get-Command stripe -ErrorAction SilentlyContinue
if (-not $stripe) {
    Write-Host "stripe CLI not found. Install: https://stripe.com/docs/stripe-cli" -ForegroundColor Red
    exit 1
}

Write-Host "Forwarding Stripe events to $url" -ForegroundColor Cyan
Write-Host "Paste the webhook signing secret (whsec_...) into STRIPE_WEBHOOK_SECRET in your .env" -ForegroundColor Yellow
& stripe listen --forward-to $url
