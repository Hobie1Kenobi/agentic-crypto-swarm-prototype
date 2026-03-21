# GitHub Pages Deployment

This site is served from the `/docs` folder via GitHub Pages.

## Activate GitHub Pages

1. Go to **Settings** → **Pages** in your GitHub repo
2. Under **Build and deployment**:
   - **Source**: Deploy from a branch
   - **Branch**: `master` (or `main`)
   - **Folder**: `/docs`
3. Click **Save**
4. The site will be available at: `https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/`

## What Gets Published

- `docs/index.html` — Main project identity page
- `docs/site-data.json` — Metrics, contracts, report links (for future JS use)
- Other files in `docs/` (ARCHITECTURE.md, etc.) are accessible if linked

## What Is Not Published

- `.env`, private keys, wallet seeds
- `deployed_local_address_manifest.json` (Anvil/local only)
- Internal root-cause or debug docs
- `node_modules/`, `venv/`, build artifacts

## Updating the Site

1. Edit `docs/index.html` or `docs/site-data.json`
2. Push to `master`
3. GitHub Pages rebuilds automatically (usually within 1–2 minutes)

### Adding New Reports

- Add the report file to the repo root (or `docs/reports/`)
- Add a link in `docs/index.html` under Reports
- Update `docs/site-data.json` if using it for dynamic content

### Updating Metrics

- After a new soak test, update the numbers in `docs/index.html` (Proof section)
- Optionally update `docs/site-data.json` for consistency
