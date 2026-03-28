# Agent marketplace capability matrix — technical tasks & mainnet readiness

This document maps **what our stack can actually do today** to **marketplace expectations**, and what to build for a **robust, earn-ready, mainnet-safe** deployment.

---

## 1. North star

**Earn revenue** by selling **well-defined task SKUs** we can fulfill with high reliability. **Do not** advertise ambiguous “general AI” on every marketplace until routing, SLAs, and failure modes are explicit.

---

## 2. Core primitives in the repo (building blocks)

| Primitive | Location | What it does |
|-----------|----------|----------------|
| **Constitution-bound LLM** | `swarm/llm.py`, `api_402`, `miner_service.task_handler`, `generate_response_for_query` | Short answers under fixed ethics rules (no gambling, illegal content; sustainable compute framing). |
| **Task templates (soak / realism)** | `services/task_templates.py` | `summarization`, `classification`, `extraction`, `short_answer` with SLA hints and `validation_rule` metadata. |
| **Celo x402 HTTP seller** | `api_402` | `GET/POST /query` → 402 → `fulfillQuery` → LLM response. |
| **Facilitator x402 seller** | `api_seller_x402` | Base Sepolia USDC via x402.org facilitator; same LLM path. |
| **Compute marketplace miner** | `miner_service.py` | `POST /task` with `{query}` → LLM; optional `registerAsMiner` on-chain. |
| **Private task settlement** | `task_market_demo`, `multi_rail_hybrid`, `ComputeMarketplace` | Escrow, worker/validator/requester roles, withdrawals. |
| **Public → private hybrid** | `public_market_adapter` | Olas-shaped intake → normalized internal task → Celo settlement (mock/live configurable). |
| **x402 buyer** | `external_commerce/x402_buyer.py`, `invoker` | Pay Arcana, echo, Agoragentic-style URLs. |
| **Customer balance / metering** | `services/customer_balance.py` | Credit/debit for XRPL→Celo flows (demo path). |

**Single LLM backbone:** Almost all “work” paths ultimately call the same **short-form text generation** pattern—not separate fine-tuned models per marketplace yet.

---

## 3. Task families we can support *honestly* today

| Task family | Examples | Fit | Notes |
|-------------|----------|-----|--------|
| **Short Q&A** | “What is X in one sentence?” | **Strong** | Default `api_402` / seller query param `q`. |
| **Summarization** | “Summarize in one sentence: …” | **Strong** | `task_templates` + soak queries. |
| **Binary / ternary classification** | Yes/no, risk level | **Strong** | Prompt asks constrained output. |
| **Light extraction** | “One sentence compliance risk from …” | **Moderate** | No structured JSON schema enforcement in all paths; add Pydantic output if marketplace requires. |
| **Oracle / live price / chain data** | Arcana-style `symbol=ETH` | **Weak without adapters** | Need HTTP/tool call + parsing, not LLM-only. |
| **Multi-step agents** | Agoragentic vault / passport | **Weak** | Requires per-listing integration, not generic. |
| **Long-context doc Q&A** | Full PDF | **Unverified** | Depends on Ollama model context; not soak-tested at scale. |

---

## 4. Marketplace → capability mapping

| Marketplace / rail | Typical ask | Our match today | To earn safely |
|---------------------|-------------|-----------------|----------------|
| **Celo `api_402`** | Paid LLM query | **Full** | Keep price + `fulfillQuery` aligned with `services/payment`. |
| **Base x402 / Bazaar** | USDC per GET `q` | **Full** (facilitator seller) | Public URL + one paid smoke; list only `q`-style SKUs. |
| **x402-test-echo / similar** | Echo / test | **Full** (as buyer for testing) | Use to validate client, not primary revenue. |
| **Arcana** | GET oracle, params | **Partial** | Add dedicated handler: fetch price API or LLM fallback **only if** you document behavior. |
| **Agoragentic** | Per-listing POST bodies | **Partial** | One integration test per listing ID you sell. |
| **ComputeMarketplace** | Escrow task + score | **Full** for text tasks | `task_templates` realism; miner + validator keys. |
| **Olas / public adapter** | External request → Celo | **Hybrid / mock** | Live Olas when mech-client configured; mainnet needs ops hardening. |
| **XRPL → Celo** | Payment correlation | **Proven** | Revenue is settlement-side CELO flows, not XRP custody. |

---

## 5. Robust system — what “mainnet ready” should include

**Already in good shape**

- Dual payment rails (Celo native + facilitator USDC).
- Soak tests and proof artifacts.
- Constitution string on LLM calls.
- Config-driven providers (`x402_providers.json`).

**Gaps to close before broad mainnet marketing**

| Area | Risk | Mitigation |
|------|------|------------|
| **SKU clarity** | Buyers expect exact behavior | Publish **one catalog** (`task_capability_catalog.json`) and match listings to it. |
| **Output validation** | Garbage or policy violations | Add optional **schema validation** (JSON) for paid routes; reject before settle. |
| **Routing** | Wrong handler for marketplace | **Router** layer: `task_family` → handler (LLM vs oracle adapter). |
| **Observability** | Silent failures | Metrics: 402 rate, settle failures, latency p95; alert on facilitator errors. |
| **Secrets / keys** | Leaked keys | Env-only; separate **seller receive** vs **hot spend** keys if treasury grows. |
| **Rate limits** | Abuse / drain | Per-IP or per-api-key limits on `api_402` / `api_seller_x402` (see PRODUCTION-READINESS). |

---

## 6. Suggested phased plan

**Phase A — Earn on testnet (now)**  
- Run both sellers; one real USDC payment to `pay_to`.  
- Keep listings to **task_templates**-aligned prompts only.

**Phase B — Catalog + router (pre-mainnet)**  
- Load `task_capability_catalog.json` at startup.  
- Map `q` or POST body to a **task_family**; reject unknown families with 400 + docs link.

**Phase C — Mainnet**  
- Deploy `AgentRevenueService` + marketplace on **Celo mainnet**; facilitator seller on **Base mainnet** with production facilitator URL.  
- Run parallel testnet + mainnet smoke weekly.

---

## 7. Related files

- `docs/SWARM_REVENUE_FOCUS.md` — revenue operating loop.  
- `packages/agents/config/task_capability_catalog.json` — machine-readable SKUs.  
- `packages/agents/services/task_templates.py` — internal task variety for soak.  
- `documentation/operations/PRODUCTION-READINESS.md` — security and ops checklist.

---

*This matrix should be updated when a new marketplace integration ships or a new task family is tested end-to-end.*
