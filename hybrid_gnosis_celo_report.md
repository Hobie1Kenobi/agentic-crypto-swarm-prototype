# Hybrid Gnosis (Olas adapter) -> Celo (private settlement)

## Boundaries (explicit, no silent fakes)
- real external interaction: `False` (boundary: `mocked_external_replay`)
- real private onchain settlement: `True`

## Correlation IDs
- external_request_id: `mock-1773898505`
- external_tx_hash: `None`
- internal_task_id: `8`

## Settlement Accounting (economic categories)
- protocol_fee: expected 1000000000000000 wei (0.001000 CELO); pending 1000000000000000 wei (0.001000 CELO)
- finance_fee: expected 5000000000000000 wei (0.005000 CELO); pending 5000000000000000 wei (0.005000 CELO)
- worker_payout: expected 760000000000000 wei (0.000760 CELO); pending 760000000000000 wei (0.000760 CELO)
- requester_refund: expected 3240000000000000 wei (0.003240 CELO); pending 3240000000000000 wei (0.003240 CELO)

## Combined Entitlement by Address (roles overlap)
- `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC`: expected 4240000000000000 wei (0.004240 CELO); pending 4240000000000000 wei (0.004240 CELO)
- protocol_fee: expected 1000000000000000 wei (0.001000 CELO)
- requester_refund: expected 3240000000000000 wei (0.003240 CELO)
- `0xCF3572136265A5ED34D412200E63017e39223592`: expected 5000000000000000 wei (0.005000 CELO); pending 5000000000000000 wei (0.005000 CELO)
- finance_fee: expected 5000000000000000 wei (0.005000 CELO)
- `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b`: expected 760000000000000 wei (0.000760 CELO); pending 760000000000000 wei (0.000760 CELO)
- worker_payout: expected 760000000000000 wei (0.000760 CELO)

## Remaining Blocker (if full public integration not achieved)
```json
{
  "type": "rpc_or_wallet_issue",
  "detail": "mechx failed (exit 1): Running command with agent_mode=False\n\nError: Private key file `ethereum_private_key.txt` does not exist!\nSpecify a valid key file with --key option."
}
```

## Evidence Pointers
- communication trace: `communication_trace.md`
- public adapter run: `public_adapter_run_report.json`
- private settlement: `celo_sepolia_task_market_report.json`
