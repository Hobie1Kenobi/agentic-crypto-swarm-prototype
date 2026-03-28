# Production Readiness — Celo Mainnet Launch

Guidance for a post-testing production launch on **Celo mainnet** (chain ID 42220). Use this together with [CELO-SEPOLIA-TESTNET.md](CELO-SEPOLIA-TESTNET.md) and [SETUP.md](SETUP.md).

---

## 1. Production deployment checklist

- [ ] **Chain:** `CHAIN_ID=42220`, `CHAIN_NAME=celo-mainnet`, `RPC_URL` or `CELO_MAINNET_RPC_URL` set to a reliable Celo mainnet RPC (e.g. Ankr, Infura, Alchemy).
- [ ] **Env:** `.env` copied from `.env.example`; no testnet/placeholder values; no `.env` or `.env.local` committed. For mainnet, maintain `.env.mainnet` (from `.env.mainnet.example`, gitignored) with **mainnet-only overrides**; run `npm run env:mainnet` to **merge** into `.env` (empty keys in `.env.mainnet` keep existing `.env` secrets; backs up `.env` first). Smoke/orchestration always load `.env` only.
- [ ] **Wallets:** Agent keys created or imported; addresses and keys stored only in env/secrets (not in repo).
- [ ] **Deployer:** EOA used for `forge script` has sufficient CELO for deploy gas; key is `PRIVATE_KEY` (or equivalent).
- [ ] **Contracts:** Deploy with `.\scripts\deploy.ps1 --broadcast` on mainnet RPC; run `npm run fetch-addresses` and verify `REVENUE_SERVICE_ADDRESS`, `CONSTITUTION_ADDRESS`, `COMPUTE_MARKETPLACE_ADDRESS` in `.env`.
- [ ] **Treasury / finance:** `FINANCE_DISTRIBUTOR_ADDRESS` and beneficiary set; both funded if they need to send txs.
- [ ] **Payer:** `ROOT_STRATEGIST_ADDRESS` (or the address derived from the key used for simulation) funded with CELO for pay-per-query txs.
- [ ] **DAO (optional):** If using governance path, deploy DAO only after core revenue flow is validated; see Section 10.
- [ ] **Explorer:** Verify all deployed contracts and first txs on [Celo Explorer](https://explorer.celo.org).
- [ ] **Runbooks:** Team has access to this doc, SETUP, and CELO-SEPOLIA-TESTNET; know how to run orchestration and simulation and where logs/reports are.
- [ ] **Marketplace smoke (optional):** After deploy and `npm run fetch-addresses`, run `npm run mainnet:marketplace-smoke` for one full on-chain task lifecycle; artifacts are `celo_mainnet_task_market_report.json` / `.md` at repo root.
- [ ] **Automated sequence:** `npm run mainnet:preflight` (read-only checks). `npm run mainnet:readiness` defaults to dry-run deploy + fetch (no smoke). `npm run mainnet:readiness -- -Broadcast` after funding deployer; `npm run mainnet:readiness -- -SkipDeploy -SkipFetch -WithSmoke` for smoke only after contracts exist and agents are funded.

---

## 2. Security checklist

- [ ] **Keys:** No private keys in code, logs, or repo; all keys in env or a secrets manager; `.env` and `.env.local` in `.gitignore`.
- [ ] **Contracts:** `AgentRevenueService` uses `ReentrancyGuard`, `Pausable`, and `Ownable`; fee math (10% / 50%) and `MIN_PAYMENT` verified; no unchecked external calls besides treasury/finance.
- [ ] **Access:** Revenue contract owner is a single EOA or Timelock (if DAO); only owner can `pause`, `setTreasury`, `setFinanceDistributor`.
- [ ] **Inputs:** `fulfillQuery(resultMetadata)` has no arbitrary call/callback; metadata is logged/emitted only; consider length/cost limits if metadata is large.
- [ ] **Dependencies:** Foundry and OpenZeppelin at pinned versions; no unknown or unvetted dependencies in the critical path.
- [ ] **RPC:** Use HTTPS and a trusted RPC provider; avoid public endpoints for mainnet if they expose high throughput or admin actions.
- [ ] **Secrets handling:** Follow Section 4 (secrets handling guidance).

---

## 3. Operational checklist

- [ ] **Monitoring:** At least balance and tx success/failure for revenue contract, finance distributor, and beneficiary (Section 5).
- [ ] **Alerting:** Alerts on repeated tx failures, low payer balance, or contract pause (Section 5).
- [ ] **Logging:** Application logs (orchestration, simulation, api_402) written to a known location; no secrets in logs.
- [ ] **Backups:** Env/secrets backed up in a secure store; contract addresses and deployment params recorded.
- [ ] **Incident response:** Owner can pause `AgentRevenueService` in an emergency; runbook for pause and unpause.
- [ ] **Upgrades:** Revenue contract is not upgradeable; parameter changes (treasury, finance distributor) via owner or governance (Section 7).

---

## 4. Secrets handling guidance

- **Storage:** Store private keys and API keys in environment variables or a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault). Never commit `.env`, `.env.local`, or any file containing keys.
- **Access:** Restrict access to deployer and agent keys; use separate keys per environment (e.g. testnet vs mainnet) and rotate if compromised.
- **CI/CD:** Do not inject production keys in plain text in CI; use secret variables or a secure vault and restrict who can deploy to mainnet.
- **Local:** Use `.env.example` as a template; developers use local `.env` that is gitignored; never commit real keys.
- **Leak response:** If a key is exposed: rotate immediately, revoke/transfer ownership if needed, and pause the revenue contract if the exposed key can pause or change parameters.

