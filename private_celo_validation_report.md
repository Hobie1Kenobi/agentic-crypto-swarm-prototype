# Private Celo Marketplace Validation (Celo Sepolia)

## Boundaries
- public external interaction: `(not used)`
- private onchain settlement: `contract_level_execution (real)`

## Lifecycle Proof
- chain_id: `11142220`
- compute marketplace: `0x159074bc4b8811df1ef16526766de57fb59db7db`
- task_id: `4`
- task status: `Finalized`
- escrow: `0.01 CELO` (`10000000000000000 wei`)
- requester: `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` (`ROOT_STRATEGIST`)
- worker: `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b` (`DEPLOYER`)
- validator: `0xCF3572136265A5ED34D412200E63017e39223592` (`FINANCE_DISTRIBUTOR`)
- treasury: `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` (`TREASURY`)
- finance_distributor: `0xCF3572136265A5ED34D412200E63017e39223592` (`FINANCE_DISTRIBUTOR`)

## Settlement Accounting (economic categories)
- **protocol_fee**: expected 1000000000000000 wei (0.001000 CELO); pending n/a
- **finance_fee**: expected 5000000000000000 wei (0.005000 CELO); pending 5000000000000000 wei (0.005000 CELO)
- **worker_payout**: expected 760000000000000 wei (0.000760 CELO); pending 760000000000000 wei (0.000760 CELO)
- **requester_refund**: expected 3240000000000000 wei (0.003240 CELO); pending n/a

## Combined Entitlement by Address (roles overlap)
- `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC`: expected 4240000000000000 wei (0.004240 CELO); pending 4240000000000000 wei (0.004240 CELO)
- protocol_fee: expected 1000000000000000 wei (0.001000 CELO)
- requester_refund: expected 3240000000000000 wei (0.003240 CELO)
- `0xCF3572136265A5ED34D412200E63017e39223592`: expected 5000000000000000 wei (0.005000 CELO); pending 5000000000000000 wei (0.005000 CELO)
- finance_fee: expected 5000000000000000 wei (0.005000 CELO)
- `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b`: expected 760000000000000 wei (0.000760 CELO); pending 760000000000000 wei (0.000760 CELO)
- worker_payout: expected 760000000000000 wei (0.000760 CELO)

## Withdrawal Evidence
- withdraw(0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC): role=ROOT_STRATEGIST; tx=`e718eeb394b97850f84842e72c68cdf97c04b80cabdf28b278d54394e74ccff6`
- withdraw(0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b): role=DEPLOYER; tx=`57c8353a6f40f34b90a77a5f67f37fe03c9de0a51e4ee2d6ad81d0f9bccf8399`
- withdraw(0xCF3572136265A5ED34D412200E63017e39223592): role=FINANCE_DISTRIBUTOR; tx=`04974f2ea03c758b8ada0298d408a10bc5a17b46668856c2efb7600db13e21e3`

## Raw Artifacts
- source JSON: `celo_sepolia_task_market_report.json`
