# Migration Audit: Base Sepolia → Celo-First Production

**Purpose:** Transform the repo from Base Sepolia–centered prototype to Celo-first (Celo Sepolia testnet, Celo mainnet production) while preserving architecture and keeping optional Polygon/x402 paths.

---

## 1. Migration audit summary

### 1.1 Hardcoded Base / Base Sepolia / 84532 references

| Location | Type | Detail |
|----------|------|--------|
| **foundry.toml** | RPC | `base_sepolia = "https://base-sepolia.g.alchemy.com/v2/"` |
| **.env.example** | Default | `CHAIN_ID=84532`, comments "Base Sepolia" |
| **.cursor/rules/AGENTS.md** | Doc | "Base Sepolia only (chain ID 84532)" |
| **scripts/deploy.ps1** | RPC fallback | `https://base-sepolia.g.alchemy.com/v2/$ALCHEMY_API_KEY`, `https://sepolia.base.org` |
| **scripts/deploy-dao.ps1** | RPC fallback | Same as deploy.ps1 |
| **scripts/fetch-and-save-addresses.ps1** | Chain order | `$chainIds = @(84532, 31337)`; default path `broadcast\Deploy.s.sol\84532` |
| **packages/wallet/scripts/create-accounts.ts** | Chain + RPC | `baseSepolia` from viem/chains; RPC list Base Sepolia only; fallback `https://sepolia.base.org` |
| **packages/wallet/scripts/test-userop.ts** | Chain + RPC + Explorer | `baseSepolia`; bundler `https://api.pimlico.io/v2/84532/rpc`; explorer `https://sepolia.basescan.org/tx/` |
| **packages/agents/simulation_run.py** | Default CHAIN_ID | `os.getenv("CHAIN_ID", "84532")` (3 places) |
| **packages/agents/api_402.py** | RPC + CHAIN_ID | `get_rpc()` Alchemy Base + sepolia.base.org; `CHAIN_ID` default 84532 |
| **packages/agents/swarm/nodes.py** | RPC | `_get_rpc()` same Base Sepolia fallbacks |
| **packages/agents/miner_service.py** | RPC + CHAIN_ID | Same pattern; default CHAIN_ID 84532 |
| **packages/agents/validator_bot.py** | RPC + CHAIN_ID | Same pattern |
| **packages/agents/pay_and_get_tx_hash.py** | CHAIN_ID | Default 84532 |
| **README.md** | Doc | "Base Sepolia", Basescan, basefaucet.com, CDP faucet, "Testnet only: Base Sepolia (84532)" |
| **docs/ARCHITECTURE.md** | Doc | "Testnet ETH via faucet", "Alchemy Base Sepolia", "Base Sepolia" in table |
| **docs/SETUP.md** | Doc | "Base Sepolia Faucet", deploy URL base-sepolia.g.alchemy.com |
| **docs/COMPUTE_MARKETPLACES_AND_DAOS.md** | Doc | "Base Sepolia / Anvil", "Base is supported" for x402 |

### 1.2 Pimlico / Base-specific bundler

| Location | Detail |
|----------|--------|
| **.env.example** | `PIMLICO_API_KEY` (no chain-agnostic bundler URL) |
| **packages/wallet/scripts/test-userop.ts** | Hardcoded `https://api.pimlico.io/v2/84532/rpc` (Base Sepolia only) |

Pimlico may support other chains via different chain IDs; bundler URL should be derived from chain config or env.

### 1.3 Scripts assuming ETH / Base

- **deploy.ps1, deploy-dao.ps1:** Use `RPC_URL` or Alchemy Base fallback; no Celo RPC fallback.
- **fetch-and-save-addresses.ps1:** Prefers chain 84532 then 31337; no 44787 (Celo Sepolia) or 42220 (Celo mainnet).
- **create-accounts.ts:** Uses viem `baseSepolia`; chain is fixed.
- **test-userop.ts:** Same; explorer and bundler are Base-only.

### 1.4 Docs promising Base-only behavior

