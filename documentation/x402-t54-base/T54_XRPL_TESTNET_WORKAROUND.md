# T54 XRPL Testnet Workaround

t54.ai only hosts a **mainnet** facilitator (`https://xrpl-facilitator-mainnet.t54.ai`). There is no public testnet facilitator. To run the full XRPL–Celo bridge on testnet via x402, use a **self-hosted testnet facilitator**.

## Option 1: xrpl-x402-facilitator (Recommended)

The open-source [xrpl-x402-facilitator](https://pypi.org/project/xrpl-x402-facilitator/) supports XRPL testnet and uses the same x402 `/verify` and `/settle` contract as t54.

### Setup

1. **Install (requires Redis; Python 3.12+):**

```bash
pip install xrpl-x402-facilitator redis
```

2. **Start Redis** (e.g. `redis-server` or Docker: `docker run -p 6379:6379 redis`).

3. **Run the facilitator on testnet:**

```bash
export MY_DESTINATION_ADDRESS=rYourReceiver...
export FACILITATOR_BEARER_TOKEN=your-secret-token
export REDIS_URL=redis://127.0.0.1:6379/0
export NETWORK_ID=xrpl:1
export XRPL_RPC_URL=https://s.altnet.rippletest.net:51234

xrpl-x402-facilitator --host 127.0.0.1 --port 8010
```

4. **Configure our t54 adapter** (`.env`):

```bash
T54_XRPL_ENABLED=1
T54_XRPL_MODE=testnet
T54_XRPL_FACILITATOR_URL=http://127.0.0.1:8010
T54_XRPL_WALLET_SEED=sEd...
XRPL_RECEIVER_ADDRESS=rYourReceiver...
```

### End-to-end flow

- Our **x402 seller** (or api_402 with an XRPL payment mode) talks to this facilitator on `/verify` and `/settle`.
- Our **t54 adapter** (buyer) builds presigned XRPL payments and sends them to our seller.
- Seller calls facilitator → facilitator submits to XRPL testnet → payment settles.
- XRPL receipt feeds into your existing correlation layer → Celo private settlement.

**Note:** The facilitator URL in our config (`T54_XRPL_FACILITATOR_URL`) is used for the fail-closed check: "is testnet supported?" A local URL like `http://127.0.0.1:8010` is treated as testnet-capable and does **not** block. When buying from **external** t54 APIs (e.g. third-party merchants), those use t54's hosted mainnet facilitator—testnet is not available for them. This workaround applies when you run **your own** x402 seller that uses a self-hosted facilitator.

## Option 2: Dry-run / Simulated for pipeline testing

For testing the pipeline (correlation, cycle logs, reports) without real XRPL:

```bash
T54_XRPL_ENABLED=1
T54_XRPL_MODE=local
T54_XRPL_DRY_RUN=1
```

- No facilitator needed.
- No wallet needed for HTTP requests.
- Produces `local_dev_only` artifacts that you can map into your bridge logic for staging/dev.

## Option 3: Mainnet with minimal XRP

t54’s hosted mainnet facilitator works today. For small-scale tests, use mainnet with a small amount of XRP:

```bash
T54_XRPL_ENABLED=1
T54_XRPL_MODE=mainnet
T54_XRPL_WALLET_SEED=sEd...
# T54_XRPL_FACILITATOR_URL defaults to https://xrpl-facilitator-mainnet.t54.ai
```

## Bridging to Celo

Your existing `multi_rail_hybrid` flow already does:

1. **XRPL payment** (mock/replay/live) → verified receipt
2. **Correlation** → `xrpl_tx_hash` → `internal_task_id`
3. **Celo settlement** → task lifecycle, withdrawals

The t54 adapter provides **presigned x402** payments. For your bridge to work:

- **Receive side:** Your XRPL receiver (`XRPL_RECEIVER_ADDRESS`) gets payments; your correlation layer maps them to tasks.
- **Pay side:** When buying from t54-style APIs (your own or others), the t54 adapter builds the payment. The seller’s facilitator (hosted or self-hosted) verifies and settles.

With a self-hosted testnet facilitator, you can run this entire flow on testnet without using t54’s mainnet endpoint.
