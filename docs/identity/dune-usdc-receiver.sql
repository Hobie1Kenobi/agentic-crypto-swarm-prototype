-- Agentic Swarm Marketplace — Base USDC receipts into the x402 receiver
-- Paste into Dune. Unique SKU prices map value / 1e6 onto the live catalog.

SELECT
  evt_block_time,
  evt_tx_hash,
  "from" AS payer,
  "to" AS receiver,
  value / 1e6 AS usdc
FROM erc20_base.evt_Transfer
WHERE contract_address = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
  AND "to" = 0x408f39B19266022FeC03076091e59D1f4f163658
ORDER BY evt_block_time DESC
LIMIT 500;