- README: "Testnet only: Base Sepolia (84532). Never mainnet."
- AGENTS.md: "Base Sepolia only (chain ID 84532)".
- ARCHITECTURE.md, SETUP.md: Base Sepolia faucet and RPC.

### 1.5 Simulation assumptions

- **simulation_run.py:** Uses `CHAIN_ID` and `get_rpc()`; default 84532; no Celo-specific logic.
- **run-local-simulation.ps1, run-local-orchestration.ps1, deploy-local-only.ps1:** Use Anvil (31337) and local RPC; no Base dependency.
- Local path is already chain-agnostic (Anvil + .env.local).

### 1.6 x402 coupling

- **api_402.py:** Uses generic `get_rpc()` and `CHAIN_ID`; payment is native token to `AgentRevenueService`. Not tied to Base except via current RPC/CHAIN_ID defaults.
- **COMPUTE_MARKETPLACES_AND_DAOS.md:** Mentions "Base is supported" for x402; optional Polygon path already documented.
- **Conclusion:** x402 code is not tightly coupled to Base; it uses env-driven RPC and chain ID. Isolate behind payment-provider abstraction later; for migration, switching defaults to Celo is enough.

---

## 2. Files to change (excluding lib/, broadcast/, cache/)

| Priority | File | Changes |
|----------|------|---------|
| 1 | **New: config/chains.ts** (or .json + loader) | Canonical chain config (name, chainId, rpcEnv, explorer, native symbol, etc.) |
| 2 | **New: packages/agents/config.py** | Chain/config module for Python (or shared JSON read by all) |
| 3 | **foundry.toml** | Add celo_sepolia, celo_mainnet; keep base_sepolia as legacy; document |
| 4 | **.env.example** | CHAIN_ID=44787, CHAIN_NAME, RPC_URL, CELO_* URLs, EXPLORER_URL; mark Base optional |
| 5 | **scripts/deploy.ps1** | Use chain-aware RPC (from env CHAIN_ID or CHAIN_NAME); Celo fallbacks |
| 6 | **scripts/deploy-dao.ps1** | Same |
| 7 | **scripts/fetch-and-save-addresses.ps1** | Chain order 44787, 42220, 31337; default path from CHAIN_ID |
| 8 | **packages/wallet/scripts/create-accounts.ts** | Chain from env (celoSepolia / celo / anvil); RPC list Celo-first |
| 9 | **packages/wallet/scripts/test-userop.ts** | Chain and bundler from config; explorer URL from config |
| 10 | **packages/agents/simulation_run.py** | Default CHAIN_ID 44787; get_rpc() from shared config or chain-aware fallbacks |
| 11 | **packages/agents/api_402.py** | Same |
| 12 | **packages/agents/swarm/nodes.py** | _get_rpc() from shared config |
| 13 | **packages/agents/miner_service.py** | Same |
| 14 | **packages/agents/validator_bot.py** | Same |
| 15 | **packages/agents/pay_and_get_tx_hash.py** | CHAIN_ID default from config |
| 16 | **.cursor/rules/AGENTS.md** | Celo Sepolia / Celo mainnet; Base optional |
| 17 | **README.md** | Celo-first; Celo Sepolia faucet; explorer; optional Base/Polygon |
| 18 | **docs/ARCHITECTURE.md** | Celo RPC, testnet/mainnet; optional Base |
| 19 | **docs/SETUP.md** | Celo Sepolia deploy and faucet |
| 20 | **docs/COMPUTE_MARKETPLACES_AND_DAOS.md** | Celo-first; Polygon optional for x402 |

Contracts: **No changes** for chain migration (no 84532 or Base in contracts; `ether` is unit only).

---

## 3. Dependency / risk report

