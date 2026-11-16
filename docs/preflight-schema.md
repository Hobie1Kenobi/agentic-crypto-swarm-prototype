# Agent pre-flight check — `asm.preflight.v1`

Headline SKU for Agentic Swarm Marketplace. Screen a contract, a seller/`payTo`, and an optional resource URL before an agent pays.

- HTTP: `GET https://api.agentic-swarm-marketplace.com/x402/v1/preflight`
- MCP tool: `preflight_check` (first/top tool on `/mcp`)
- Price after the free daily quota: **$0.01 USDC** on Base (`eip155:8453`) via the CDP x402 facilitator
- Free tier: **5 calls per caller per UTC day** (counted by a hash of the client IP). Invalid input is a free `400` and does not consume the quota. Calls past the quota return a normal `402`.
- Supported networks: Base (`eip155:8453`) and XRPL mainnet (`xrpl:mainnet`, alias `xrpl:0`)

## Input

Query parameters (aliases in parentheses):

| Field | Required | Notes |
| --- | --- | --- |
| `contractAddress` (`address`, `contract`) | one of contract or payTo | Base EVM address, `0x` + 40 hex |
| `payTo` (`seller`, `sellerAddress`) | one of contract or payTo | Base EVM `0x…` or XRPL classic `r…` |
| `resource` (`url`, `resourceUrl`) | no | Absolute URL claimed by the seller |
| `network` (`chainId`) | no | `eip155:8453` or `xrpl:mainnet` |

A request with neither a contract nor a `payTo` returns HTTP 400 and is not charged.

## Output

```json
{
  "schema": "asm.preflight.v1",
  "sku": "agent-preflight-check",
  "verdict": "SAFE | RISKY | INCONCLUSIVE",
  "riskScore": 0,
  "reasons": ["human-readable reasons"],
  "evidence": [{"check": "contract_triage", "severity": "safe", "reason": "…", "source": "blockscout_v2"}],
  "sources": ["blockscout_v2"],
  "timestamp": "2026-11-16T22:00:00Z",
  "network": ["eip155:8453"],
  "target": {"contractAddress": "0x…", "payTo": "0x…", "resource": null},
  "checks": {},
  "lookupFailed": false
}
```

`riskScore` is 0–100, where 0 is safest. It is only raised when `verdict` is `RISKY`.

## Honesty rule

- Lookup or network failure → `INCONCLUSIVE` with `lookupFailed: true`. Never `RISKY`.
- Unverified contracts without other positive evidence → `INCONCLUSIVE`, not `RISKY`.
- `RISKY` requires positive evidence (for example a malicious contract triage, XRPL `lsfGlobalFreeze`, a domain TOML that does not list the account, or a non-HTTPS resource URL).

The engine combines contract-triage (including proxy implementation resolution) with seller-trust checks: known catalogs, Blockscout address metadata, XRPL `account_info` (age via XRPScan when available, flags, domain), and `/.well-known/xrp-ledger.toml`.
