# Compute Marketplaces & DAOs

Ways to connect the agent swarm to **compute marketplaces** (x402-style, Bittensor-style) and **full DAOs** on testnet (Celo Sepolia, Anvil) or mainnet.

**Production v1:** For a minimal safe launch on Celo mainnet, deploy **without** the DAO; keep `AgentRevenueService` owned by an EOA or multisig. Use `npm run deploy:dao` only as an **optional/advanced** path after validating the core revenue flow. See [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md) Section 12.

---

## 1. x402-style: Pay-per-call APIs (agents earn as providers)

**Idea:** Expose our AI service over HTTP. Clients get `402 Payment Required` with payment instructions; after they pay (e.g. on Base), we serve the response. Fits “agents earn on a compute marketplace” because we become a paid API that other agents or apps can call.

**How x402 works (short):**
- Client `GET /query?q=...` → server responds **402** + headers: price, token, recipient, chain.
- Client signs and sends payment (on-chain or via facilitator), then retries the request with a **PAYMENT-SIGNATURE** (or similar) header.
- Server verifies payment and returns the resource.

**In our testnet setting:**

| Option | Description |
|--------|-------------|
| **A) x402 in front of our contract** | Add an HTTP API (e.g. FastAPI/Express) that: (1) returns 402 with our `AgentRevenueService` address and `MIN_PAYMENT`; (2) accepts a header with a **tx hash** of a `fulfillQuery(metadata)` call; (3) waits for tx confirmation, then returns the same `metadata` (or a fresh LLM response). No need for a separate token; payment is native ETH to our contract. |
| **B) Use @coinbase/x402 (or x402 SDK)** | Use the official protocol and facilitator so clients pay in USDC/ETH via the standard 402 flow; our backend verifies via the facilitator and then calls our contract or records the payment. Base is supported; works on Base Sepolia with test USDC if available. |
| **C) Agents as x402 consumers** | When our swarm calls external paid APIs (e.g. another team’s model API), use an x402 client to pay and get the resource. That doesn’t make *us* earn on a marketplace but lets us participate in one. |

**Concrete next steps (testnet):**
- Add a small **HTTP 402 adapter** in `packages/agents` (or a new `packages/api`): one endpoint that returns 402 with `AgentRevenueService` address and amount; on retry with `X-Payment-Tx-Hash` (or similar), verify the tx on-chain and return the AI response (reuse existing LLM + constitution).
- Optional: depend on `@coinbase/x402` and implement the full header flow so we’re compatible with standard x402 clients.

---

## 2. Bittensor-style: Testnet compute marketplace (miners + validators)

**Idea:** Recreate a *marketplace* on our testnet where “miners” (our agents or other bots) do work, “validators” score them, and a contract distributes testnet ETH (or a test ERC20) by score — same *pattern* as Bittensor, without TAO or Bittensor mainnet.

**Why not real Bittensor here:** Bittensor runs on its own chain, uses TAO, and has strict miner/validator tooling (Linux, etc.). For “our testnet setting” we keep everything on Base Sepolia (or Anvil) and implement a minimal marketplace.

**Sketch:**

1. **Registry contract (testnet)**  
   - `registerAsMiner(metadata)` / `setValidatorAllowlist(validator, allowed)`.
   - Store miner/validator list and optional stake (test ETH or test token).

2. **Tasks and scores**  
   - Validators (we run one or more) send “tasks” to miners (e.g. “answer this query”).  
   - Miners respond; validators submit **scores** on-chain (e.g. `submitScores(minerAddress[], scores[])`).

3. **Reward contract**  
   - Periodically (e.g. every N blocks or on-demand): read scores, compute weights, **distribute testnet ETH** from a reward pool to miners.  
   - Our swarm’s “earn” flow = our agent is a miner, gets scored, receives testnet ETH from this contract.

4. **Where our swarm fits**  
   - **As miner:** One or more of our LangGraph agents register as miners. They receive tasks (e.g. from a validator bot), run LLM + constitution, return response; validator scores and submits; reward contract pays them.  
   - **As validator:** We run a validator bot that sends tasks to registered miners and submits scores (e.g. quality/relevance), so the marketplace has at least one honest scorer.

**Concrete next steps (testnet):**
- Add `contracts/ComputeMarketplace.sol` (or similar): registry + `submitScores` + `distributeRewards` with a simple weighting (e.g. proportional to score).
- Add a **miner service** in `packages/agents`: register on-chain, listen for tasks (or poll), run existing LLM flow, return result to validator.
- Add a **validator bot** (separate script or node): issues tasks, collects responses, scores them, calls `submitScores`.
- Fund the reward pool with testnet ETH (or mint test ERC20) and run a few rounds to prove “agents connect and earn” on this marketplace.

---

## 3. Full DAOs in our testnet setting

**Idea:** Make treasury and/or revenue parameters **governed** by a DAO on testnet (proposals + voting), so “the swarm” or token holders control fees, beneficiary, or upgrades.

**Options:**

| Option | Description |
|--------|-------------|
| **Treasury DAO** | Treasury address is a **governance contract** (e.g. OpenZeppelin Governor): proposals to transfer funds or change `financeDistributor` / `beneficiary`; voting with a test ERC20 or NFT. |
| **Parameter DAO** | Governance sets `PROTOCOL_FEE_BPS`, `DISTRIBUTABLE_BPS`, or a new “DAO treasury” address in `AgentRevenueService` (e.g. via `onlyGovernance` and a timelock). |
| **Agent voting** | Agents hold voting power (e.g. one token per agent type); proposals could be “approve new IP prompt,” “change profit threshold,” etc. |

**Concrete next steps (testnet):**
- Deploy a **governance token** (ERC20) and a **Governor** (e.g. GovernorCountingSimple + Timelock) on Base Sepolia.
- Set **treasury** or **owner** of `AgentRevenueService` to the Timelock so only successful proposals can change fee params or beneficiary.
- Optional: add an “agent voting” front-end or script so our swarm (or a human) can create and vote on proposals.

---

## 4. Summary table

| Mechanism | How agents “connect and earn” | Testnet fit |
|-----------|------------------------------|-------------|
| **x402-style** | We expose a paid API; clients pay (e.g. to our contract) and get AI responses. Our agents *are* the compute marketplace. | Add HTTP 402 adapter; optional @coinbase/x402. Base Sepolia works. |
| **Bittensor-style** | We run miners (and optionally validators) in a testnet marketplace; rewards paid by a contract from scores. | New contract + miner/validator services on Base Sepolia or Anvil. |
| **Full DAO** | Treasury and/or fee/beneficiary settings are governed by proposals; agents (or humans) vote. | Governor + token + point AgentRevenueService at Timelock. |

---

## 5. Implemented order

1. **x402-style adapter** — Smallest change: add an HTTP layer that returns 402 and verifies payment against existing `AgentRevenueService` so “agents earn” via standard pay-per-call API.
2. **Testnet compute marketplace** — One contract + miner + validator to prove “Bittensor-style” earn on our chain.
3. **DAO** — Add governance for treasury and key parameters so the testnet run is “full DAO” and upgradeable by vote.

If you tell me which of these you want to implement first (x402 adapter, marketplace contract + bots, or DAO), I can outline concrete tasks and file changes next.
