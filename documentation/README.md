# Documentation

Long-form project manuals and runbooks live here, grouped by topic. **GitHub Pages** content stays in the repo root **`docs/`** folder (static `index.html`, `site-data.json`, hosted discovery scans, etc.).

| Folder | Contents |
|--------|----------|
| `architecture/` | System design, audits, multi-rail notes |
| _Runbook_ | **[PUBLIC_MAINNET_OPERATIONS.md](PUBLIC_MAINNET_OPERATIONS.md)** — stable HTTPS, Base mainnet USDC + XRPL mainnet XRP, syncing `docs/endpoints.json` for GitHub Pages |
| `celo-xrpl/` | Celo / XRPL rails, mainnet notes, testnet guides |
| `x402-t54-base/` | x402, T54 seller, marketplace integration, [ClawCredit (buyer-side)](x402-t54-base/CLAWCREDIT_INTEGRATION.md) |
| `marketplace-stripe/` | Marketplace + Stripe / MPP operator docs |
| `operations/` | Setup, production readiness, soak operators, realism — **[CLOUDFLARE_CACHE_AND_SECURITY.md](operations/CLOUDFLARE_CACHE_AND_SECURITY.md)** (edge cache / SSL / secrets), **[AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md](operations/AGENTIC_SWARM_MARKETPLACE_COM_SETUP.md)** (domain + tunnel + Pages) |
| `grants/` | Grant-style reports and external summaries |
| `discovery/` | Discovery scans, XRPL catalog, [airdrop intelligence](discovery/AIRDROP_INTELLIGENCE_AGENT.md), [EVM claims](discovery/AIRDROP_CLAIM_EXECUTION.md), [claim extract / verify](discovery/CLAIM_EXTRACT_AND_VERIFY.md) |
| `examples/` | JSON and other examples ([airdrop ClaimSpec templates](examples/airdrop_claim_uint256.example.json), [olas replay](examples/olas_request_replay_example.json), …) |

Paths in code comments may use the `documentation/...` prefix from the repository root.
