# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `11142220`
- Marketplace: `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9`
- TaskId: `27`
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
- 0x9E3A6f34B7cf6d9bDd621758ED7B0A81145388DC: before=3240000000000000 wei, after=0 wei, tx=e03f9c1e2a5d47f6625ed6efc98bdb57220ce41203bcd8666389639c2b45cdc3
- 0xC3032259c26Ae78cd305a868De39A2373b94d0C2: before=760000000000000 wei, after=0 wei, tx=c4f41e4812b33429675edf4c7458ef99ce2942f78a515a773db68d758899561c
- 0xD92264f5f6a98B62ff635e0F0b77c8A059Eb3Bb6: before=1000000000000000 wei, after=0 wei, tx=a9049bf96f68358bea9fa27bc23a7515ab3fa8f4d39ee16904678d55f0939eb8
- 0xCF3572136265A5ED34D412200E63017e39223592: before=5000000000000000 wei, after=0 wei, tx=20efd292aeef30cb5e01b69d86d2d0add0cfb75f8b20e40ac6bd7a5619b31518

## Transaction Links
- createTask [ROOT_STRATEGIST]: `385e9da45c62849dc0799c9145b0006396063a229873999ede0f1741960c0b6e` -> https://celo-sepolia.blockscout.com/tx/385e9da45c62849dc0799c9145b0006396063a229873999ede0f1741960c0b6e
- acceptTask [IP_GENERATOR]: `150c778891dea7deab1a22ec9e9b39fd66bbc14f373b6ffa7157c56ff4b4b63a` -> https://celo-sepolia.blockscout.com/tx/150c778891dea7deab1a22ec9e9b39fd66bbc14f373b6ffa7157c56ff4b4b63a
- submitResult [IP_GENERATOR]: `d477d2215caf34febe6036594549696e811dbfebdc77a73a07648edf85323527` -> https://celo-sepolia.blockscout.com/tx/d477d2215caf34febe6036594549696e811dbfebdc77a73a07648edf85323527
- submitTaskScore [DEPLOYER]: `747014a0023cd4026acfeaa7bc01d994839c190acf77d0307194c6c5e1fc05f1` -> https://celo-sepolia.blockscout.com/tx/747014a0023cd4026acfeaa7bc01d994839c190acf77d0307194c6c5e1fc05f1
- finalizeTask [DEPLOYER]: `cfb5a203aeb3fb7a55139c19515a47fe2c405a641251f83bb17d1e8e3269cd03` -> https://celo-sepolia.blockscout.com/tx/cfb5a203aeb3fb7a55139c19515a47fe2c405a641251f83bb17d1e8e3269cd03
- withdraw [ROOT_STRATEGIST]: `e03f9c1e2a5d47f6625ed6efc98bdb57220ce41203bcd8666389639c2b45cdc3` -> https://celo-sepolia.blockscout.com/tx/e03f9c1e2a5d47f6625ed6efc98bdb57220ce41203bcd8666389639c2b45cdc3
- withdraw [IP_GENERATOR]: `c4f41e4812b33429675edf4c7458ef99ce2942f78a515a773db68d758899561c` -> https://celo-sepolia.blockscout.com/tx/c4f41e4812b33429675edf4c7458ef99ce2942f78a515a773db68d758899561c
- withdraw [TREASURY]: `a9049bf96f68358bea9fa27bc23a7515ab3fa8f4d39ee16904678d55f0939eb8` -> https://celo-sepolia.blockscout.com/tx/a9049bf96f68358bea9fa27bc23a7515ab3fa8f4d39ee16904678d55f0939eb8
- withdraw [FINANCE_DISTRIBUTOR]: `20efd292aeef30cb5e01b69d86d2d0add0cfb75f8b20e40ac6bd7a5619b31518` -> https://celo-sepolia.blockscout.com/tx/20efd292aeef30cb5e01b69d86d2d0add0cfb75f8b20e40ac6bd7a5619b31518

## Warnings (non-fatal)
- registerAsMiner: already registered (skipped).
- setValidatorAllowlist: already allowlisted (skipped).

## Errors
- (none)