| Risk | Mitigation |
|------|------------|
| **viem chains** | Use `celoSepolia`, `celo` from viem/chains; ensure version supports Celo. |
| **Pimlico** | May not support Celo Sepolia/Celo mainnet; document as optional; keep signer/EOA path as default for Celo. |
| **ERC-4337 on Celo** | Celo has AA support; entry point may differ; create-accounts/test-userop must use chain-appropriate entry point. |
| **Alchemy** | Alchemy has Celo RPC; use CELO_SEPOLIA_RPC_URL or generic RPC_URL; avoid hardcoding Base. |
| **Explorer** | Celo: explorer.celo.org (mainnet), celo-sepolia.blockscout.com or similar for Sepolia; document. |
| **Faucet** | Celo Sepolia has faucets; document in README/SETUP. |
| **Native token** | Celo uses CELO (not ETH); contracts use msg.value (same wei semantics). Logging "ETH" can stay for local/Anvil; use "native" or CHAIN_NATIVE_SYMBOL in docs. |

---

## 4. Recommended execution order

1. **Phase 0 (this audit)** — Done.
2. **Phase 1 — Chain abstraction**  
   - Add shared chain config (JSON or TS + Python-readable).  
   - Add `config/chains.json` (or `config/chains.ts`) with: anvil, celo_sepolia, celo_mainnet, base_sepolia (legacy), polygon_amoy, polygon_mainnet.  
   - Add `packages/agents/config.py` (or use single JSON) for Python.  
   - Update `.env.example` with CHAIN_NAME, CHAIN_ID, RPC_URL, CELO_RPC_URL, EXPLORER_URL, etc.
3. **Phase 2 — Celo-first migration**  
   - foundry.toml: add celo_sepolia, celo_mainnet.  
   - Default CHAIN_ID → 44787 (Celo Sepolia); default RPC fallbacks → Celo.  
   - deploy.ps1, deploy-dao.ps1, fetch-and-save-addresses.ps1: use chain-aware RPC and chain IDs (44787, 42220, 31337).  
   - Wallet: create-accounts.ts and test-userop.ts use chain from env (celoSepolia/celo/anvil).  
   - Agents: all get_rpc() and CHAIN_ID defaults from config/Celo.  
   - Docs: README, ARCHITECTURE, SETUP, AGENTS.md, COMPUTE_MARKETPLACES_AND_DAOS: Celo-first, Base optional.
4. **Phases 3–11** — Per original plan (ERC-4337 review, contract hardening, payment layer, orchestration, local harness, Celo Sepolia path, production readiness, tests, documentation).

---

## 6. Phase 1 & 2 implementation summary (done)

- **config/chains.json** added: anvil, celo-sepolia (11142220), celo-mainnet (42220), base-sepolia (legacy), polygon-amoy, polygon-mainnet. Default chain: celo-sepolia.
- **packages/agents/config/chains.py** added: get_chain_id(), get_rpc(), get_explorer_url(), get_native_symbol(), get_chain_config(); reads CHAIN_ID/CHAIN_NAME and config/chains.json.
- **.env.example** updated: CHAIN_NAME=celo-sepolia, CHAIN_ID=11142220, CELO_* RPC vars, EXPLORER_URL; Base marked legacy.
- **foundry.toml** updated: anvil, celo_sepolia, celo_mainnet, base_sepolia, polygon_amoy, polygon_mainnet RPC endpoints.
- **scripts/deploy.ps1, deploy-dao.ps1**: RPC resolution by CHAIN_ID (31337, 11142220, 42220, 84532) with Celo defaults.
- **scripts/fetch-and-save-addresses.ps1**: chain order 11142220, 42220, 31337, 84532; default path 11142220.
- **packages/agents**: simulation_run.py, api_402.py, swarm/nodes.py, miner_service.py, validator_bot.py, pay_and_get_tx_hash.py now use config.chains (get_rpc, get_chain_id).
- **packages/wallet**: create-accounts.ts and test-userop.ts use getChain()/getRpcUrl()/getExplorerUrl() with Celo Sepolia (11142220) and Celo mainnet (42220); Base Sepolia (84532) and Anvil (31337) supported.
- **Docs**: .cursor/rules/AGENTS.md, README.md, docs/ARCHITECTURE.md, docs/SETUP.md updated for Celo-first; Base optional/legacy.

