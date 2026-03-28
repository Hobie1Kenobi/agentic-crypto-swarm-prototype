# 24-Hour Soak Test — Root Cause Analysis

## Summary

The 15.6% success rate was **not intentional**. It was caused by `.env` being updated mid-run, switching to a different `ComputeMarketplace` contract that fails the five-distinct-addresses check.

## Timeline

| Cycles | Marketplace contract | Result |
|--------|----------------------|--------|
| 0–14   | `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9` | Success |
| 15–95  | `0x447a9438808e126219528a9bc62c2becc66e9cf1` | Failure |

**Evidence:** In `artifacts/traces/soak-24h/`:
- `cycle_0000` through `cycle_0014`: `compute_marketplace_address` = `0xad8eaf...`
- `cycle_0015` through `cycle_0095`: `compute_marketplace_address` = `0x447a94...`

## Failure error

```
Private demo requires five distinct addresses: requester, worker, validator, treasury, finance_distributor.
Set TREASURY_PRIVATE_KEY and TREASURY_ADDRESS at deploy so treasury is distinct from the other four.
```

## Root cause

Between cycle 14 (≈08:34 UTC) and cycle 15 (≈08:49 UTC), the environment used by the soak test changed. In practice, `COMPUTE_MARKETPLACE_ADDRESS` or `PRIVATE_MARKETPLACE_ADDRESS` in `.env` was switched from:

- **Working contract:** `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9` (treasury/finance distinct from all agent roles)
- **Broken contract:** `0x447a9438808e126219528a9bc62c2becc66e9cf1` (treasury or finance overlaps with requester/worker/validator)

`task_market_demo.py` reads the marketplace address from env and checks that all five addresses are distinct. With `0x447a94...`, the check fails and the cycle is reported as failed.

## Why the 6h run had 100% success

The 6h run used `.env` that consistently pointed at `0xad8eaf...`. No env change occurred during the run, so all 24 cycles succeeded.

## Why this was not “fails in action”

- Failures are not due to load, RPC, XRPL, or Celo logic.
- Failures are caused by pointing at the wrong marketplace contract after `.env` was updated during the 24h run.
- A soak test is meant to stress real flows, not a configuration change mid-run.

## Possible causes of the .env change

1. `scripts/fetch-and-save-addresses.ps1` or similar overwriting `.env`
2. A new deployment or manual edit updating `COMPUTE_MARKETPLACE_ADDRESS`
3. Another process or script altering `.env` while the soak test was running

## Mitigation

1. **Load env once at start:** At soak test startup, read the marketplace address (and other critical env) into local variables and reuse them for all cycles instead of re-reading `.env` each cycle.
2. **Validate before run:** Add a pre-flight check that the configured marketplace has five distinct addresses and fail fast if not.
3. **Lock critical config:** Optionally snapshot critical env vars at start and log a warning if they change mid-run.

## Recommended fix

Update the soak test runner so it does not re-load `.env` per cycle, or at least does not re-read `COMPUTE_MARKETPLACE_ADDRESS` / `PRIVATE_MARKETPLACE_ADDRESS` after the first cycle, to avoid mid-run configuration changes from affecting the run.
