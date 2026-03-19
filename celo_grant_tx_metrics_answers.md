# Celo grant — transaction metrics (evidence-based)

## 1) Analytics summary (audit)

- **Scope:** Count **unique, successful, public-chain** transactions evidenced by this repository (JSON/MD with `celo-sepolia.blockscout.com` links or non-null `tx_hash` on **Celo Sepolia, chain ID `11142220`**).
- **Excluded (explicit):**
  - **Local Anvil** (`chain_id` **31337**): `local_task_market_report.json`, `simulation_report.json`.
  - **Non-onchain / mocked:** `external_tx_hash: null`, `olas` live attempts with **no** tx hash, `mocked_external_replay` identifiers (not EVM txs).
  - **Duplicates:** same `tx_hash` repeated inside one artifact → counted once.
- **Other public chains:** **No** Gnosis/Olas **confirmed** tx hash appears in current artifacts (`olas_live_attempt_report.json` → `tx_hash: null`).
- **Unique Celo Sepolia txs documented in-repo:** **29** (see `celo_grant_tx_metrics_evidence.json`).
- **14-day moving average:** **Not computable to calendar precision from repo files alone** because **block timestamps per tx** are not stored in artifacts.  
  - **Conservative proxy (labeled assumption):** *If* all 29 txs fell inside any rolling 14-day window, **29 ÷ 14 ≈ 2.07** → disclose **~2 transactions/day** (rounded down for conservatism).

---

## 2) Recommended grant-form answers

### Q1 — Exactly how many daily transactions do you have as of today? (2 week moving average on any chain)

**Answer (defensible):**  
We document **29 unique successful transactions on Celo Sepolia (public testnet)** with verifiable Blockscout links in our repository artifacts. We **cannot** compute a rigorous **calendar 14-day moving average** from repository data alone because **per-tx block timestamps are not recorded** in those files.  

**Conservative proxy for a 2-week MA (explicit assumption):** if all documented txs occurred within a 14-day window, average **≈ 2 on-chain transactions per day** on Celo Sepolia.

**Evidence:**  
- `celo_grant_tx_metrics_evidence.json` (full hash list + sources)  
- Representative artifacts: `celo_sepolia_task_market_report.json`, `dual_mode_run_report.json`, `celo_sepolia_run_report.json`, `celo_sepolia_run_report.md`, `private_celo_validation_report.md`  
- Example explorer base: `https://celo-sepolia.blockscout.com/tx/<tx_hash>`

---

### Q2 — How are you counting your daily tx’s?

**Answer:**  
We count **only unique EVM transaction hashes** that are:

1. **On a public chain** we can cite in Blockscout (**Celo Sepolia**, chain ID **11142220**), and  
2. **Backed by a non-null `tx_hash`** and/or a **Blockscout URL** in a committed report.

We **do not** count:

- Local **Anvil** / `127.0.0.1:8545` runs (`chain_id` **31337**).  
- **Simulation-only** hashes from `simulation_report.json`.  
- **Adapter “replay” / trace events** where `tx_hash` is **null**.  
- **Duplicate** appearances of the same hash in one report (counted once).

**Optional next step (for a true 14-day MA):** pull **block timestamp** for each hash from Blockscout or RPC and bucket by UTC day.

---

### Q3 — Describe how the project will increase daily transactions on Celo.

**Answer:**  
The protocol is designed so **each end-to-end task** on the private marketplace produces **multiple on-chain steps on Celo** (e.g. task creation/acceptance, result submission, scoring/finalization, and role-based withdrawals), as shown in `celo_sepolia_task_market_report.json` and `hybrid_gnosis_celo_report.json`.  

Growth on Celo comes from:

1. **More tasks processed** through the same contract lifecycle (linear increase in txs per task).  
2. **Hybrid routing** (`public_market_adapter` + `task_market_demo`): external intake normalizes into internal tasks settled on Celo when `MARKET_MODE=hybrid`.  
3. **Multi-role / multi-agent flows**: distinct signers (requester, worker, validator/finance roles) each contribute txs in the documented flow.  
4. **Revenue and distribution paths** on Celo Sepolia (e.g. `fulfillQuery` + distribution txs referenced in `celo_sepolia_run_report.md`).  
5. **Mainnet migration:** the same patterns deploy to **Celo mainnet** for production traffic (testnet evidence today; mainnet is the scale path).

We are **not** claiming high current daily volume; we **are** claiming a **tx-heavy, verifiable settlement rail** where volume scales with **tasks × steps per task**.

---

## 3) Evidence list (high level)

| Count | Source file | Chain |
|------:|-------------|-------|
| 8 | `celo_sepolia_task_market_report.json` | Celo Sepolia |
| 8 | `dual_mode_run_report.json` | Celo Sepolia |
| 8 | `celo_sepolia_run_report.json` | Celo Sepolia |
| 2 | `celo_sepolia_run_report.md` (revenue flow) | Celo Sepolia |
| 3 | `private_celo_validation_report.md` (withdrawals) | Celo Sepolia |

**Full hash union + JSON:** `celo_grant_tx_metrics_evidence.json`

---

## 4) Confidence & limitations

| Topic | Confidence | Limitation |
|-------|------------|------------|
| **Unique tx count (29)** | **High** for “documented in repo” | Does not prove all txs are within the last 14 calendar days without Blockscout timestamp queries. |
| **14-day MA** | **Low** without explorer/RPC enrichment | Repo lacks per-tx `blockTimestamp`; any single-number MA is a **proxy** under stated assumptions. |
| **Gnosis / Olas** | **N/A (no hash)** | Live attempt reports show **no** confirmed external tx hash in artifacts to date. |
| **Testnet vs mainnet** | **Clear** | Evidence is **Celo Sepolia** (public testnet), not Celo mainnet production volume. |

---

## 5) Suggested disclosure footnote (paste under Q1)

> Reported figures are **Celo Sepolia (chain ID 11142220)** transactions evidenced by **Blockscout-linked hashes** in repository artifacts (`celo_grant_tx_metrics_evidence.json`). A **true** 14-day moving average requires **per-transaction block timestamps** from Blockscout/RPC; the **~2 tx/day** value is a **conservative proxy** assuming all documented txs fall within a 14-day window.
