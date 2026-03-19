# Hybrid Clean Proof Report

## Boundaries (no silent fakes)
- public external interaction: `mocked_external_replay`
- private onchain settlement: `contract_level_execution`

## Public intake (adapter)
- ok: `True`
- market_mode: `hybrid`
- external_request_id: `mock-1773893520`
- notes: `OLAS_ENABLED is not set (set OLAS_ENABLED=1 to attempt live).`

## Private marketplace (Celo/Anvil) execution
- chain_id: `11142220`
- compute_marketplace: `0x159074bc4b8811df1ef16526766de57fb59db7db`
- task_id: `3`

### Runtime roles (addresses)
- requester: `ROOT_STRATEGIST` `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC`
- worker: `DEPLOYER` `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b`
- validator: `FINANCE_DISTRIBUTOR` `0xCF3572136265A5ED34D412200E63017e39223592`
- treasury: `TREASURY` `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC`
- finance_distributor: `FINANCE_DISTRIBUTOR` `0xCF3572136265A5ED34D412200E63017e39223592`

## Settlement accounting (economic categories)
- **protocol_fee**: to `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` expected 1000000000000000 wei (0.001000 CELO); actual_pending combined (see by-address)
- **finance_fee**: to `0xCF3572136265A5ED34D412200E63017e39223592` expected 5000000000000000 wei (0.005000 CELO); actual_pending 5000000000000000 wei (0.005000 CELO)
- **worker_payout**: to `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b` expected 760000000000000 wei (0.000760 CELO); actual_pending 760000000000000 wei (0.000760 CELO)
- **requester_refund**: to `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` expected 3240000000000000 wei (0.003240 CELO); actual_pending combined (see by-address)

## Combined entitlement by address (when roles overlap)
- `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` (ROOT_STRATEGIST): expected 4240000000000000 wei (0.004240 CELO); pending 4240000000000000 wei (0.004240 CELO)
  - protocol_fee: expected 1000000000000000 wei (0.001000 CELO)
  - requester_refund: expected 3240000000000000 wei (0.003240 CELO)
- `0xCF3572136265A5ED34D412200E63017e39223592` (FINANCE_DISTRIBUTOR): expected 5000000000000000 wei (0.005000 CELO); pending 5000000000000000 wei (0.005000 CELO)
  - finance_fee: expected 5000000000000000 wei (0.005000 CELO)
- `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b` (DEPLOYER): expected 760000000000000 wei (0.000760 CELO); pending 760000000000000 wei (0.000760 CELO)
  - worker_payout: expected 760000000000000 wei (0.000760 CELO)

## Evidence pointers
- See `communication_trace.md` for step-by-step boundary markers.
- See `public_adapter_run_report.json` and `celo_sepolia_task_market_report.json` for raw data.
