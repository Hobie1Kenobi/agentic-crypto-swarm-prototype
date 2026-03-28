# Customer Balance Layer Demo Report

**Date:** 2026-03-21T05:59:01Z

- **Balance layer (credit/debit):** ✅ OK
- **Celo settlement:** ✅ OK

## Flow

- 1. XRPL payment (mock/live) -> verified receipt
- 2. Credit customer balance (XRP/RLUSD -> wei)
- 3. Budget check (balance >= escrow)
- 4. Debit escrow
- 5. createTask on Celo Sepolia
- 6. Metering record

## Customer Balance Activity

- **Customer ID:** `mock-1774072672`
- **Balance (after):** 0 wei
- **Credits:** 1
- **Debits:** 1
- **Metering records:** 0

### Credits
- +10000000000000000 wei (XRP) ref=498E60B41CF24DE329EC...
### Debits
- -10000000000000000 wei task_id=None

## Celo Settlement

- **Task ID:** 43
- **ComputeMarketplace:** `0xad8eaf9436b2580172e65d537ef9cf7d5f06a5a9`

- [createTask](https://celo-sepolia.blockscout.com/tx/50d83aadfe2ee7a97f1a684b73206111e139f08ab349d851ac211c5b425b0675)
- [acceptTask](https://celo-sepolia.blockscout.com/tx/1a7aca661e259834b0b0d4349cab3077b819ed72a12294f3643cbd1311ea7c98)
- [submitResult](https://celo-sepolia.blockscout.com/tx/9fdb8d1b308baf9da494ac18289852e1a62a918c5558926ce7fef5a295bebcf5)
- [submitTaskScore](https://celo-sepolia.blockscout.com/tx/f017e08f01c338153951f1aab11a14779b503c0129c791493b9489fd968e435b)
- [finalizeTask](https://celo-sepolia.blockscout.com/tx/3d53a8751a51c4c69a0b45e3080d1a37dbba929765a1eb28da8dce1e290d7aa2)
- [withdraw](https://celo-sepolia.blockscout.com/tx/0af0299cd6e6f126949dbed6f809efc9065edce332ae3396c39c9eb19c09e94b)
- [withdraw](https://celo-sepolia.blockscout.com/tx/cc0577759a9e55c33901d40c709f912b99b4237ee9ecd7858bffce5c899d3cf9)
- [withdraw](https://celo-sepolia.blockscout.com/tx/1490c237af9d0d61c4e4f3b999219c8b1fb0e67ae8962c32831a8c93e4e674e8)
- [withdraw](https://celo-sepolia.blockscout.com/tx/ca4b815c5756ddf283bca358fa6140021ab7ad10febee9b25442aff61b410ab3)
