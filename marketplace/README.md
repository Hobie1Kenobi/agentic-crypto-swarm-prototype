# Marketplace — operator guide

This directory holds **sellable bundles** and **pending order files** for Stripe MPP (crypto deposit on Tempo).

## Flow

1. Set `STRIPE_SECRET_KEY` and `MARKETPLACE_DASHBOARD_BUNDLE_PRICE_USD` in `.env`.
2. Create a PaymentIntent + pending order: `npm run marketplace:order` (or enable `MARKETPLACE_HTTP_ENABLED=1` and POST to `/v1/orders` — see `documentation/marketplace-stripe/MARKETPLACE_DASHBOARD_BUNDLE.md`).
3. Buyer pays to the displayed Tempo address.
4. Verify: `npm run marketplace:verify -- --pi pi_xxx`.
5. On `succeeded`, deliver `dist/x402-strategy-dashboard-bundle-*.zip` (from `npm run marketplace:pack`).

`x402`, T54, and Celo rails continue to work independently; this path is **fiat/crypto-via-Stripe deposit** for digital goods only.
