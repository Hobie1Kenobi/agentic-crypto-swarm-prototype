# XRPL x402 discovery scan

**Updated:** `2026-03-25T18:56:10Z` UTC

Filtered public x402 listings (CDP + PayAI) for **XRPL / XRP** payment signals. Read-only.

## Commands

```bash
npm run discovery:xrpl
```

## Summary

- Unique resources: **7**

### Per source

| Source | Items scanned | XRPL-filtered rows |
|--------|---------------|---------------------|
| Coinbase CDP x402 discovery | 600 | 6 |
| PayAI facilitator discovery | 600 | 1 |

## Sample resources

- `https://mesh.heurist.xyz/x402/agents/FundingRateAgent/get_all_funding_rates`
- `https://x402-secure-api.t54.ai/x402/tools/get_api_health`
- `https://x402-secure-api.t54.ai/x402/tools/get_available_resources`
- `https://x402-secure-api.t54.ai/x402/tools/get_overall_score`
- `https://x402-secure-api.t54.ai/x402/tools/get_social_trust`
- `https://x402-secure-api.t54.ai/x402/tools/get_webpage_trust`
- `https://x402factory.ai/solana/coinprice`

## Xaman

This scan does **not** need your Xaman secret. Paying an x402 endpoint on XRPL from automation uses `XRPL_WALLET_SEED` (hot wallet) in `.env` — **not** Xaman’s signing flow. Use Xaman for manual review of URLs.
