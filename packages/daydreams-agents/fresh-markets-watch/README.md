# Fresh Markets Watch

Daydreams AI bounty agent — lists new AMM `PairCreated` events within a configurable time window.

## Run locally

```bash
cd packages/daydreams-agents/fresh-markets-watch
npm install
export ADDRESS=0x408f39B19266022FeC03076091e59D1f4f163658
export NETWORK=base
export FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402
npm start
```

Health: `GET http://127.0.0.1:8091/health`

Invoke (x402 paywalled when payments env is set):

```bash
curl -X POST http://127.0.0.1:8091/entrypoints/scan/invoke \
  -H 'content-type: application/json' \
  -d '{"chain":"base","window_minutes":60}'
```

## Deployment

Proxied via unified Caddy stack at `/agents/fresh-markets-watch/*` → `:8091`.

Public URL (when stack + ngrok wired):

`https://api.agentic-swarm-marketplace.com/agents/fresh-markets-watch/health`

Start with: `npm run daydreams:fresh-markets`

## Bounty

- Issue: [daydreamsai/agent-bounties#1](https://github.com/daydreamsai/agent-bounties/issues/1)
- Acceptance: factory-filtered pair detection, enrichment fields, x402 reachable
