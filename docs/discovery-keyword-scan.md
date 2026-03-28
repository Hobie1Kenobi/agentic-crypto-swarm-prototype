# x402 discovery — keyword scan (airdrop-adjacent)

**Updated:** `2026-03-25T17:34:10Z` (UTC)  
**Disclaimer:** These are **weak signals** from public x402 discovery listings (Coinbase CDP + PayAI). A keyword match is **not** confirmation of a legitimate airdrop or claim.

## How to regenerate

```bash
npm run discovery:keywords
# or
python scripts/scan-discovery-keywords.py
```

Optional env: `DISCOVERY_KEYWORD_CONFIG`, `DISCOVERY_SCAN_MAX_ITEMS_PER_SOURCE`, `DISCOVERY_SCAN_PAGE_SIZE`, `DISCOVERY_SCAN_SLEEP_SECONDS`, `DISCOVERY_SCAN_TIMEOUT_SECONDS`.

## Summary

- **Unique resources with a hit:** 404
- **Keywords:** 28 (`airdrop, claim, reward, incentive, faucet, quest, points, season` …)

### Per source

| Source | Items scanned | Hit rows (pre-dedupe) |
|--------|---------------|------------------------|
| Coinbase CDP x402 discovery | 600 | 333 |
| PayAI facilitator discovery | 600 | 74 |

## Top hits (deduped by `resource`)

