# agentic-swarm-marketplace.com — GitHub Pages + Cloudflare Tunnel

Use this domain in three roles:

| Hostname | Purpose |
|----------|---------|
| **`www.agentic-swarm-marketplace.com`** | Static **GitHub Pages** site (`docs/` — layout, `endpoints.json`, `llms.txt`) |
| **`api.agentic-swarm-marketplace.com`** | **Live sellers** via Cloudflare Tunnel → unified Caddy **:9080** (`/x402/*`, `/t54/*`) |
| **`agentic-swarm-marketplace.com` (apex)** | Optional: redirect to `www` in Cloudflare, or point apex at GitHub Pages (A records below) |

Your GoDaddy screenshot shows **`@` → WebsiteBuilder** and **`www` → apex**. For this setup you will **remove the Website Builder apex** and **point `www` at GitHub**, not at the bare domain.

---

## Part A — Add the domain to Cloudflare (recommended)

Cloudflare Tunnel **public hostnames** need DNS in **Cloudflare** for your zone. Easiest path: **move nameservers** from GoDaddy to Cloudflare (free plan is enough).

1. Sign up at [Cloudflare](https://dash.cloudflare.com/) → **Add a site** → enter `agentic-swarm-marketplace.com`.
2. Cloudflare will show **two nameservers** (e.g. `xxx.ns.cloudflare.com`).
3. In **GoDaddy** → your domain → **Nameservers** → **Change** → **Custom** → paste Cloudflare’s two nameservers → Save.
4. Wait for propagation (often 15 minutes–24 hours). Cloudflare will email when active.

After this, **edit DNS only in Cloudflare**, not GoDaddy.

---

## Part B — DNS records in Cloudflare

### 1) GitHub Pages (`www`)

**Option B1 — `www` only (simplest)**

| Type | Name | Target / value | TTL |
|------|------|----------------|-----|
| **CNAME** | `www` | `hobie1kenobi.github.io` | Auto |

GitHub Pages (project site): [Managing a custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site).

**Option B2 — Apex `@` for the same site**

If you want `https://agentic-swarm-marketplace.com` (no `www`) to load Pages, add GitHub’s **A** records for `@`:

| Type | Name | Value |
|------|------|--------|
| **A** | `@` | `185.199.108.153` |
| **A** | `@` | `185.199.109.153` |
| **A** | `@` | `185.199.110.153` |
| **A** | `@` | `185.199.111.153` |

(From [GitHub Pages IP addresses](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site#configuring-an-apex-domain).)

Remove any **conflicting** `@` record (e.g. GoDaddy Website Builder).

### 2) API tunnel (`api`)

After the tunnel is created (Part C), Cloudflare usually creates a **CNAME** for `api` → `xxxx.cfargotunnel.com`. If not, add the CNAME **exactly** as shown in **Zero Trust → Networks → Tunnels → your tunnel → Public hostname**.

---

## Part C — GitHub repo: attach the custom domain

Repo: `Hobie1Kenobi/agentic-crypto-swarm-prototype`, Pages source: **`/docs`** on `master`/`main`.

1. GitHub → **Settings → Pages → Custom domain**.
2. Enter **`www.agentic-swarm-marketplace.com`** (or apex if you use A records only).
3. Save. GitHub may open a PR or add **`docs/CNAME`**; if you commit **`docs/CNAME`** yourself, it must contain **one line**:

   ```text
   www.agentic-swarm-marketplace.com
   ```

4. Wait for **DNS check** to pass, then enable **Enforce HTTPS**.

Site should load at `https://www.agentic-swarm-marketplace.com/agentic-crypto-swarm-prototype/` (project URL path unchanged unless you use a `CNAME` at repo root for user site — you’re on a **project** site, so the path remains unless you add a redirect).

---

## Part D — Cloudflare Tunnel for `api.agentic-swarm-marketplace.com`

1. Install [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. [Zero Trust](https://one.dash.cloudflare.com/) → **Networks → Tunnels** → **Create tunnel**.
3. Name it (e.g. `swarm-sellers`), install the connector on your PC, run the login command Cloudflare shows.
4. Add a **Public hostname**:
   - **Subdomain:** `api`
   - **Domain:** `agentic-swarm-marketplace.com`
   - **Service:** `http://localhost:9080`  
     (or `http://host.docker.internal:9080` if you use Docker for `cloudflared` per `scripts/cloudflare-tunnel/README.md`)

5. Locally, always run **unified Caddy** before testing:

   ```bash
   npm run x402:seller
   npm run t54:seller
   npm run proxy:unified
   ```

6. In **repo root `.env`** (never commit):

   ```env
   X402_SELLER_PUBLIC_URL=https://api.agentic-swarm-marketplace.com/x402/v1/query
   T54_SELLER_PUBLIC_BASE_URL=https://api.agentic-swarm-marketplace.com/t54
   ```

7. Refresh the public registry and commit:

   ```bash
   npm run docs:sync-endpoints
   ```

8. Commit **`docs/endpoints.json`** and push so **GitHub Pages** lists the same **`api.`** URLs.

Repo reference: `scripts/cloudflare-tunnel/README.md`, `scripts/reverse-proxy/README.md`, `documentation/PUBLIC_MAINNET_OPERATIONS.md`.

---

## Part E — Clean up GoDaddy-only records

After nameservers point to Cloudflare, **GoDaddy DNS tab no longer controls DNS**. In **Cloudflare**, do **not** copy:

- `pay` → `paylinks.commerce.godaddy.com` (only if you still need GoDaddy Commerce pay links; recreate only if required).
- Old **Website Builder** apex.

---

## Quick verification

| Check | URL |
|-------|-----|
| Pages | `https://www.agentic-swarm-marketplace.com/agentic-crypto-swarm-prototype/` |
| API health (after tunnel + Caddy) | `https://api.agentic-swarm-marketplace.com/health` |
| T54 health | `https://api.agentic-swarm-marketplace.com/t54/health` |

---

## If you must keep GoDaddy nameservers

You cannot use **Cloudflare Tunnel hostnames** on your domain the same way without the zone on Cloudflare. Options: **move NS to Cloudflare** (above), or use **another** tunnel product / VPS with a **manual** CNAME in GoDaddy to that provider. For this repo, **Cloudflare + NS migration** is the path that matches the existing docs.
