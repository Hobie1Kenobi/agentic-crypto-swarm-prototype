# 13 — Mainnet preflight (2026-09-02)

No seeds used. No Payment / Escrow / TrustSet. Xaman is the only intended signer.

## Frozen template check

| Check | Result |
|---|---|
| payTo in templates | `rHyLmYewCQABAx6MMRBBuYYUUYWve2E1Lf` PASS |
| identity in templates | `rHTHaQ9EtuKkSSAoh9R1ViGt69J2ZMHQWq` PASS |
| Domain hex | `6167656E7469632D737761726D2D6D61726B6574706C6163652E636F6D` = `agentic-swarm-marketplace.com` PASS |
| Catalog SHA3-512 prefix | `46a60a5fd7eebe24` PASS (`asm:sku-catalog:v1`) |
| Credential type | `ASM-T54-PayTo` (hex `41534D2D5435342D506179546F`) — keep 08 spelling, not `ASM-T54-PAYTO` |

## Live HTTP

After seller restart on this host (Caddy :9080 → :8043 / :8765):

| URL | Result |
|---|---|
| https://api.agentic-swarm-marketplace.com/.well-known/xrp-ledger.toml | **PASS** 200, both r-addresses |
| https://api.agentic-swarm-marketplace.com/.well-known/did.json | **PASS** 200 |
| https://api.agentic-swarm-marketplace.com/.well-known/x402.json | **PASS** 200, `xrpl:0` + `t54/.well-known/x402.json` |
| https://api.agentic-swarm-marketplace.com/t54/.well-known/x402.json | **PASS** 200, payTo frozen |
| https://api.agentic-swarm-marketplace.com/t54/catalog-snapshot | **PASS** 200, hash `46a60a5f…` |
| https://api.agentic-swarm-marketplace.com/t54/verify | **PASS** 200 (unpaid; `ok=false` until `?hash=` matches) |
| https://www.agentic-swarm-marketplace.com/.well-known/xrp-ledger.toml | **FAIL** 404 at preflight start — Pages not deployed yet |
| https://www.agentic-swarm-marketplace.com/.well-known/xrpl-merchant.json | **FAIL** 404 at preflight start |
| https://www.agentic-swarm-marketplace.com/.well-known/did.json | **FAIL** 404 at preflight start |
| https://agentic-swarm-marketplace.com/.well-known/xrp-ledger.toml | **FAIL** DNS `getaddrinfo` — no A/AAAA |

**Domain hex is not changed.** Identity already has `agentic-swarm-marketplace.com`. Bidirectional proof until apex exists: **www + api** toml, same bytes. Step 1 (payTo Domain) waits until www toml is 200 so we do not point Domain at a 404 host.

`GET /t54/verify` first returned 422 (`request` query required) because `from __future__ import annotations` hid FastAPI’s `Request` type. Fixed in `identity/routes.py`; sellers restarted.

## AccountRoots (validated, `s1.ripple.com:51234`, ledger ~106718094)

| | identity `rHTH…Wq` | payTo `rHyL…1Lf` |
|---|---|---|
| Sequence | 94639456 | 103294535 |
| Balance (drops) | 23012602 | 5026411 |
| Flags | 0 | 0 |
| RegularKey | none | none |
| OwnerCount | 5 | 0 |
| Domain | `agentic-swarm-marketplace.com` | **empty** |
| DID object | entryNotFound | entryNotFound |
| disableMaster | false | false — **P0 HOT** |

Identity SigningPubKey (Domain tx `D97C1C07…B3F1`): `032B97245BB2145B1EFC0D2756555F533353B8D53A9E2B430EE44D025E49067999` (secp256k1). Hosted `did.json` uses this as `verificationMethod` — not invented.

## Amendments

| Amendment | Enabled on mainnet |
|---|---|
| `DID` (XLS-40) | **yes** |
| `fixEmptyDID` | **yes** |
| `Credentials` (XLS-70) | **yes** — CredentialCreate/Accept are in scope after DIDSet |

## Xumm keys

Present in local `.env` / `.env.mainnet` (values not printed). Payload create is allowed. No xrpl seed used to submit.

## Go / no-go for payloads

| Step | Allowed now? |
|---|---|
| 1 payTo Domain | After www toml **200** |
| 2 DIDSet | After Step 1 tesSUCCESS |
| 3 Credential | After Step 2; amendment live |
| 4 catalog memo | Optional after Step 2/3 |
| 5 RegularKey | **STOP** — no RegularKey address provided |
| 6 disable master | **STOP** — waiting for `DISABLE_MASTER` |
