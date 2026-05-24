# GasRoute Oracle

x402 agent for [daydreamsai/agent-bounties#4](https://github.com/daydreamsai/agent-bounties/issues/4).

Compares live gas fees across Base, Optimism, Arbitrum, and Polygon via viem, then returns the cheapest chain with congestion and tip hints.

## Run

```bash
cd packages/daydreams-agents/gas-route-oracle
npm install
npm start
```

Default port: **8093**

## Invoke

```bash
curl http://127.0.0.1:8093/health

curl -X POST http://127.0.0.1:8093/entrypoints/route/invoke \
  -H 'content-type: application/json' \
  -d '{"chain_set":["base","optimism","arbitrum"],"calldata_size_bytes":256,"gas_units_est":180000}'
```

Returns HTTP 402 when x402 payment env is configured.