**Risks:** Pimlico bundler remains Base Sepolia–only; test-userop uses BUNDLER_RPC_URL or skips when not Base. Celo AA can be wired later via a Celo-capable bundler.

---

## 7. Phase 5 — Contract hardening (done)

- **AgentRevenueService.sol**: Emit `FeeDistributed(treasury, protocolFee)` and `FeeDistributed(financeDistributor, distributable)` in `fulfillQuery` for audit trail; added `setTreasury(address)` for owner (symmetry with `setFinanceDistributor`).
- **AgentRevenueService.t.sol**: Added tests for `FeeDistributed` emissions, remainder-in-contract, `setTreasury`, and `setFinanceDistributor`. All 10 Forge tests pass (7 AgentRevenueService + 3 ComputeMarketplace).

---

## 8. Phase 6 — Payment layer (done)

- **services/payment.py**: Centralized `MIN_PAYMENT_WEI`, `REVENUE_ABI`, `get_min_payment_wei()` (env `PAYMENT_WEI` override), and `verify_payment_tx()` for on-chain payment verification.
- **api_402.py**: Uses payment module for verification and constants; 402 response and headers include `native_symbol` (CELO/ETH) from chain config; new header `X-Payment-Native-Symbol`.
- **simulation_run.py**, **pay_and_get_tx_hash.py**: Use `get_min_payment_wei()` and `REVENUE_ABI` from `services.payment` so payment logic is single-sourced.
- **Docs**: ARCHITECTURE.md section 3.1 "Payment layer (x402)"; .env.example optional `PAYMENT_WEI`.

---

## 9. Phase 7 — Local-first test harness (done)

- **One command:** `npm run harness:local` runs `scripts/local-harness.ps1`: start/connect Anvil → deploy → write `.env.local` with deterministic keys (one Anvil key for all agents) → run full orchestration (LangGraph + simulation + finance) → generate **simulation_report.json** and **simulation_report.md** in repo root.
- **Reset:** `npm run harness:local:reset` stops Anvil (if running), starts fresh, then same flow for a clean chain.
- **No faucet:** All agent keys set to Anvil’s first account (pre-funded 10,000 ETH). No `create-accounts` or testnet needed.
- **Repeatable:** Re-run without `-Reset` reuses the same chain and `.env.local`.
- **Report generator:** `scripts/generate-simulation-report.py` parses `simulation_log.txt`, optionally fetches balances from RPC (using `.env.local`), writes structured JSON and Markdown summary (tx hashes, distribution, threshold_met, balances).
- **Unified scripts:** `run-local-simulation.ps1` and `run-local-orchestration.ps1` now call the report generator at the end; `.env.local` includes all agent keys. `harness:local` is the canonical full-system validation path.
- **Docs:** README and SETUP.md updated with local harness section; npm scripts: `harness:local`, `harness:local:reset`, `simulation:local`, `orchestrate:local`.

---

## 10. Phase 8 — Celo Sepolia public test path (done)

- **docs/CELO-SEPOLIA-TESTNET.md:** Documented 8-step flow: (1) set env vars, (2) create/import agent wallets, (3) deploy contracts, (4) fund required accounts, (5) run orchestration, (6) monitor balances, (7) verify distributions, (8) inspect events in explorer. Includes quick reference table, deploy/run command examples, and troubleshooting (PRIVATE_KEY, insufficient funds, RPC, wrong chain, distribution threshold, REVENUE_SERVICE_ADDRESS, max-steps, faucet).
- **.env.example:** Celo Sepolia comment and `CONSTITUTION_ADDRESS` added.
- **package.json:** `testnet:celo` script runs `scripts/run-celo-sepolia-e2e.ps1`.
- **scripts/celo-sepolia-balances.ps1:** Prints Celo Sepolia balances for ROOT_STRATEGIST, FINANCE_DISTRIBUTOR, REVENUE_SERVICE, BENEFICIARY from `.env` (requires Foundry `cast`).
- **SETUP.md / README:** Celo Sepolia section points to CELO-SEPOLIA-TESTNET.md; short path and balance script referenced.

