# Swarm revenue focus — get paid by marketplaces

**North star:** Run our agents so **external marketplaces pay us** for work we can actually deliver, then scale bridging and rails.

## How money reaches the swarm today

| Path | What you run | Who pays | Asset / chain | What we sell |
|------|----------------|----------|----------------|--------------|
| **Celo x402 seller** | `api_402` (port 8042) | Any client that pays CELO | Celo Sepolia → `fulfillQuery` | Ethical LLM Q&A (`/query?q=...`) |
| **Facilitator x402 seller** | `api_seller_x402` (port 8043) + public URL | Bazaar / any x402 client | Base Sepolia USDC | Same LLM output (`/x402/v1/query?q=...`) |
| **Compute marketplace** | `multi_rail_hybrid` / `task_market_demo` | Requester escrow on-chain | CELO in `ComputeMarketplace` | Full task lifecycle (worker + validator roles) |

**Buy side (cost centers):** `run-x402-marketplace-test.py`, `invoke_by_provider` — we **pay** Arcana / echo / Agoragentic to learn and integrate. Keep that spend small; **revenue focus = seller paths + Celo tasks.**

## Task capability (be honest)

**We are strong at today**

- Short **text Q&A** and classification under a **fixed constitution** (no gambling, illegal content; sustainable compute framing).
- Same flow powers `api_402`, `api_seller_x402`, and worker **result strings** on `ComputeMarketplace`.

**We are not automatically strong at**

- **Domain-specific APIs** (live price oracles, chain feeds) — Arcana-style endpoints need different adapters, not just the default LLM.
- **Agoragentic listing-specific** schemas (summarize vs passport vs vault) — each listing may need **custom params** and tests.
- **SLA / latency guarantees** — soak tests prove reliability of *our* stack, not every third-party SLA.

**Rule:** Only **list or advertise** SKUs that call **`generate_response_for_query`**-class behavior until you add a dedicated tool or prompt path per marketplace.

## Operating loop (revenue-first)

1. **Run sellers**  
   - Celo: `uvicorn api_402:create_app --port 8042`  
   - Base Sepolia USDC: `uvicorn api_seller_x402:create_app --port 8043`  
   - Expose 8043 via **`X402_SELLER_PUBLIC_URL`** (ngrok/VPS) for Bazaar / buyers.

2. **Prove one paid facilitator sale**  
   - Fund **buyer** Base Sepolia USDC (faucet or bridge).  
   - `X402_DRY_RUN=0` → `scripts/run-x402-seller-smoke.py` against your public URL.  
   - Confirm USDC at `pay_to` on Base Sepolia explorer.

3. **Run private settlement revenue**  
   - Keep `MARKET_MODE=hybrid` / `multi_rail` cycles so **ComputeMarketplace** continues to move CELO (requester → worker / treasury / finance).

4. **Expand marketplace surface only when capability matches**  
   - Add **one** new endpoint or prompt template per new task type; re-run soak or probe before claiming that listing.

## Config pointers

- Sellers: `packages/agents/config/x402_providers.json` — `swarm-self`, `swarm-seller-facilitator` (+ `X402_SELLER_PUBLIC_URL`).
- Keys: `ROOT_STRATEGIST_PRIVATE_KEY` — same address on Celo and Base for `pay_to` and bridging later.
- Probes: `scripts/probe-x402-seller.py`, `scripts/run-x402-agent-commerce-soak.py` (Celo buy path).

## What to defer (until revenue is flowing)

- Automatic **USDC → CELO** conversion after sale (manual or script later).
- **XRPL** seller depth until Celo + Base x402 revenue is repeatable.
- Heavy **Olas live** adapter until private settlement + x402 seller are stable.

This document is the default prioritization for “swarm gets paid by marketplaces” work.

**Deeper technical map:** [AGENT_MARKETPLACE_CAPABILITY_MATRIX.md](./AGENT_MARKETPLACE_CAPABILITY_MATRIX.md) · machine-readable SKUs: `packages/agents/config/task_capability_catalog.json`.
