# x402 Strategy Dashboard — operator bundle

This folder is the **sellable artifact**: static viewer + catalog snapshot + legal text.

## Build the ZIP (from repo root)

1. Refresh data (optional): `npm run catalog:scout-slim`
2. Pack: `npm run marketplace:pack`

Output: `dist/x402-strategy-dashboard-bundle-<timestamp>.zip` (gitignored).

## Replace with your full dashboard (optional)

Drop your multi-tab HTML (the “Earning Strategy Dashboard”) as `static/index.html`, or keep this file and add `static/dashboard.html` and link from `index.html`. Re-run `npm run marketplace:pack` before each release.

## Serve locally

```bash
cd marketplace/bundles/x402-strategy-dashboard/static
python -m http.server 8766
```

Open `http://127.0.0.1:8766/` — the viewer loads `data/catalog-slim.json`.

## Payments (Stripe MPP)

See `documentation/marketplace-stripe/MARKETPLACE_DASHBOARD_BUNDLE.md`. Operators create orders with `npm run marketplace:order`; buyers pay to the Tempo address; you verify with `npm run marketplace:verify`.
