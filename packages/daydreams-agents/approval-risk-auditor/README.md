# Approval Risk Auditor

x402 agent for [daydreamsai/agent-bounties#5](https://github.com/daydreamsai/agent-bounties/issues/5).

Scans ERC-20 `Approval` logs and live `allowance()` reads to flag unlimited/stale/high approvals and emit revoke calldata.

## Run

```bash
cd packages/daydreams-agents/approval-risk-auditor
npm install
npm start
```

Port **8095**

## Invoke

```bash
curl http://127.0.0.1:8095/health

curl -X POST http://127.0.0.1:8095/entrypoints/audit/invoke \
  -H 'content-type: application/json' \
  -d '{"wallet":"0x408f39B19266022FeC03076091e59D1f4f163658","chains":["base"]}'
```
