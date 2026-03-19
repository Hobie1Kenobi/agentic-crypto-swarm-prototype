# Agent package tests

Run from repo root or from `packages/agents`:

```bash
# From repo root
npm run test:agents

# From packages/agents
python -m pytest tests/ -v --tb=short
```

**Coverage:**

- **test_config_chains.py** — Chain config: `get_chain_id`, `get_chain_config`, `get_rpc`, `get_native_symbol`, `get_explorer_url` with env overrides and defaults.
- **test_payment.py** — Payment module: `MIN_PAYMENT_WEI`, `get_min_payment_wei` (default and env override), `REVENUE_ABI`, `verify_payment_tx` (invalid hash / bad address).
- **test_state.py** — `SwarmState` TypedDict: required and optional keys, partial state.
- **test_graph_dry_run.py** — Graph compile, `_route_after_finance` (done → end, !done → continue), `deployer_node` with/without `REVENUE_SERVICE_ADDRESS`, `finance_distributor_node` when no address (returns dict with `done`).

No RPC or Ollama required for the current tests; config and payment tests use monkeypatch; graph tests use deployer/finance nodes without live RPC.
