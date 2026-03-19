# Olas activation checklist

- Timestamp: `1773897110`
- Config complete (ready for live request): `False`

## What is missing

- OLAS_ENABLED=1
- OLAS_EOA_PRIVATE_KEY
- OLAS_PRIORITY_MECH_ADDRESS
- OLAS_TOOL
- Fund EOA on Gnosis (see olas_funding_address.txt)

## Address to fund (Gnosis)

Fund this EOA on Gnosis with xDAI for gas and mech execution:

```
0x7cC75Cb478bA5bEC29F7332cd1D2aBBcdB11073D
```

(Also written to `olas_funding_address.txt`.)

## Variables still needing values

- **OLAS_ENABLED**: set in `.env`
- **OLAS_EOA_PRIVATE_KEY**: set in `.env`
  - (Generated key was printed to stdout; add it to .env and do not commit.)
- **OLAS_PRIORITY_MECH_ADDRESS**: set in `.env`
- **OLAS_TOOL**: set in `.env`
- **OLAS_MECHX_PATH**: set in `.env`

## Checklist detail

- [x] **MECHX_EXECUTABLE**: {"ok": true, "path": "C:\\Users\\hobie\\Swarm-Economy\\.venv-olas\\Scripts\\mechx.exe"}
- [ ] **OLAS_ENABLED**: {"ok": false, "value": "(not set)"}
- [x] **OLAS_CHAIN_CONFIG**: {"ok": true, "value": "gnosis"}
- [ ] **OLAS_EOA_PRIVATE_KEY**: {"ok": false, "action": "Add the generated key to .env (see below) and fund the address in olas_funding_address.txt", "generated_address": "0x7cC75Cb478bA5bEC29F7332cd1D2aBBcdB11073D"}
- [ ] **OLAS_PRIORITY_MECH_ADDRESS**: {"ok": false, "value": null}
- [ ] **OLAS_TOOL**: {"ok": false, "value": null}
- [ ] **EOA_FUNDED_GNOSIS**: {"ok": false, "address": "0x7cC75Cb478bA5bEC29F7332cd1D2aBBcdB11073D", "balance_wei": 0, "balance_note": "RPC not connected"}
