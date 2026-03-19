# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `11142220`
- Marketplace: `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9`
- TaskId: `3`
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
- 0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC: before=3240000000000000 wei, after=0 wei, tx=6b69e4410451ab5f804106e41b12bb6802857d957171ac46e86554ca56543315
- 0xC3032259c26Ae78cd305a868De39A2373b94d0C2: before=760000000000000 wei, after=0 wei, tx=c044b78ad1eb0acb5da238670888842fbf5a6dc2720af1b8299ee8830fd3a81c
- 0xD92264f5f6a98B62ff635e0F0b77c8A059Eb3Bb6: before=1000000000000000 wei, after=0 wei, tx=eecd07a5aa560d4e73e2638ece6ae5a31d5a79cc7cd2b372caeb327731f8fdd3
- 0xCF3572136265A5ED34D412200E63017e39223592: before=5000000000000000 wei, after=0 wei, tx=ee2c98084c8a0cbde4764c50bc942065d202c51e75ce2c611e14dca7d8b528d6

## Transaction Links
- createTask [ROOT_STRATEGIST]: `1aac5a558a509e65f310d3ff2bc04bc549b45deca05e5c378bdc0275e3428db0` -> https://celo-sepolia.blockscout.com/tx/1aac5a558a509e65f310d3ff2bc04bc549b45deca05e5c378bdc0275e3428db0
- acceptTask [IP_GENERATOR]: `ff2afe36e8feb804ce67b270726973789e9f1e0cb2f01ba00b5410823d48fcfd` -> https://celo-sepolia.blockscout.com/tx/ff2afe36e8feb804ce67b270726973789e9f1e0cb2f01ba00b5410823d48fcfd
- submitResult [IP_GENERATOR]: `12a33ca59a6bed458c774a7f54875f4ee57fab9c4efed04adc0ac30d68c0769a` -> https://celo-sepolia.blockscout.com/tx/12a33ca59a6bed458c774a7f54875f4ee57fab9c4efed04adc0ac30d68c0769a
- submitTaskScore [DEPLOYER]: `ad04eeff34436488b22c81dc93cbd55f9328accfb24024118de88931d04b417d` -> https://celo-sepolia.blockscout.com/tx/ad04eeff34436488b22c81dc93cbd55f9328accfb24024118de88931d04b417d
- finalizeTask [DEPLOYER]: `ed0c968b5b85ad494a6dc0b0c5a3e293a562a588005fb1e7a37315ce88847af5` -> https://celo-sepolia.blockscout.com/tx/ed0c968b5b85ad494a6dc0b0c5a3e293a562a588005fb1e7a37315ce88847af5
- withdraw [ROOT_STRATEGIST]: `6b69e4410451ab5f804106e41b12bb6802857d957171ac46e86554ca56543315` -> https://celo-sepolia.blockscout.com/tx/6b69e4410451ab5f804106e41b12bb6802857d957171ac46e86554ca56543315
- withdraw [IP_GENERATOR]: `c044b78ad1eb0acb5da238670888842fbf5a6dc2720af1b8299ee8830fd3a81c` -> https://celo-sepolia.blockscout.com/tx/c044b78ad1eb0acb5da238670888842fbf5a6dc2720af1b8299ee8830fd3a81c
- withdraw [TREASURY]: `eecd07a5aa560d4e73e2638ece6ae5a31d5a79cc7cd2b372caeb327731f8fdd3` -> https://celo-sepolia.blockscout.com/tx/eecd07a5aa560d4e73e2638ece6ae5a31d5a79cc7cd2b372caeb327731f8fdd3
- withdraw [FINANCE_DISTRIBUTOR]: `ee2c98084c8a0cbde4764c50bc942065d202c51e75ce2c611e14dca7d8b528d6` -> https://celo-sepolia.blockscout.com/tx/ee2c98084c8a0cbde4764c50bc942065d202c51e75ce2c611e14dca7d8b528d6

## Warnings (non-fatal)
- registerAsMiner: already registered (skipped).
- setValidatorAllowlist: already allowlisted (skipped).

## Errors
- (none)
