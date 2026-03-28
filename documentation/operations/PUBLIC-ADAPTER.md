# Public Marketplace Adapter (Olas / Mech)

This repo supports **dual-mode execution**:

- **Private mode (Celo-first)**: our own onchain `ComputeMarketplace` on Celo Sepolia (or Anvil).
- **Public adapter mode (Olas / Mech)**: a request-intake + normalization layer that *can* connect to the Olas Mech Marketplace when environment and tooling allow it.

This document explains what is **live**, what is **onchain (private)**, and what is **replay/mock**.

---

## Supported Olas chains (external)

The Olas Mech Marketplace stack (via `mech-client` / `mechx`) supports these chains:

- `gnosis`
- `base`
- `polygon`
- `optimism`

**Celo is not supported by the Olas Mech marketplace stack** (as of the current docs), so Celo remains our private settlement chain.

---

## Modes

### `MARKET_MODE=private_celo`

- Runs **only** our private onchain marketplace task lifecycle on `ComputeMarketplace`.
- Produces: `celo_sepolia_task_market_report.(md|json)` (or local equivalents).

### `MARKET_MODE=public_olas`

- Runs **public adapter intake**.
- If `OLAS_ENABLED=1` and `mechx` is installed/configured, the adapter attempts a **real external Olas request** (on one of the supported Olas chains).
- If not configured, the adapter runs in **mocked external replay** mode (explicitly recorded in artifacts).
- Produces:
  - `public_adapter_run_report.(md|json)`
  - `communication_trace.(md|json)`

### `MARKET_MODE=hybrid`

- Public intake (live or replay) → normalize → execute **private onchain settlement** on Celo/Anvil → return adapter response.
- Produces:
  - `public_adapter_run_report.(md|json)`
  - `communication_trace.(md|json)`
  - `celo_sepolia_task_market_report.(md|json)` (or local equivalents)

---

## Live vs replay boundaries (no silent fakes)

Artifacts contain explicit boundaries:

- **`real_external_integration`**: request was sent to Olas via `mechx` and we captured its tx hash / request id.
- **`mocked_external_replay`**: adapter request was replayed from a JSON payload or live credentials/tooling were missing.
- **`contract_level_execution`**: internal/private `ComputeMarketplace` onchain execution occurred (Celo Sepolia or Anvil).
- **`local_simulation`**: offchain-only (no chain txs).

Check `communication_trace.md` for the per-step boundary markers.

---

## Setup: public adapter (Olas) tooling

The official Olas `mech-client` pins dependencies that conflict with this repo’s Python stack.
So we install it into an **isolated venv** and invoke the CLI.

Install `mechx` into a repo-local venv:

```powershell
npm run olas:install
```

Then set these in `.env` (minimum):

- `OLAS_ENABLED=1`
- `OLAS_CHAIN_CONFIG=base` (or `gnosis|polygon|optimism`)
- `OLAS_PRIORITY_MECH_ADDRESS=<target_mech_contract>`
- `OLAS_TOOL=<tool_name>`
- `OLAS_EOA_PRIVATE_KEY=<funded_eoa_private_key_on_that_chain>`
- Optional: `OLAS_MECHX_PATH=<repo>\.venv-olas\Scripts\mechx.exe`

Run adapter:

```powershell
npm run adapter:public
```

Hybrid run (public intake → private settlement on Celo):

```powershell
npm run adapter:hybrid
```

---

## Replay mode (deterministic, works on Celo)

You can replay an external request payload without touching Olas:

```powershell
cd packages/agents
python public_adapter_demo.py --hybrid --replay path\\to\\payload.json
```

Example payload:

```json
{
  "prompt": "What is one ethical use of AI?",
  "tool": "openai-gpt-4o-2024-05-13",
  "request_id": "external-123",
  "tx_hash": null,
  "result": null,
  "chain_config": "base"
}
```

This produces the same correlation and reports, with boundary `mocked_external_replay`.

Repo example: `docs/examples/olas_request_replay_example.json`

