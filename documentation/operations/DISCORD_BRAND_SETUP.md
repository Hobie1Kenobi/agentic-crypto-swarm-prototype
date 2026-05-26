# Discord — premier channel branding

Make `#swarm-pulse` (and your server) look like the flagship agent-commerce hub.

## One-command hub post (do this first)

Posts a **4-embed index** with logo author, rail guide, SKU strip, and community links + **8 link buttons**:

```powershell
npm run discord:hub
```

Then in Discord: **right-click the hub message → Pin Message**.

## Manual Discord app polish (~10 min)

Do these in the Discord desktop app while logged in as server owner.

### Server identity

| Setting | Action |
|---------|--------|
| **Server icon** | Server settings → Upload `assets/logo.png` (1024×1024) |
| **Server banner** | Boost Level 2+ → use logo on dark gradient background |
| **Description** | "Premier agent↔agent web3 commerce — x402, T54 XRPL, Base USDC, Celo, MCP" |
| **Invite splash** | Same logo + tagline |

### Channel layout (recommended)

Create category **AGENTIC SWARM MARKETPLACE**:

| Channel | Purpose |
|---------|---------|
| `#swarm-pulse` | Automated PoCon + marketing (webhook) — **pin hub here** |
| `#skus-and-rails` | Optional FAQ / pinned SKU list (copy from hub embed) |
| `#mcp-help` | Optional — link to mcp-integration.md |
| `#community` | Discussion group linked to `#swarm-pulse` for comments |

### `#swarm-pulse` channel settings

- **Topic:** `Hourly PoCon · x402 · T54 XRPL · Base USDC · Celo · MCP · agentic-swarm-marketplace.com`
- **Slow mode:** Off (bot-only posts)
- **Reactions:** Enable — suggest custom: 📡 🤖 🔗 ⚡
- **Webhook:** Name `Agentic Swarm` · avatar = logo (re-upload from `assets/logo.png`)

### Community features (optional, high impact)

1. Server settings → **Enable Community**
2. Set **rules channel** + **updates channel** (`#swarm-pulse` works as updates)
3. **Server Widget** → enable → embed on your marketing site
4. Link **Telegram** + **AgentHive** in server **Welcome Screen**

### Accent / appearance

- Server settings → **Profile** → accent color → pick **teal** `#00d4aa` (matches logo)
- User settings → **Appearance** → sync with server theme

## What every automated post includes (code)

After this update, each Discord marketing post has:

- **Author bar** — Agentic Swarm Marketplace + logo
- **Branded footer** — logo + tagline
- **Thumbnail** — logo
- **Chart image** — logo top-right on PNG
- **2 embeds** — theme story + Quick SKU strip
- **2 button rows** — Marketplace, MCP, Live board, T54, Base, Telegram, AgentHive

## Env

```env
DISCORD_WEBHOOK_URL=...
DISCORD_BOT_NAME=Agentic Swarm
SOCIAL_LOGO_URL=https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/assets/logo.png
```

Commit `docs/assets/logo.png` so Discord can load thumbnail/author icons from the web.

### Permanent invite (discovery funnel)

1. Discord → **Server Settings → Invite People** → create **never expires** link
2. Add to `.env.local`:

```env
SOCIAL_DISCORD_URL=https://discord.gg/your-invite
```

3. Sync everywhere:

```powershell
npm run pocon:export-board   # pulse board banner + links.json
npm run discord:hub          # optional — refresh hub embeds with Discord button
```

AgentHive marketing posts and Telegram keyboards pick up the same URL automatically.

## Next level (optional)

- **Discord Bot application** (Developer Portal) for slash commands: `/pulse`, `/skus`, `/mcp`
- **Server template** — export after layout is final, share with partners
- **Stage channel** — occasional live PoCon walkthroughs

See also: [SOCIAL_BROADCAST.md](SOCIAL_BROADCAST.md)
