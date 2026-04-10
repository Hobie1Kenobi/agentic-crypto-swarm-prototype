# my-new-api

Monetized HTTP API on **Dhali** using **x402** and the **Dhali** payment scheme on **XRPL Mainnet**. Callers pay **per request** in XRP (drops) via Dhali’s payment channel and [pay.dhali.io](https://pay.dhali.io/).

These paths match **`packages/agents/config/t54_seller_skus.json`** and your current **`T54_SELLER_PUBLIC_BASE_URL`** in `.env`. When ngrok rotates, replace the host everywhere below.

---

## Upstream (Dhali Portal reverse proxy)

Set **origin / upstream** to your public T54 seller base (no trailing slash):

**`https://api.agentic-swarm-marketplace.com/t54`**

Same value as **`DHALI_REVERSE_PROXY_UPSTREAM_URL`** / **`T54_SELLER_PUBLIC_BASE_URL`** in this repo.

---

## Public paths — direct to T54 (no Dhali)

Base: **`https://api.agentic-swarm-marketplace.com/t54`**

| SKU / route | Method | Full URL |
|-------------|--------|----------|
| Hello / ping | GET | `https://api.agentic-swarm-marketplace.com/t54/hello` |
| Structured query | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/query?q=…` |
| Research brief | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/research-brief?topic=…&context=…` |
| Constitution audit | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/constitution-audit?prompt_snippet=…` |
| Agent commerce data | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/agent-commerce-data?depth=standard` or `depth=full` |
| Airdrop intelligence | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/airdrop-intelligence?topic=…&context=…` |
| Intake resale pack | GET | `https://api.agentic-swarm-marketplace.com/t54/x402/v1/intake-resale?pack_id=<uuid>` |

---

## Public paths — via Dhali proxy

Gateway base (this asset):

**`https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990`**

When the Portal upstream is **`…/t54`**, Dhali usually maps **the same path after `/t54`** onto the proxy (no extra `/t54` in the proxy URL):

| Route | Example (GET) |
|-------|-----------------|
| Hello | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/hello` |
| Query | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/query?q=…` |
| Research brief | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/research-brief?topic=…&context=…` |
| Constitution audit | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/constitution-audit?prompt_snippet=…` |
| Agent commerce data | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/agent-commerce-data?depth=standard` |
| Airdrop intelligence | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/airdrop-intelligence?topic=…&context=…` |
| Intake resale | `https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/x402/v1/intake-resale?pack_id=<uuid>` |

If your Portal is configured so the proxy must include `/t54`, use **`…/4990/t54/hello`** (etc.) instead—match whatever successfully hits your upstream in Dhali’s test tool.

---

## Not this Dhali asset: Base USDC x402 (separate host path)

Your **Base mainnet** USDC seller (facilitator / `exact` EVM) is exposed separately, e.g.:

**`https://api.agentic-swarm-marketplace.com/x402/v1/query`** (see **`X402_SELLER_PUBLIC_URL`** in `.env`)

That rail is **EVM USDC**, not the **XRPL / Dhali** `accepts` shown on this asset. Only document it here if you intentionally front the same Base route through Dhali with a different asset.

---

## Pricing

| Field | Value |
|--------|--------|
| **Base cost** | ~0.00001000 XRP per request (10 drops; confirm in Portal if Dhali rounds display) |
| **Payout network** | XRPL Mainnet (`xrpl:0`) |
| **Runtime** | Shown in Portal (~latency after proxy) |

---

## x402 payment (Dhali scheme)

**Facilitator (charge API):**  
`https://x402.api.dhali.io/v2/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/`

**`accepts` (from asset dashboard):**

```json
{
  "scheme": "dhali",
  "network": "xrpl:0",
  "payTo": "rLggTEwmTe3eJgyQbCSk4wQazow2TeKrtR",
  "price": {
    "amount": "10",
    "asset": "xrpl:0/native:xrp"
  },
  "maxTimeoutSeconds": 1209600,
  "extra": {
    "paymentTerminal": "https://pay.dhali.io?uuids=d1e8bc5b-5fbb-4073-8f26-b0bc637e4990",
    "instruction": "Create a payment via pay.dhali.io"
  }
}
```

1. **Unpaid request** → `402 Payment Required` with x402 terms.  
2. **Buyer** completes payment via [pay.dhali.io](https://pay.dhali.io?uuids=d1e8bc5b-5fbb-4073-8f26-b0bc637e4990) or a **Dhali payment channel** / SDK (`dhali-py`, etc.).  
3. **Retry** the same request with the required **x402 / Dhali** payment headers your client stack supports.

---

## Example probe (Dhali)

```http
GET https://run.api.dhali.io/d1e8bc5b-5fbb-4073-8f26-b0bc637e4990/hello HTTP/1.1
Host: run.api.dhali.io
```

Expect **402** until a valid x402/Dhali payment is attached; then **200** with your API response body.

---

## References

- [Dhali docs](https://dhali.io/docs/)  
- [x402 on Dhali](https://dhali.io/docs/x402-support/)  
- Swarm repo: `documentation/dhali/DHALI_INTEGRATION.md`

---

*Hosts from `.env` (`T54_SELLER_PUBLIC_BASE_URL`, `X402_SELLER_PUBLIC_URL`); ngrok URLs change when the tunnel changes.*
