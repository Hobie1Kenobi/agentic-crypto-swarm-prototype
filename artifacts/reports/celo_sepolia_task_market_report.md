# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `11142220`
- Marketplace: `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9`
- TaskId: `208`
- Task status: `Finalized`
- Escrow: `0.01` CELO (`10000000000000000` wei)
- Requester: `0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC` (`ROOT_STRATEGIST`)
- Worker: `0xC3032259c26Ae78cd305a868De39A2373b94d0C2` (`IP_GENERATOR`)
- Validator: `0xAa0d73B8dFc2C1AaAa8de6e6b26A9D7281A8236b` (`DEPLOYER`)
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
- 0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC: before=3240000000000000 wei, after=0 wei, tx=78b0eaf3c13ec9c9c67431c785337ef0cb69e540426650e9058521428127d1b4
- 0xC3032259c26Ae78cd305a868De39A2373b94d0C2: before=760000000000000 wei, after=0 wei, tx=c719cc556c046d6f8b25f55ac7fad9ed6f9b1244930ba30855eea0608c4d1e1e
- 0xD92264f5f6a98B62ff635e0F0b77c8A059Eb3Bb6: before=1000000000000000 wei, after=0 wei, tx=0ca318e9e8c4605f5598b31ff9491689ed3fa48521ebeef809dc25f60a199eb1
- 0xCF3572136265A5ED34D412200E63017e39223592: before=5000000000000000 wei, after=0 wei, tx=e97ec7c477563fb24d81309cd9da0bc1cd4f011384c14dcc3dcf99e97355271e

## Transaction Links
- createTask [ROOT_STRATEGIST]: `b65be25896246189e1e9c18f1006781ad1a83a39185b7031dd79a0958103f006` -> https://celo-sepolia.blockscout.com/tx/b65be25896246189e1e9c18f1006781ad1a83a39185b7031dd79a0958103f006
- acceptTask [IP_GENERATOR]: `8a1b6fc21113f922f417ca749a394bee7fd2c6f742bf13dd770e370ab9d4f4a8` -> https://celo-sepolia.blockscout.com/tx/8a1b6fc21113f922f417ca749a394bee7fd2c6f742bf13dd770e370ab9d4f4a8
- submitResult [IP_GENERATOR]: `9738295276c344df0ece6c1c321d6aa3544a3225af004ee2e2b67cf4f9af3e1a` -> https://celo-sepolia.blockscout.com/tx/9738295276c344df0ece6c1c321d6aa3544a3225af004ee2e2b67cf4f9af3e1a
- submitTaskScore [DEPLOYER]: `035a7decce079160bc087b6f2a48f38f723185396e97b0cda0a5dce962735b21` -> https://celo-sepolia.blockscout.com/tx/035a7decce079160bc087b6f2a48f38f723185396e97b0cda0a5dce962735b21
- finalizeTask [DEPLOYER]: `7335f34c72803e684400b859c37c54057b6b4446129c891995b4267908c5f84c` -> https://celo-sepolia.blockscout.com/tx/7335f34c72803e684400b859c37c54057b6b4446129c891995b4267908c5f84c
- withdraw [ROOT_STRATEGIST]: `78b0eaf3c13ec9c9c67431c785337ef0cb69e540426650e9058521428127d1b4` -> https://celo-sepolia.blockscout.com/tx/78b0eaf3c13ec9c9c67431c785337ef0cb69e540426650e9058521428127d1b4
- withdraw [IP_GENERATOR]: `c719cc556c046d6f8b25f55ac7fad9ed6f9b1244930ba30855eea0608c4d1e1e` -> https://celo-sepolia.blockscout.com/tx/c719cc556c046d6f8b25f55ac7fad9ed6f9b1244930ba30855eea0608c4d1e1e
- withdraw [TREASURY]: `0ca318e9e8c4605f5598b31ff9491689ed3fa48521ebeef809dc25f60a199eb1` -> https://celo-sepolia.blockscout.com/tx/0ca318e9e8c4605f5598b31ff9491689ed3fa48521ebeef809dc25f60a199eb1
- withdraw [FINANCE_DISTRIBUTOR]: `e97ec7c477563fb24d81309cd9da0bc1cd4f011384c14dcc3dcf99e97355271e` -> https://celo-sepolia.blockscout.com/tx/e97ec7c477563fb24d81309cd9da0bc1cd4f011384c14dcc3dcf99e97355271e

## Warnings (non-fatal)
- registerAsMiner: already registered (skipped).
- setValidatorAllowlist: already allowlisted (skipped).

## Errors
- (none)
