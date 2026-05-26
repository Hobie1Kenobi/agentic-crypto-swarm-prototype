# Social broadcast — Discord, Telegram, pulse board

Extend PoCon (same Ollama pipeline as AgentHive) to run **24/7 discovery** on Discord and Telegram, enriched with **GitHub repo activity** from your existing `GITHUB_TOKEN`.

## Architecture

```
GitHub API ──┐
Oracle/worker/commerce ──► PoCon factory (Ollama) ──► artifacts/pocon/latest.json
                           │
                           ├── AgentHive (@swarm_pocon)
                           ├── Discord (rich embeds + link buttons)
                           ├── Telegram (HTML + inline keyboard)
                           └── docs/pulse-board/ (GitHub Pages dashboard)
```

**GitHub credentials** feed *content* (stars, commits, releases) — they do not post to Discord/Telegram directly. Each channel needs its own bot/webhook token.

## Setup (one-time)

### Discord

1. Create a server (or use existing) → channel **#swarm-pulse**
2. Channel settings → Integrations → **Webhooks** → New webhook
3. Copy URL → `.env.local`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_BOT_NAME=Agentic Swarm
SOCIAL_LOGO_URL=https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/assets/logo.png
```

4. **Brand the channel** (one-time hub + manual polish):

```powershell
npm run discord:hub
```

Pin the hub message in `#swarm-pulse`. Full checklist: [DISCORD_BRAND_SETUP.md](DISCORD_BRAND_SETUP.md).

Each automated post includes: logo author/footer, theme embed + SKU strip, pulse chart PNG, and **8 link buttons** (Marketplace, MCP, Live board, T54, Base, Telegram, AgentHive).

**Discovery funnel:** set `SOCIAL_DISCORD_URL` (permanent invite) — syncs to pulse board banner, AgentHive posts, Telegram keyboards, and Discord hub buttons via `npm run pocon:export-board`.

Optional: add a **Discord Bot** (Developer Portal) for slash commands later — webhooks are enough for rich embeds + link buttons.

### Telegram (your @Hobie1Kenobi account)

Telegram does **not** let apps hook into your open desktop client or post as your personal [@Hobie1Kenobi](https://t.me/Hobie1Kenobi) user automatically. The supported pattern:

- **You** (Hobie) own the **channel** in the app you already have open
- A **bot** (created via BotFather) posts PoCon pulses into that channel 24/7

#### In Telegram on your PC (logged in as Hobie)

1. **New Channel** (hamburger menu → New Channel)
   - Name: `Agentic Swarm Marketplace`
   - Description: PoCon pulses, x402 SKUs, MCP — machine-paid agent commerce
   - **Public link:** pick something like `t.me/AgenticSwarmPulse` (must be unused)

2. **Create bot** — open chat with [@BotFather](https://t.me/BotFather)
   ```
   /newbot
   Agentic Swarm PoCon
   AgenticSwarmPulseBot
   ```
   Copy the token (shown once).

3. **Add bot to channel**
   - Open your new channel → **Manage channel** → **Administrators** → **Add administrator**
   - Search for `AgenticSwarmPulseBot` → enable **Post messages** (and **Edit messages** optional)

4. **Wake the bot** — post any message in the channel (e.g. "PoCon online")

5. **Discover chat id** (repo helper):
   ```powershell
   # paste token in .env.local first, or:
   python scripts/telegram-setup.py --token YOUR_TOKEN --probe
   ```

6. **`.env.local`**
   ```env
   TELEGRAM_BOT_TOKEN=123456789:AAF...
   TELEGRAM_CHAT_ID=-1001234567890
   POCON_SOCIAL_POST=1
   SOCIAL_AGENTHIVE_URL=https://agenthive.to/agents/swarm_pocon
   ```

7. **Test**
   ```powershell
   python scripts/telegram-setup.py --test
   npm run pocon:social-post
   ```

Optional: pin the channel on your Telegram sidebar; link it from [agentic-swarm-marketplace.com](https://www.agentic-swarm-marketplace.com) and your GitHub README.

**Not supported:** logging into your personal account from Python (userbot/Telethon) — against Telegram automation rules for marketing bots and fragile on desktop sessions.

### GitHub (already likely set)

Uses `GITHUB_TOKEN` / `EARNING_WORKER_GITHUB_TOKEN` for richer posts (stars, latest commit):

```env
SOCIAL_GITHUB_REPO=Hobie1Kenobi/agentic-crypto-swarm-prototype
```

### Enable auto-post

```env
POCON_SOCIAL_POST=1
POCON_HIVE_POST=1
```

Runs inside `npm run pocon:factory:daemon` and `npm run commerce:workers:start`.

**Telegram chart posts:** each pulse renders a branded PNG (`POCON_TELEGRAM_CHART=1`) and sends via `sendPhoto` with inline buttons including **Live board**.

**Marketing rotation (`POCON_MARKETING_POST=1`, default):** each factory cycle picks a **unique theme** (T54/XRPL, Base x402, Celo, MCP, Bazaar, each SKU, Telegram, AgentHive, GitHub, …). Ollama writes fresh copy; chart header and CTA buttons match the theme. Preview: `npm run pocon:marketing-preview`.

**GitHub Pages board:** auto-exported each factory cycle to `docs/pulse-board/` (`POCON_EXPORT_BOARD=1`) — JSON + `pulse-chart.png`. Deploy by committing `docs/pulse-board/` or your Pages workflow.

## Commands

```powershell
npm run discord:hub                     # one-time branded channel index (pin in Discord)
npm run pocon:social-post              # manual Discord + Telegram
npm run pocon:social-post -- --force    # re-post same pulse_id
npm run pocon:export-board              # sync pulse.json → GitHub Pages
npm run pocon:marketing-preview         # preview next marketing theme + copy
```

Pulse board URL (after export + Pages deploy):

`https://hobie1kenobi.github.io/agentic-crypto-swarm-prototype/pulse-board/`

## Cadence

| Channel | Default | Notes |
|---------|---------|-------|
| PoCon factory | 1h (`POCON_INTERVAL_SEC`) | One pulse drives all channels |
| AgentHive | 3 posts/pulse | headline + 2 signals |
| Discord/Telegram | 1 rich post/pulse | embed + inline links |
| Pulse board | on export | auto-refresh every 5 min in browser |

For **more frequent** Telegram/Discord without re-running Ollama, add a lightweight “signal-only” loop later (`SOCIAL_SIGNAL_INTERVAL_SEC`) that posts top bazaar/worker deltas between hourly pulses.

## Interactive presence roadmap

| Phase | Deliverable |
|-------|-------------|
| **Now** | Webhook embeds, Telegram keyboards, pulse board |
| **Next** | Discord Bot slash commands: `/pulse`, `/skus`, `/mcp` |
| **Next** | Telegram bot commands + `/start` menu |
| **Later** | Canvas/React live board on custom domain with x402 paywall teaser |
| **Later** | Auto-export pulse board on each factory cycle (GitHub Action commit) |

## Constitution

Same rules as PoCon: no gambling, no illegal content, not financial advice. Social copy is derived from the same constitution-gated synthesis prompt.
