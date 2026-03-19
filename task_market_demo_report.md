# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `11142220`
- Marketplace: `0x159074bc4b8811df1ef16526766de57fb59db7db`
- TaskId: `8`
- Task status: `Finalized`
- Escrow: `0.01` CELO (`10000000000000000` wei)
- Requester: `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` (`ROOT_STRATEGIST`)
- Worker: `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b` (`DEPLOYER`)
- Validator: `0xCF3572136265A5ED34D412200E63017e39223592` (`FINANCE_DISTRIBUTOR`)
- Validator approvals: `1`
- Score: `19`

## Settlement Accounting
- Protocol fee (10%): `0.001000` CELO
- Finance fee (50%): `0.005000` CELO
- Worker payout: `0.000760` CELO
- Requester refund: `0.003240` CELO
- PendingWithdrawals matches expected: `True`

## Pending Withdrawals Created/Claimed
- Withdrawals summary: (see JSON under `withdrawals`)
- 0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC: before=4240000000000000 wei, after=0 wei, tx=f517180ae63a3279c761ec3df6514882e90bcf80a35829daea8507928f0de0e4
- 0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b: before=760000000000000 wei, after=0 wei, tx=4726fddfa27da86749f036be78d276a7026eb2ea2d508c1d29c9684cba62fec7
- 0xCF3572136265A5ED34D412200E63017e39223592: before=5000000000000000 wei, after=0 wei, tx=6bd466507711df47a0f1ef737d9a07a020ba2c2d8efd94eb709b68f095102980

## Transaction Links
- createTask [ROOT_STRATEGIST]: `882cf86a8aed6e60064feb8b5ac2acec1572b710078cbe59bc999c55d7f641fc` -> https://celo-sepolia.blockscout.com/tx/882cf86a8aed6e60064feb8b5ac2acec1572b710078cbe59bc999c55d7f641fc
- acceptTask [DEPLOYER]: `48fd38dc607e8db954227fc662a25bc35ab828e369db6790ce55231f0316e753` -> https://celo-sepolia.blockscout.com/tx/48fd38dc607e8db954227fc662a25bc35ab828e369db6790ce55231f0316e753
- submitResult [DEPLOYER]: `4a072c63a3f20dccd568e6b94ca3e4a81e734752792a6e44dfca62084d7f539d` -> https://celo-sepolia.blockscout.com/tx/4a072c63a3f20dccd568e6b94ca3e4a81e734752792a6e44dfca62084d7f539d
- submitTaskScore [FINANCE_DISTRIBUTOR]: `7a865c5ad8912988544069b8f9918e0aa0c9cd23bdb29a68ce0bc264080ceb04` -> https://celo-sepolia.blockscout.com/tx/7a865c5ad8912988544069b8f9918e0aa0c9cd23bdb29a68ce0bc264080ceb04
- finalizeTask [FINANCE_DISTRIBUTOR]: `5abd07d292808feea04c82740c3266043d52ffbadd16cb3d803103b43ded45a3` -> https://celo-sepolia.blockscout.com/tx/5abd07d292808feea04c82740c3266043d52ffbadd16cb3d803103b43ded45a3
- withdraw [ROOT_STRATEGIST]: `f517180ae63a3279c761ec3df6514882e90bcf80a35829daea8507928f0de0e4` -> https://celo-sepolia.blockscout.com/tx/f517180ae63a3279c761ec3df6514882e90bcf80a35829daea8507928f0de0e4
- withdraw [DEPLOYER]: `4726fddfa27da86749f036be78d276a7026eb2ea2d508c1d29c9684cba62fec7` -> https://celo-sepolia.blockscout.com/tx/4726fddfa27da86749f036be78d276a7026eb2ea2d508c1d29c9684cba62fec7
- withdraw [FINANCE_DISTRIBUTOR]: `6bd466507711df47a0f1ef737d9a07a020ba2c2d8efd94eb709b68f095102980` -> https://celo-sepolia.blockscout.com/tx/6bd466507711df47a0f1ef737d9a07a020ba2c2d8efd94eb709b68f095102980

## Warnings (non-fatal)
- registerAsMiner: already registered (skipped).
- setValidatorAllowlist: already allowlisted (skipped).

## Errors
- (none)
