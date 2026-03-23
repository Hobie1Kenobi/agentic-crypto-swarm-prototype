# x402 Marketplace Integration

Our swarm can interact with testnet-focused x402 agent marketplaces. This doc covers setup and usage.

## Provider Catalog (from config)

| Provider | Network | Payment | Description |
|----------|---------|---------|-------------|
| **swarm-self** | Celo Sepolia | Celo native | Our api_402 (fulfillQuery) |
| **x402-test-echo** | Base Sepolia | x402.org facilitator | Test endpoint, ~$0.01 USDC |
| **arcana-x402** | Base Sepolia | x402.org facilitator | Crypto agents (Oracle, Chain Scout, News, etc.), ~$0.03/query |
| **agoragentic** | Base | x402.org facilitator | 26+ endpoints, vault, agent-passport, commerce |
| **x402-bazaar-discovery** | Base Sepolia | Free (read-only) | Coinbase Bazaar discovery catalog |
| **x402-discovery-api** | Base | Free | 251+ indexed services, search by query/price |
| **t54-xrpl-example** | XRPL | t54 facilitator | Placeholder for XRPL x402 |

## Requirements by Marketplace Type

### Celo (swarm-self)

- `ROOT_STRATEGIST_PRIVATE_KEY`, `REVENUE_SERVICE_ADDRESS`, `RPC_URL`
- No extra deps

### Base Sepolia (Arcana, x402-test-echo, etc.)

- **Bridge (recommended):** Fund `ROOT_STRATEGIST` on **Celo Sepolia** only. The script auto-bridges USDC to Base Sepolia via [LI.FI](https://li.fi) before x402 calls. No manual Base funding.
- **Fallback:** Fund `ROOT_STRATEGIST` on Base Sepolia directly via [Coinbase CDP Faucet](https://portal.cdp.coinbase.com/products/faucet)
- **Python:** `pip install x402` (for ExactEvmScheme / payment signing)
- **Config:** `X402_TEST_FACILITATOR_URL=https://x402.org/facilitator` (default), `X402_BRIDGE_ENABLED=1` (default)

### XRPL (t54)

- See `docs/T54_XRPL_TESTNET_WORKAROUND.md`

## Discovery

### Config-based

Providers are loaded from `packages/agents/config/x402_providers.json`.

### Remote discovery

Enable with `X402_DISCOVERY_ENABLED=1`. Discovery will fetch from:

- `https://x402-discovery-api.onrender.com/discover` (251+ services)
- `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` (Bazaar)
- `https://facilitator.payai.network/discovery/resources`

## Usage

### Script: discover and test

```bash
# List providers and test x402-test-echo (needs Base Sepolia USDC + x402)
python scripts/run-x402-marketplace-test.py

# With remote discovery
X402_DISCOVERY_ENABLED=1 python scripts/run-x402-marketplace-test.py

# Dry run (no payment, just probe)
X402_DRY_RUN=1 python scripts/run-x402-marketplace-test.py
```

### Programmatic

```python
from external_commerce import Discovery, invoke_by_provider

discovery = Discovery()
providers = discovery.discover_from_config()

# Invoke by provider
for p in providers:
    if p.provider_id == "x402-test-echo":
        status, data, err = invoke_by_provider(p, params={"msg": "hello"})
        print(status, data, err)
```

## Smart Hybrid Settlement

| Path | When | Action |
|------|------|--------|
| **Testnet (faucet)** | Arcana, x402-test-echo | Check Base Sepolia USDC; print faucet links (Circle, Coinbase CDP). No bridge. |
| **Mainnet (Celo facilitator)** | `X402_USE_FACILITATOR=1` + `celo_native` provider | Try Ultravioleta/Celo facilitator — pay from Celo USDC directly. |
| **Mainnet (bridge)** | Fallback | LI.FI Celo->Base; bridge only shortfall (checks Base balance first). |

Fund Celo only; same key = same address on Base. `ensure_base_sepolia_test_usdc()` for testnet; `ensure_base_usdc_for_x402()` for mainnet.

```bash
# Test with facilitator-first (try Celo pay before bridge)
python scripts/run-x402-marketplace-test.py --facilitator-first

# Disable bridge, use facilitator only
X402_BRIDGE_ENABLED=0 X402_USE_FACILITATOR=1 python scripts/run-x402-marketplace-test.py

# Manual bridge (mainnet only; testnet uses faucet)
python scripts/bridge_utils.py --mainnet 1
python scripts/bridge_utils.py --dry-run
```

## Key Fallback

For Base marketplaces, the buyer tries keys in order:

1. `X402_BUYER_BASE_SEPOLIA_PRIVATE_KEY`
2. `X402_BUYER_PRIVATE_KEY`
3. `ROOT_STRATEGIST_PRIVATE_KEY`

Same key on Celo and Base = same address. Fund Celo, bridge on demand.

## Links

- [x402.org](https://x402.org) — Protocol and Bazaar
- [Arcana docs](https://mintlify.com/explore/Aypp23/x402-hackathon)
- [Agoragentic](https://agoragentic.com)
- [x402 Discovery API](https://github.com/rplryan/x402-discovery-mcp)
