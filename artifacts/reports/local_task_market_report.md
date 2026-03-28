# Task Marketplace Demo Report
## Lifecycle Proof
- Chain ID: `31337`
- Marketplace: `0xad3a921a649d23d5d41722f3fd455f40d333292f`
- TaskId: `3`
- Task status: `Finalized`
- Escrow: `0.01` ETH (`10000000000000000` wei)
- Requester: `0xbDa6060D3f3A49bf2778968FA09c8915c7AB64c5` (`ROOT_STRATEGIST`)
- Worker: `0xBB14C637BB54D02FFa008B4b2d4E4FD03d5aC0DC` (`IP_GENERATOR`)
- Validator: `0x0932B8D499e5a93E3892A744996227ba627d1a1d` (`DEPLOYER`)
- Validator approvals: `1`
- Score: `19`

## Settlement Accounting
- Protocol fee (10%): `0.001000` ETH
- Finance fee (50%): `0.005000` ETH
- Worker payout: `0.000760` ETH
- Requester refund: `0.003240` ETH
- PendingWithdrawals matches expected: `True`

## Pending Withdrawals Created/Claimed
- Withdrawals summary: (see JSON under `withdrawals`)
- 0xbDa6060D3f3A49bf2778968FA09c8915c7AB64c5: before=3240000000000000 wei, after=0 wei, tx=6321a34a88cc20c5a4e5e82f5f5101305f55afb12673af9981ff20ff395fc17a
- 0xBB14C637BB54D02FFa008B4b2d4E4FD03d5aC0DC: before=760000000000000 wei, after=0 wei, tx=8ec4a96fe6bebd621424213290c568a35c12871d0528f5b6eff329de9808a3fa
- 0x0932B8D499e5a93E3892A744996227ba627d1a1d: before=1000000000000000 wei, after=0 wei, tx=fadadad2ea6e98a4ed50ba3e8e7b8dcae6a7481692e389d91bd53cb4ecba1ede
- 0x2156f405b1b06D1516116d4Bf4ea869ef8311bC1: before=5000000000000000 wei, after=0 wei, tx=a7ee54a56a8177d620081912e62bbb7ccac183e1628cd1775a2a1fdb0bbb48e8

## Transaction Links
- createTask [ROOT_STRATEGIST]: `3125e7ab802aa31f9590f4b196d2536b61cd7672f3562f3a9a7804c3078ce4bf` -> 3125e7ab802aa31f9590f4b196d2536b61cd7672f3562f3a9a7804c3078ce4bf
- acceptTask [IP_GENERATOR]: `4175a166ed4e7d37162ec2825912d22d4074facd5baa952ea686d89db877c33b` -> 4175a166ed4e7d37162ec2825912d22d4074facd5baa952ea686d89db877c33b
- submitResult [IP_GENERATOR]: `df2a63e9f2f0956b45b897edeab743575387b4ea05422459f84005dc7105c663` -> df2a63e9f2f0956b45b897edeab743575387b4ea05422459f84005dc7105c663
- submitTaskScore [DEPLOYER]: `1248284bbfa2f9539ce5ea426fe524fe1395535a76e01d6ec0211ec6302b5499` -> 1248284bbfa2f9539ce5ea426fe524fe1395535a76e01d6ec0211ec6302b5499
- finalizeTask [DEPLOYER]: `eeefb5498ecc4572d242d42314287e3f4f3c2280f338d8d2e0cfdf176ad073bb` -> eeefb5498ecc4572d242d42314287e3f4f3c2280f338d8d2e0cfdf176ad073bb
- withdraw [ROOT_STRATEGIST]: `6321a34a88cc20c5a4e5e82f5f5101305f55afb12673af9981ff20ff395fc17a` -> 6321a34a88cc20c5a4e5e82f5f5101305f55afb12673af9981ff20ff395fc17a
- withdraw [IP_GENERATOR]: `8ec4a96fe6bebd621424213290c568a35c12871d0528f5b6eff329de9808a3fa` -> 8ec4a96fe6bebd621424213290c568a35c12871d0528f5b6eff329de9808a3fa
- withdraw [OWNER]: `fadadad2ea6e98a4ed50ba3e8e7b8dcae6a7481692e389d91bd53cb4ecba1ede` -> fadadad2ea6e98a4ed50ba3e8e7b8dcae6a7481692e389d91bd53cb4ecba1ede
- withdraw [FINANCE_DISTRIBUTOR]: `a7ee54a56a8177d620081912e62bbb7ccac183e1628cd1775a2a1fdb0bbb48e8` -> a7ee54a56a8177d620081912e62bbb7ccac183e1628cd1775a2a1fdb0bbb48e8

## Warnings (non-fatal)
- registerAsMiner: already registered (skipped).
- setValidatorAllowlist: already allowlisted (skipped).

## Errors
- (none)
