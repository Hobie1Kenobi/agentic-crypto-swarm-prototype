# Cloudflare: cache, SSL, and secrets (production API host)

Use this after **`api.<your-domain>`** points at a **Cloudflare Tunnel** and serves **Caddy :9080** (x402, T54, marketplace, webhooks).

## SSL/TLS

- **SSL/TLS** → recommended mode for tunnels: **Full** (not “Flexible”). The tunnel connects to your origin over **HTTP** on localhost; HTTPS terminates at the Cloudflare edge.

## Cache (avoid caching paid / dynamic APIs)

Paid routes return **402**, **JSON**, and **Set-Cookie**-style behavior — caching them can confuse buyers and agents.

1. **Caching** → **Configuration** → **Cache Rules** → **Create rule**.
2. **Rule name:** e.g. `Bypass API and webhooks`.
3. **When incoming requests match:** **Hostname** equals `api.agentic-swarm-marketplace.com` (or your API host).
4. **Optional path refinement:** URI Path contains `/x402` **OR** `/t54` **OR** `/webhooks` **OR** `/mcp` (adjust to match your routes).
5. **Then:** **Bypass cache** (or **Eligible for cache** → **Bypass**).

You can add a second rule for **`www`** if you only want to cache static assets there; GitHub Pages already serves the site from GitHub’s edge.

## WAF and bots

- Default **Managed rules** are fine to start. If legitimate x402 clients get blocked, use **Security Events** to tune or add an exception for your buyer IPs (short-lived).

## Secrets hygiene

- **Never commit** `.env`, `.env.local`, `.env.mainnet`, or tunnel **`credentials.json`** (repo `.gitignore` already lists these).
- If any key was ever pasted into a ticket, chat, or screenshot, **rotate** it (Stripe, CDP, RPC keys, seeds).
- Prefer **separate** keys for **buy** vs **receive** roles where the repo documents that split.

## Stripe webhooks (marketplace / MPP)

If you use **Stripe MPP**, set the dashboard webhook URL to your public API origin, e.g. **`https://api.agentic-swarm-marketplace.com/webhooks/stripe`**, matching **`MARKETPLACE_PUBLIC_BASE_URL`** and your app routes. Remove any old **ngrok** webhook endpoints.

## Related

- [PUBLIC_MAINNET_OPERATIONS.md](../PUBLIC_MAINNET_OPERATIONS.md) — public URLs and rails  
- [AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md](./AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md) — DNS + tunnel + Pages  
