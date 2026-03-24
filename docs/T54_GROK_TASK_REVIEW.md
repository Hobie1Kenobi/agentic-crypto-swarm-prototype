# T54 / payout-oriented task review (Grok-style priorities)

This doc maps **premium, payout-oriented** task ideas to **what this repo already implements** and **what state to add** so listings stay honest and verifiable.

See also: [AGENT_MARKETPLACE_CAPABILITY_MATRIX.md](AGENT_MARKETPLACE_CAPABILITY_MATRIX.md), [T54_SELLER.md](T54_SELLER.md).

---

## What is already implemented (relevant to T54 + payouts)

| Area | Status | Where |
|------|--------|--------|
| T54 XRPL **seller** (402 + `xrpl:0` + facilitator) | Done | `t54_seller_app.py`, `npm run t54:seller`, `T54_SELLER_PRICE_DROPS` |
| T54 **buyer** adapter (pay + settle) | Done | `integrations/t54_xrpl/adapter.py`, `npm run t54:cycle` |
| Discovery hook for your public seller URL | Done | `T54_SELLER_PUBLIC_URL`, `T54_X402_RESOURCE_URL` → `t54-xrpl-example` |
| Celo x402 **seller** (CELO `fulfillQuery`) | Done | `api_402` |
| Base USDC **seller** (Bazaar-style) | Done | `api_seller_x402` |
| Constitution-bound **short LLM** answers | Done | `generate_response_for_query`, swarm LLM |
| Soak / realism **task templates** | Done | `services/task_templates.py` — **small** SKUs (~$0.01-style), not $5–500 |
| Escrow + validator **task marketplace** | Done | `task_market_demo`, `ComputeMarketplace` |
| Pricing catalog for XRPL quote path | Partial | `services/pricing.py` — single `task_execution` tier, not per-SKU |

---

## Grok’s 7 task families — honest fit vs repo

| # | Task family | Payout “certainty” (market) | **Honest fit with current stack** | What’s missing for real delivery |
|---|-------------|-----------------------------|-----------------------------------|----------------------------------|
| 1 | On-chain forensics & wallet risk | High if buyers trust methodology | **Weak as shipped** — no chain indexer, no graph/MEV pipeline | RPC/indexer (Covalent, Arkham-class), rules engine, reproducible scoring; LLM only summarizes *if* you feed structured facts |
| 2 | Narrative / sentiment alpha | High in crypto Twitter | **Weak** — no X/TG/Discord connectors | Data APIs, compliance (ToS), rate limits; LLM summarizes fetched text |
| 3 | Yield route optimization | High for DeFi | **Weak** — no live APY routers | DeFiLlama/yield APIs, chain sim or quote-only; **never** promise executable “tx blobs” without audited signing path |
| 4 | Token due diligence | High for DAOs | **Moderate** — LLM can structure *if* inputs are URLs/docs you allow | On-chain pulls (supply, holders) via RPC; manual “team history” remains fuzzy |
| 5 | Multi-source research packs | Medium–high | **Moderate** — aligns with long-form LLM + citations **if** you constrain format | PDF export, source URLs, optional web fetch tools (allowed domains) |
| 6 | Contract pre-audit scans | High post-hacks | **Weak** — no Slither/Mythril in repo | Static analysis pipeline + LLM explanation of findings only |
| 7 | Agent constitution / behavior audit | Niche, sticky | **Strong conceptual fit** — matches **constitution** framing | Formalize input (export prompts), rubric, structured report template |

**Bottom line:** The repo is **strong** on **payment rails**, **escrow**, **short ethical LLM**, and **T54 seller HTTP**. It is **not** yet a full “forensics / sentiment / yield / bytecode scanner” product without **external data + tools** per SKU.

---

## Recommended “state” to implement (prioritized, swarm-aligned)

### Tier A — Do first (no new chains; increases real payout odds)

1. **SKU catalog in config** — **Implemented:** `packages/agents/config/t54_seller_skus.json` + `t54_seller_catalog.py`; `t54_seller_app.py` registers **one `require_payment` middleware per path** (per-SKU pricing). Override path with **`T54_SELLER_SKUS_JSON`**.

2. **Structured output + validation** — **Implemented:** `t54_seller_models.py` + handlers in `t54_seller_handlers.py`; `output_schema` passed into each SKU’s `require_payment` (x402 metadata).

3. **“Honest listing” in `x402_providers.json`** — **Implemented:** rows `t54-xrpl-example`, `t54-xrpl-research-brief`, `t54-xrpl-constitution-audit`, `t54-xrpl-hello` with **`metadata.t54_path`**; discovery fills **`resource_url`** from **`T54_SELLER_PUBLIC_BASE_URL`** or legacy **`T54_SELLER_PUBLIC_URL`** (host derived).

4. **Reputation / proof loop** — **Optional:** `npm run report:t54-commerce` — line-count / artifact summary under `external_commerce_data/` (extend as you add payment logs).

5. **Daemon** — **Implemented (Windows):** `npm run t54:seller:daemon` → `scripts/t54-seller-daemon.ps1` (restart loop). Use systemd/PM2 on Linux if you prefer.

### Tier B — When you have APIs budget

- **Research pack SKU:** allowlisted `httpx` fetch + citation-required prompt (no raw Twitter unless API).  
- **DD-lite SKU:** token contract + RPC reads (supply, top holders) + LLM narrative — **disclose** data sources in the response.

### Tier C — Heavy engineering (later)

- Forensics, MEV, bytecode scan: dedicated services + probably **not** LLM-only.

---

## Mapping Grok’s “Week 1” to this repo

| Grok Week 1 | Concrete action here |
|-------------|------------------------|
| List top 3 tasks on T54 | Implement **3 SKUs** in Tier A + list URLs in `T54_SELLER_PUBLIC_URL` / discovery |
| Expose x402 endpoints | **Done:** `t54:seller`; optionally **same** LLM backend as `api_402` behind a paid T54 route |
| Update `providers.json` with facilitator | **Done:** `t54-xrpl-example` uses `https://xrpl-facilitator-mainnet.t54.ai` |
| api_402 | Stays **Celo** rail; T54 is **separate** seller — cross-link in docs only unless you unify behind a gateway |

---

## Revenue expectations

Internal docs should treat **$200–1.5k/mo** and **$5k–20k+/mo** as **aspirational** until you have **traffic**, **SKU clarity**, and **repeat buyers**. The stack supports **micropayments and escrow**; it does not guarantee demand.

---

## Summary

- **Already done for T54 seller + payouts (mechanics):** facilitator URL, seller server, discovery envs, buyer adapter.  
- **Not done for Grok’s 7 verticals end-to-end:** most require **data/tools** beyond the current LLM + payment layer.  
- **Best next implementation state:** **multi-SKU T54 seller**, **structured outputs**, **honest provider rows**, **ops daemon** — then grow Tier B SKUs as you add APIs.