---

## 11. Phase 9 — Production readiness (done)

- **docs/PRODUCTION-READINESS.md:** Single doc covering: (1) production deployment checklist, (2) security checklist, (3) operational checklist, (4) secrets handling guidance, (5) monitoring/alerting recommendations, (6) wallet key management guidance, (7) upgrade/governance notes, (8) economic risk notes, (9) abuse/spam considerations for pay-per-query, (10) rate limit and circuit breaker recommendations, (11) accounting/audit log recommendations, (12) DAO/governance review and minimal safe launch recommendation.
- **DAO recommendation:** DAO (SwarmGovernor + Timelock + token) is **optional/advanced** for v1. Minimal safe launch: do not deploy DAO on mainnet; keep `AgentRevenueService` owned by EOA or multisig. Gate DAO behind `npm run deploy:dao` and document in COMPUTE_MARKETPLACES_AND_DAOS.md and README.
- **README.md:** New "Production readiness" section linking to PRODUCTION-READINESS.md and v1 minimal launch (no DAO).
- **SETUP.md:** New "Production (Celo mainnet)" section linking to PRODUCTION-READINESS.md.
- **COMPUTE_MARKETPLACES_AND_DAOS.md:** Production v1 note added: deploy without DAO; DAO optional/advanced.

---

## 12. Phase 10 — Tests (done)

**Contracts (Forge):**
- **AgentRevenueService.t.sol:** 18 tests. Fee split correctness (exact min, large value, remainder in contract), minimum payment enforcement (revert below min), pause/unpause and pause-only blocks fulfillQuery, admin-only (setTreasury, setFinanceDistributor, pause, unpause revert when non-owner), constructor reverts for zero treasury/finance, QueryFulfilled and FeeDistributed emissions, TransferFailed when treasury reverts (RevertingReceiver), receive() accepts ether, exact MIN_PAYMENT succeeds.
- **ComputeMarketplace.t.sol:** 14 tests. submitScores reverts (NotValidator, MinerNotRegistered, InvalidInput for length mismatch and empty array), registerAsMiner reverts (duplicate, metadata >256 chars), distributeRewards reverts (NoScores), zero balance no revert, resetRoundScores onlyOwner, proportional reward split (2 miners), getMiners return values.

**Agents/orchestration (pytest):**
- **tests/test_config_chains.py:** Chain config: get_chain_id default and from env, get_chain_config by name/id, get_rpc default/env/placeholder-ignore, get_native_symbol and get_explorer_url for celo-sepolia and anvil.
- **tests/test_payment.py:** MIN_PAYMENT_WEI, get_min_payment_wei default and PAYMENT_WEI override, REVENUE_ABI structure, verify_payment_tx false for invalid hash and bad address.
- **tests/test_state.py:** SwarmState TypedDict keys and optional fields, partial state.
- **tests/test_graph_dry_run.py:** Graph compiles, _route_after_finance (done→end, !done→continue), deployer_node with/without REVENUE_SERVICE_ADDRESS, finance_distributor_node returns dict when no address.

**Scripts:** `npm run test` (forge + pytest), `npm run test:contracts`, `npm run test:agents`. **packages/agents/tests/README.md** documents agent tests.

---

## 5. Celo chain IDs and RPC (reference)

- **Celo Sepolia (testnet):** chainId **11142220**.  
  RPC: `https://rpc.ankr.com/celo_sepolia` or `https://forno.celo-sepolia.celo-testnet.org`; Explorer: https://celo-sepolia.blockscout.com; Faucet: https://faucet.celo.org/celo-sepolia.
- **Celo mainnet:** chainId 42220.  
  RPC: e.g. `https://celo-mainnet.infura.io/v3/<key>`, or public endpoints.
- **Anvil (local):** 31337, `http://127.0.0.1:8545`.

Explorer: e.g. https://celo-sepolia.blockscout.com (testnet), https://explorer.celo.org (mainnet).
