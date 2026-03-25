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
- `docs/robots.txt` — Crawler rules (allows indexing; points to `sitemap.xml`)
- `docs/sitemap.xml` — URL list for search engines (does not replace Search Console)
- `docs/google*.html` — Google Search Console HTML file verification (one-time; keep if re-verifying)
- `docs/site-data.json` — Metrics, contracts, report links (for future JS use)
- Other files in `docs/` (ARCHITECTURE.md, etc.) are accessible if linked

### Search indexing (how it actually works)

- **`robots.txt`** does not register your site with Google or “broadcast” it. It only tells crawlers which paths they are allowed to fetch. Blocking everything (`Disallow: /`) would *prevent* indexing; an **Allow** policy lets normal indexing proceed.
- **Discovery** still depends on **links from other sites**, **sitemap** hints, **`meta` / Open Graph** on pages, and time. For measurable SEO, add the property in **[Google Search Console](https://search.google.com/search-console)** (and optionally Bing Webmaster Tools) and submit `sitemap.xml` there.

#### Google Search Console — sitemap URL (must be full path)

Project Pages sites live **under the repo name**, not at the root of `github.io`.

- **Correct sitemap URL to submit:**  
  `https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/sitemap.xml`
- **Wrong (404):** `https://hobie1kenobi.github.io/sitemap.xml` — that path is not this project; Google will show **“Sitemap could not be read”** and **0** discovered URLs.

Use the **same URL prefix** property as the site: `https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/`. If you already submitted the wrong URL, remove it in GSC and add the full URL above, then **Request validation** / wait for recrawl (often within a few days).

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
