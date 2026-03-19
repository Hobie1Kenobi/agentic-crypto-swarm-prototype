# Live XRPL → Celo Multi-Rail Proof Report

**Status:** Verified | **Run ID:** 1773948374 | **Date:** 2025-03-15

---

## Executive Summary

This report documents a **successful live end-to-end multi-rail agent commerce flow**:

1. **XRPL** — Machine-native payment (1 XRP) verified on testnet
2. **Celo** — Private settlement (task lifecycle + escrow + 4 withdrawals) on Celo Sepolia

Both rails executed on public testnets with verifiable transaction hashes.

---

## 1. XRPL Payment (Machine Rail)

| Field | Value |
|-------|-------|
| **Tx Hash** | `3943947D18BBD22006E9A1B1DE1E9C3B9FF55679358F898568464383F4F03FBB` |
| **Explorer** | [View on XRPL Testnet](https://testnet.xrpl.org/transactions/3943947D18BBD22006E9A1B1DE1E9C3B9FF55679358F898568464383F4F03FBB) |
| **Payer** | `rsyAXyxtBu2yexX7bWxuh3wZRvA98FXRzW` |
| **Receiver** | `rBTkGWdrqnJL8s7aHwnFJTnEVnV3nZ8b5` |
| **Amount** | 1 XRP |
| **Verification** | ✅ `real_xrpl_payment` |
| **Network** | XRPL Testnet |

---

## 2. Celo Settlement (Private Rail)

| Field | Value |
|-------|-------|
| **Chain** | Celo Sepolia (11142220) |
| **Explorer** | [celo-sepolia.blockscout.com](https://celo-sepolia.blockscout.com) |
| **Internal Task ID** | 3 |
| **Task Status** | Finalized |
| **Compute Marketplace** | `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9` |

### Correlated Celo Transaction Hashes

| Step | Role | Tx Hash | Link |
|------|------|---------|------|
| createTask | ROOT_STRATEGIST | `1aac5a55...` | [View](https://celo-sepolia.blockscout.com/tx/1aac5a558a509e65f310d3ff2bc04bc549b45deca05e5c378bdc0275e3428db0) |
| acceptTask | IP_GENERATOR | `ff2afe36...` | [View](https://celo-sepolia.blockscout.com/tx/ff2afe36e8feb804ce67b270726973789e9f1e0cb2f01ba00b5410823d48fcfd) |
| submitResult | IP_GENERATOR | `12a33ca5...` | [View](https://celo-sepolia.blockscout.com/tx/12a33ca59a6bed458c774a7f54875f4ee57fab9c4efed04adc0ac30d68c0769a) |
| submitTaskScore | DEPLOYER | `ad04eeff...` | [View](https://celo-sepolia.blockscout.com/tx/ad04eeff34436488b22c81dc93cbd55f9328accfb24024118de88931d04b417d) |
| finalizeTask | DEPLOYER | `ed0c968b...` | [View](https://celo-sepolia.blockscout.com/tx/ed0c968b5b85ad494a6dc0b0c5a3e293a562a588005fb1e7a37315ce88847af5) |
| withdraw (requester) | ROOT_STRATEGIST | `6b69e441...` | [View](https://celo-sepolia.blockscout.com/tx/6b69e4410451ab5f804106e41b12bb6802857d957171ac46e86554ca56543315) |
| withdraw (worker) | IP_GENERATOR | `c044b78a...` | [View](https://celo-sepolia.blockscout.com/tx/c044b78ad1eb0acb5da238670888842fbf5a6dc2720af1b8299ee8830fd3a81c) |
| withdraw (treasury) | TREASURY | `eecd07a5...` | [View](https://celo-sepolia.blockscout.com/tx/eecd07a5aa560d4e73e2638ece6ae5a31d5a79cc7cd2b372caeb327731f8fdd3) |
| withdraw (finance) | FINANCE_DISTRIBUTOR | `ee2c9808...` | [View](https://celo-sepolia.blockscout.com/tx/ee2c98084c8a0cbde4764c50bc942065d202c51e75ce2c611e14dca7d8b528d6) |

---

## 3. Settlement Accounting by Category

| Category | Address | Amount (CELO) | Status |
|----------|---------|---------------|--------|
| **Protocol fee** | `0xD92264f5f6a98B62ff635e0F0b77c8A059Eb3Bb6` | 0.001 | ✅ Withdrawn |
| **Finance fee** | `0xCF3572136265A5ED34D412200E63017e39223592` | 0.005 | ✅ Withdrawn |
| **Worker payout** | `0xC3032259c26Ae78cd305a868De39A2373b94d0C2` | 0.00076 | ✅ Withdrawn |
| **Requester refund** | `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` | 0.00324 | ✅ Withdrawn |

**Settlement matches expected:** Yes

---

## 4. Correlation

| XRPL Tx Hash | Internal Task ID | Celo Tx Count |
|--------------|-----------------|---------------|
| `3943947D18BBD22006E9A1B1DE1E9C3B9FF55679358F898568464383F4F03FBB` | 3 | 9 |

**Flow:** XRPL payment → Celo task lifecycle → full settlement (all 4 withdrawals)

---

## 5. Final Outcome

| Metric | Value |
|--------|-------|
| **Overall** | ✅ Success |
| **Payment rail** | XRPL (live) |
| **Settlement rail** | Celo (live) |
| **Boundary** | `hybrid:public_intake->private_onchain_settlement` |
| **Live proven** | Yes |

---

## Related Artifacts

- `live_xrpl_to_celo_proof_report.json` — Machine-readable proof
- `communication_trace.md` — Step-by-step event timeline
- `multi_rail_run_report.json` — Full run output