| Resource | Keywords | Sources |
|----------|----------|---------|
| https://api.questflow.ai/x402/swarm/qrn:swarm:68ea4d16101cbfe6d82a12fe | early, quest, season, token | cdp |
| https://www.402bnb.fun/api/participate | claim, eligible, participat, token | cdp |
| https://x402factory.ai/solana/coinprice | points, quest, snapshot, token | payai |
| https://api.questflow.ai/x402/swarm/qrn:swarm:688a23cbc6520a7b2678f77a | early, quest, token | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:68b9a4b04b4f3f371ab33f9a | early, quest, token | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:68fba818f205a67a3e2d6eb4 | airdrop, quest, token | cdp |
| https://www.luckymint.xyz/api/mint10x | bonus, reward, token | cdp |
| https://x402factory.ai/base/llm/gpt | points, quest, token | cdp |
| https://x402factory.ai/solana/llm/gpt | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/32X5W88Z9PATZH85T5 | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/4TC64D7MFFRX5DNRZ9 | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/6BNTBUF2DASXXWCAD2 | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/6JAF5PYRGEC8X9XYFC | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/AW5793DBAYAHSEHJTU | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/H32KZAUGYY5MPHEX62 | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/HFNPTD5QQQAMHB6NCF | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/J38T6ZGANCNB8SLZJZ | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/KCBWQQHUC8D4GQB5DT | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/KR92MHBFNW9Z7MST4E | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/M4BAZ396XPH8QAHE3X | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/NZGVSXRC6HMKB8FWDA | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/T6G59ANZRFBKRHXTHG | points, quest, token | payai |
| https://x402factory.ai/solana/llm/gpt/YXPJPFB26CSY6VTN3N | points, quest, token | payai |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:6823042fd973977d61d66bfd | early, quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:68230489d973977d61d66e9d | ecosystem, quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68245d50639b9d8f54d50eda | quest, reward | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68eca8dd7938a7458fbd26b6 | quest, token | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68ecc0ccd2f1fd7645d7e820 | quest, token | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68f5afdeb496db62cf747cf9 | quest, token | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68f7332ab496db62cf748f05 | quest, token | cdp |
| https://api-staging.intra-tls2.dctx.link/x402/agent/qrn:agent:68230489d973977d61d66e9d | ecosystem, quest | cdp |
| https://api-staging.intra-tls2.dctx.link/x402/swarm/qrn:swarm:68245d50639b9d8f54d50eda | quest, reward | cdp |
| https://api.barvis.io/token/airdrop | airdrop, token | cdp |
| https://api.delx.ai/api/v1/x402/jwt-inspect | claim, token | payai |
| https://api.moltalyzer.xyz/api/polymarket/signal | quest, season | payai |
| https://api.questflow.ai/x402/agent/qrn:agent:687df7c0b234010b7d331c25 | quest, token | cdp |
| https://api.questflow.ai/x402/agent/qrn:agent:687df7d3b234010b7d331cc4 | ecosystem, quest | cdp |
| https://api.questflow.ai/x402/agent/qrn:agent:687e2a4457b6ecbe004244af | genesis, quest | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:687e352657b6ecbe00424694 | quest, reward | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:687e3fac57b6ecbe00425788 | quest, token | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:68c770291dad762112b4735a | early, quest | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:68f2e9bf0ebd74a791201ae2 | quest, token | cdp |
| https://api.questflow.ai/x402/swarm/qrn:swarm:68f79934bd72982773eff3bf | quest, token | cdp |
| https://api.slamai.dev/chain/tokens/trending | snapshot, token | payai |
| https://arb.axryl.com/opportunities/json | quest, snapshot | cdp |
| https://blocksearch.dev/api/insights/list | airdrop, token | cdp, payai |
| https://mesh.heurist.xyz/x402/agents/AIXBTProjectInfoAgent/search_projects | ecosystem, token | cdp |
| https://mesh.heurist.xyz/x402/agents/EtherscanAgent/get_erc20_token_transfers | distribution, token | cdp |
| https://mesh.heurist.xyz/x402/agents/EtherscanAgent/get_erc20_top_holders | distribution, token | cdp |
| https://mesh.heurist.xyz/x402/agents/EvmTokenInfoAgent/get_recent_large_trades | distribution, token | cdp |
| https://mesh.heurist.xyz/x402/agents/GoplusAnalysisAgent/fetch_security_details | testnet, token | cdp |
| https://mesh.heurist.xyz/x402/agents/TrendingTokenAgent/get_trending_tokens | quest, token | cdp |
| https://mesh.heurist.xyz/x402/agents/YahooFinanceAgent/indicator_snapshot | snapshot, token | cdp |
| https://poim.io/api/x402/answer | quest, token | cdp |
| https://proof-of-intelligence-mint-web.vercel.app/API/x402/answer | quest, token | cdp |
| https://proof-of-intelligence-mint-web.vercel.app/api/x402/answer | quest, token | cdp |
| https://x402.onchainexpat.com/api/x402-crypto/token-holders | distribution, token | payai |
| https://x402factory.ai/base/ata | points, token | cdp |
| https://x402factory.ai/solana/music | points, quest | payai |
| https://x402factory.ai/solana/xprofile | points, quest | payai |
| http://api.deepnets.ai/api/clean-trending-tokens | token | cdp |
| http://api.xona-agent.com/xlayer/token/solana-market | token | payai |
| http://apiv2.laevitas.ch/api/v1/options/snapshot | snapshot | payai |
| http://x-research-x402-n3ak8.ondigitalocean.app/x402/read | distribution | payai |
| http://x-research.suzi.trade/x402/accounts-feed/20 | distribution | payai |
| http://x-research.suzi.trade/x402/read | distribution | payai |
| http://x-research.suzi.trade/x402/search/100 | distribution | payai |
| http://x-research.suzi.trade/x402/search/20 | distribution | payai |
| http://x-research.suzi.trade/x402/thread/100 | distribution | payai |
| http://x-research.suzi.trade/x402/trending/general | distribution | payai |
| http://x-research.suzi.trade/x402/trending/solana | distribution | payai |
| https://agent.collabrachain.fun/api/polymarket/discovery/early-movers | early | payai |
| https://agent.collabrachain.fun/api/token-screener/rugger | token | payai |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:682303bfd973977d61d66a38 | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:68230442d973977d61d66ccb | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:68230447d973977d61d66ce1 | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:68230461d973977d61d66dad | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:6823047dd973977d61d66e5f | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:6823065f5380bd59df4992e4 | quest | cdp |
| https://api-dev.intra-tls2.dctx.link/x402/agent/qrn:agent:682306635380bd59df4992fa | quest | cdp |

## Machine-readable

- Repo: `external_commerce_data/discovery-keyword-scan-summary.json`
- Pages mirror: [`discovery-keyword-scan.json`](discovery-keyword-scan.json)

## Pair with Airdrop Scout

Use interesting `resource` URLs as `--context` for `scripts/run-airdrop-scout.py` for LLM Farm Score + rationale. See `docs/AIRDROP_INTELLIGENCE_AGENT.md`.
