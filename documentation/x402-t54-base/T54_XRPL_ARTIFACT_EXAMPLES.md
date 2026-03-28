# T54 XRPL Artifact Examples

## Mainnet-configured example artifact

```json
{
  "payment_attempt_id": "a1b2c3d4e5f6",
  "mode": "mainnet",
  "facilitator_url": "https://xrpl-facilitator-mainnet.t54.ai",
  "network": "mainnet",
  "wallet_address": "rPEPPER7kfTD9w2To4CQk6UCfuHM9c6GDY",
  "receiver_address": "rMerchant123456789012345678901234",
  "quote_id": "quote-abc",
  "invoice_id": "INV-xyz-123",
  "destination_tag": 100001,
  "memo_ref": "query: What is agentic commerce?",
  "amount_xrp": "1",
  "amount_drops": "1000000",
  "signed_blob_present": true,
  "submit_status": "ok",
  "verify_status": "ok",
  "settle_status": "ok",
  "xrpl_tx_hash": "ABC123DEF456789...",
  "ledger_index": 87654321,
  "validated": true,
  "error_type": "",
  "error_message": "",
  "verification_status": "real_t54_xrpl_payment",
  "reason": "",
  "facilitator_response": "{\"success\":true,\"transaction\":\"...\"}"
}
```

## Testnet-blocked artifact

```json
{
  "payment_attempt_id": "blocked001",
  "mode": "testnet",
  "facilitator_url": "",
  "network": "testnet",
  "wallet_address": "(from_seed)",
  "receiver_address": "",
  "quote_id": "",
  "invoice_id": "",
  "destination_tag": null,
  "memo_ref": "",
  "amount_xrp": "",
  "amount_drops": "",
  "signed_blob_present": false,
  "submit_status": "",
  "verify_status": "",
  "settle_status": "",
  "xrpl_tx_hash": null,
  "ledger_index": null,
  "validated": false,
  "error_type": "",
  "error_message": "",
  "verification_status": "testnet_facilitator_unavailable",
  "reason": "testnet_facilitator_unavailable",
  "facilitator_response": "absent"
}
```

## Local/dev-mode artifact

```json
{
  "payment_attempt_id": "local001",
  "mode": "local",
  "facilitator_url": "",
  "network": "testnet",
  "wallet_address": "(from_seed)",
  "receiver_address": "",
  "quote_id": "",
  "invoice_id": "",
  "destination_tag": null,
  "memo_ref": "",
  "amount_xrp": "",
  "amount_drops": "",
  "signed_blob_present": false,
  "submit_status": "",
  "verify_status": "",
  "settle_status": "",
  "xrpl_tx_hash": null,
  "ledger_index": null,
  "validated": false,
  "error_type": "",
  "error_message": "",
  "verification_status": "local_dev_only",
  "reason": "T54_XRPL_DRY_RUN=true",
  "facilitator_response": "dry_run_skip"
}
```