---

## 5. Monitoring and alerting recommendations

- **Balances:** Monitor CELO balance of: deployer (if it holds funds), `ROOT_STRATEGIST_ADDRESS` (payer), `FINANCE_DISTRIBUTOR_ADDRESS`, and `REVENUE_SERVICE_ADDRESS`. Low payer balance can stop new queries; low finance balance can delay distributions.
- **On-chain events:** Index or watch `QueryFulfilled` and `FeeDistributed` from `AgentRevenueService` to confirm payments and splits; alert on long gaps or unexpected drops in volume if you rely on sustained revenue.
- **Application health:** If running api_402 or orchestration as a service, monitor process health, RPC connectivity, and response times; alert on repeated RPC or tx failures.
- **Alerting:** Set thresholds (e.g. payer balance below N CELO, contract paused, or > M failed txs in an hour) and notify operators; use PagerDuty, Slack, or email depending on your stack.
- **Dashboards:** Optional: Grafana/dashboard for balance history, tx count, and event counts per day.

---

## 6. Wallet key management guidance

- **Separation:** Use distinct keys for: (1) deployer (one-time or rare), (2) root strategist (payer for queries), (3) finance distributor (distribution txs), (4) other agents if used. Reduces blast radius if one key is compromised.
- **Custody:** Prefer hardware wallets or KMS for deployer and high-value keys; hot wallets only for automated payer/finance with limited balance.
- **Rotation:** Plan rotation for long-lived keys; after rotation update env and ensure no automation still uses the old key.
- **Spend limits:** Agent design (e.g. daily caps) is currently enforced off-chain or by design; for mainnet consider additional caps or multi-sig for large distributions.

---

## 7. Upgrade and governance notes

- **AgentRevenueService:** Not upgradeable (no proxy). Parameter changes (treasury, finance distributor) only via `setTreasury` / `setFinanceDistributor` and `pause` / `unpause` by the current owner.
- **Owner transfer:** If you deploy without DAO, owner is the deployer EOA. You can transfer ownership to a multisig or, later, to a Timelock (after deploying the DAO).
- **DAO path:** If you enable governance (Section 10), ownership is transferred to the Timelock; only successful governance proposals can then change parameters or pause. Timelock delay (e.g. 60 seconds in current script) should be increased for mainnet (e.g. 24–48 hours).

---

## 8. Economic risk notes

- **Fee assumptions:** 10% protocol fee and 50% distributable are fixed in the contract; remainder stays in the contract. Ensure this matches your economic model and that the contract does not accumulate more value than intended without a withdrawal path (currently there is no owner withdrawal; remainder is effectively locked).
- **CELO volatility:** Revenue is in CELO; value in fiat or other assets will fluctuate. Consider this for treasury and distribution planning.
- **Gas:** Mainnet gas costs will be higher than testnet; ensure payer and finance distributor have enough CELO for gas and that MIN_PAYMENT (0.001 CELO) still makes sense for your use case.
- **Concentration:** If one address (e.g. root strategist) holds most operational funds, compromise or key loss has high impact; diversify or cap balances where possible.

---

## 9. Abuse, spam, and pay-per-query considerations

