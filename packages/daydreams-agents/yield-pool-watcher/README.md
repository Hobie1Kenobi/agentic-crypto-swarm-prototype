# Yield Pool Watcher

x402 agent for [daydreamsai/agent-bounties#6](https://github.com/daydreamsai/agent-bounties/issues/6).

Tracks APY and TVL via DefiLlama yields API, compares against cached snapshots, and fires alerts when thresholds are breached.

## Run

```bash
cd packages/daydreams-agents/yield-pool-watcher
npm install
npm start
```

Port **8096**

## Invoke

```bash
curl http://127.0.0.1:8096/health

curl -X POST http://127.0.0.1:8096/entrypoints/watch/invoke \
  -H 'content-type: application/json' \
  -d '{"protocol_ids":["aerodrome","uniswap-v3"],"pools":[],"threshold_rules":{"tvl_drop_pct":10,"apy_spike_pct":25}}'
```

Run twice to populate deltas/alerts (first call seeds cache).
