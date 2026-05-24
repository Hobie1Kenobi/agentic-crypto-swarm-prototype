# Slippage Sentinel

Daydreams AI bounty agent — estimates safe slippage (bps) for Uniswap V2-style routes using pool depth and recent swap volatility.

## Run

```bash
cd packages/daydreams-agents/slippage-sentinel
npm install
export ADDRESS=0x408f39B19266022FeC03076091e59D1f4f163658
export NETWORK=base
export FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402
npm start
```

Port default: **8092**

## Invoke

```bash
curl -X POST http://127.0.0.1:8092/entrypoints/estimate/invoke \
  -H 'content-type: application/json' \
  -d '{
    "chain":"base",
    "token_in":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "token_out":"0x4200000000000000000000000000000000000006",
    "amount_in":"1000000000",
    "route_hint":"uniswap-v2-base"
  }'
```

## Bounty

[daydreamsai/agent-bounties#3](https://github.com/daydreamsai/agent-bounties/issues/3)