- **Spam / low-value queries:** Anyone can call `fulfillQuery` with at least `MIN_PAYMENT`; the contract does not rate-limit. Attackers can spam queries to consume LLM/compute or to create noise. Mitigations: (1) run orchestration/simulation in a controlled environment and do not expose a public unfiltered api_402 without additional controls; (2) consider minimum value or allowlists if you open a public API.
- **Metadata abuse:** `resultMetadata` is stored in events and can be used for spam or long strings; consider capping length or sanitizing off-chain if you index it.
- **Sybil:** No on-chain identity; many addresses can pay and query. If you need “one user, one vote” or rate limits per identity, implement off-chain (e.g. API keys, auth) or future contract changes.

---

## 10. Rate limit and circuit breaker recommendations

- **API (api_402):** Add rate limiting per IP or per API key (e.g. N requests per minute) to reduce abuse and protect backend/LLM. Reject or return 429 when exceeded.
- **Orchestration / simulation:** Limit concurrency and total txs per run (e.g. max N `fulfillQuery` txs per hour); use `--max-steps` to cap graph steps.
- **RPC:** Use a rate-limited or dedicated RPC so one process does not exhaust provider limits; back off on 429 or connection errors.
- **Circuit breaker:** If RPC or contract calls fail repeatedly (e.g. 5 failures in a row), stop sending new txs and alert; resume only after manual check or after a cooldown and successful health check.
- **Contract:** `AgentRevenueService` has `pause()`; use it as a manual circuit breaker in an emergency (e.g. exploit or critical bug).

---

## 11. Accounting and audit log recommendations

- **On-chain:** Rely on `QueryFulfilled` and `FeeDistributed` events for a verifiable audit trail of payments and fee splits; index these for accounting and reporting.
- **Off-chain:** Keep logs of orchestration runs, simulation runs, and api_402 requests (without secrets); include tx hashes, timestamps, and outcome (success/failure). Retain for at least the period required for audits or disputes.
- **Reconciliation:** Periodically reconcile on-chain balances and event totals with internal accounting (e.g. sum of distributable amounts vs finance balance).
- **Reports:** Reuse or extend `simulation_report.json` / `simulation_report.md` for runs that generate them; store in a secure location if they contain sensitive info.

---

## 12. DAO / governance: review and minimal safe launch

### Current DAO setup

- **Script:** `script/DeployDAO.s.sol` deploys: `SwarmGovernanceToken`, `TimelockController` (60 s delay), `SwarmGovernor`, then transfers `AgentRevenueService` ownership to the Timelock. After that, only governance proposals can change `setFinanceDistributor`, `setTreasury`, or `pause` / `unpause`.
- **Usage:** `npm run deploy:dao` (or `.\scripts\deploy-dao.ps1`) runs after the main deploy; requires `REVENUE_SERVICE_ADDRESS` and `PRIVATE_KEY`.

### Recommendation for v1 production launch

- **Minimal safe launch:** For v1, **do not deploy the DAO** on mainnet. Launch with the revenue contract owned by a single EOA or a **multisig** (e.g. 2-of-3). This keeps operations simple, avoids token distribution and governance overhead, and lets you pause or adjust parameters quickly if needed.
- **DAO as optional/advanced path:** Keep the DAO code and `npm run deploy:dao` as an **advanced, optional** path. Document that:
  - DAO is for teams that want on-chain governance and timelocked parameter changes.
  - It adds token deployment, voting, and timelock delay; mainnet Timelock delay should be increased (e.g. 24–48 hours), and token distribution and quorum must be designed.
  - Use only after the core revenue flow has been validated on mainnet without DAO.

### If you enable DAO later

- Increase Timelock delay in `DeployDAO.s.sol` (e.g. 1 day = 86400 seconds) for mainnet.
- Decide token distribution and quorum (e.g. 4% quorum in current Governor) so proposals are executable but not trivially passable.
- Document the governance flow (create proposal → vote → queue → execute) and who holds proposer/executor roles.

---

## Quick reference

| Topic            | Section |
|------------------|--------|
| Deployment steps | 1      |
| Security         | 2      |
| Operations       | 3      |
| Secrets          | 4      |
| Monitoring       | 5      |
| Wallets          | 6      |
| Upgrades         | 7      |
| Economic risk    | 8      |
| Abuse/spam       | 9      |
| Rate limits      | 10     |
| Accounting       | 11     |
| DAO / v1 launch  | 12     |
