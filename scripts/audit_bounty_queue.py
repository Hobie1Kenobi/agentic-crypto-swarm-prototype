#!/usr/bin/env python3
"""Audit bounty queue → JSON + Markdown checklist."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "earning_worker.sqlite3"
COMPLETIONS = ROOT / "artifacts" / "earning_worker" / "completions"
OUT_JSON = ROOT / "artifacts" / "earning_worker" / "QUEUE_AUDIT.json"
OUT_MD = ROOT / "artifacts" / "earning_worker" / "QUEUE_AUDIT.md"
OPEN_PRS = ROOT / "artifacts" / "earning_worker" / "QUEUE_OPEN_PRS.json"

# Manual map: issue → PR (verified via gh)
KNOWN_PR_MAP: dict[str, str] = {
    "daydreamsai/agent-bounties#1": "https://github.com/daydreamsai/agent-bounties/pull/199",
    "daydreamsai/agent-bounties#3": "https://github.com/daydreamsai/agent-bounties/pull/200",
    "daydreamsai/agent-bounties#4": "https://github.com/daydreamsai/agent-bounties/pull/201",
    "daydreamsai/agent-bounties#5": "https://github.com/daydreamsai/agent-bounties/pull/202",
    "daydreamsai/agent-bounties#6": "https://github.com/daydreamsai/agent-bounties/pull/203",
    "daydreamsai/agent-bounties#7": "https://github.com/daydreamsai/agent-bounties/pull/207",
    "daydreamsai/agent-bounties#8": "https://github.com/daydreamsai/agent-bounties/pull/205",
    "daydreamsai/agent-bounties#9": "https://github.com/daydreamsai/agent-bounties/pull/206",
    "daydreamsai/agent-bounties#10": "https://github.com/daydreamsai/agent-bounties/pull/204",
    "claude-builders-bounty/claude-builders-bounty#1": "https://github.com/claude-builders-bounty/claude-builders-bounty/pull/2081",
    "claude-builders-bounty/claude-builders-bounty#2": "https://github.com/claude-builders-bounty/claude-builders-bounty/pull/2083",
    "claude-builders-bounty/claude-builders-bounty#3": "https://github.com/claude-builders-bounty/claude-builders-bounty/pull/2082",
    "claude-builders-bounty/claude-builders-bounty#4": "https://github.com/claude-builders-bounty/claude-builders-bounty/pull/2080",
    "claude-builders-bounty/claude-builders-bounty#5": "https://github.com/claude-builders-bounty/claude-builders-bounty/pull/2084",
    "base-org/contracts#257": "https://github.com/base/contracts/pull/304",
    "base-org/contracts#258": "https://github.com/base/contracts/pull/305",
    "base-org/contracts#259": "https://github.com/base/contracts/pull/306",
    "base-org/contracts#279": "https://github.com/base/contracts/pull/303",
    "base-org/contracts#286": "https://github.com/base/contracts/pull/307",
    "coinbase/onchainkit#2646": "https://github.com/coinbase/onchainkit/pull/2662",
    "coinbase/onchainkit#2652": "https://github.com/coinbase/onchainkit/pull/2661",
    "coinbase/onchainkit#2655": "https://github.com/coinbase/onchainkit/pull/2660",
    "coinbase/onchainkit#2657": "https://github.com/coinbase/onchainkit/pull/2659",
    "celo-org/gitcoin#54": "https://github.com/electric-capital/open-dev-data/pull/2878",
}

CLAIMED_NOT_BUILT = [
    "daydreamsai/agent-bounties#2",
]

SKIP = {
    "Scottcjn/rustchain-bounties",
    "Scottcjn/Rustchain",
    "orchestration-agent/AgentOrchestration",
    "SecureBananaLabs/bug-bounty",
    "coinbase/onchainkit#2644",
}


def _load_completions() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not COMPLETIONS.exists():
        return out
    for p in sorted(COMPLETIONS.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        eid = str(data.get("external_id") or "")
        plan = data.get("plan") or {}
        pr = data.get("pr_url") or KNOWN_PR_MAP.get(eid)
        out[eid] = {
            "file": p.name,
            "feasible": plan.get("feasible"),
            "pr_url": pr,
            "reason": (plan.get("reason") or "")[:120],
        }
    return out


def main() -> int:
    if not DB.exists():
        print(f"Missing {DB}")
        return 1

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    by_status: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT external_id, status FROM opportunities WHERE channel='bounty' ORDER BY status, external_id"
    ):
        by_status.setdefault(row["status"], []).append(row["external_id"])
    conn.close()

    completions = _load_completions()
    open_prs = []
    if OPEN_PRS.exists():
        open_prs = json.loads(OPEN_PRS.read_text(encoding="utf-8"))

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Gaps: feasible completion, no PR
    completion_gaps = [
        eid
        for eid, c in completions.items()
        if c.get("feasible") and not c.get("pr_url") and eid not in SKIP
    ]

    payload = {
        "generated_at": ts,
        "status_counts": {k: len(v) for k, v in sorted(by_status.items())},
        "by_status": by_status,
        "completions": completions,
        "completion_gaps": completion_gaps,
        "claimed_not_built": CLAIMED_NOT_BUILT,
        "known_pr_map": KNOWN_PR_MAP,
        "open_pr_count": len(open_prs),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Bounty queue audit — {ts}",
        "",
        "SQLite + completion artifacts + verified PR map.",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Open (discovered only) | {len(by_status.get('open', []))} |",
        f"| Submitted (apply comment) | {len(by_status.get('submitted', []))} |",
        f"| PR opened (SQLite) | {len(by_status.get('pr_opened', []))} |",
        f"| In progress | {len(by_status.get('in_progress', []))} |",
        f"| Failed | {len(by_status.get('failed', []))} |",
        f"| **Open GitHub PRs (Hobie1Kenobi)** | **{len(open_prs)}** |",
        "",
        "## Tier 1 — Awaiting merge/payout (PR open)",
        "",
        "| Issue | PR | Payout rail |",
        "|-------|-----|-------------|",
    ]

    tier1 = [
        ("Daydreams #1 Fresh Markets", KNOWN_PR_MAP["daydreamsai/agent-bounties#1"], "Solana"),
        ("Daydreams #3 Slippage Sentinel", KNOWN_PR_MAP["daydreamsai/agent-bounties#3"], "Solana"),
        ("Daydreams #4 GasRoute Oracle", KNOWN_PR_MAP["daydreamsai/agent-bounties#4"], "Solana"),
        ("Daydreams #5 Approval Risk", KNOWN_PR_MAP["daydreamsai/agent-bounties#5"], "Solana"),
        ("Daydreams #6 Yield Pool Watcher", KNOWN_PR_MAP["daydreamsai/agent-bounties#6"], "Solana"),
        ("Claude Builders #1–#5", "PRs #2080–#2084", "Base USDC"),
        ("base/contracts docs #257–#259, #279, #286", "PRs #303–#307", "TBD"),
        ("OnchainKit #2646, #2652, #2655, #2657", "PRs #2659–#2662", "TBD"),
        ("Celo ecosystem listing #54", KNOWN_PR_MAP["celo-org/gitcoin#54"], "TBD"),
    ]
    for label, pr, rail in tier1:
        lines.append(f"| {label} | {pr} | {rail} |")

    lines += [
        "",
        "**Est. in-flight value:** ~$5,000 Solana (Daydreams) + ~$575 Base (Claude Builders) + doc bounties TBD.",
        "",
        "## Tier 2 — Claimed, not built yet",
        "",
        "| Issue | Agent | Next step |",
        "|-------|-------|-----------|",
    ]
    agents = {
        "#2": "Cross DEX Arbitrage Alert",
        "#7": "LP Impermanent Loss Estimator",
        "#8": "Perps Funding Pulse",
        "#9": "Lending Liquidation Sentinel",
        "#10": "Bridge Route Pinger",
    }
    for eid in CLAIMED_NOT_BUILT:
        num = eid.split("#")[1]
        lines.append(f"| [{eid}](https://github.com/{eid.replace('#', '/issues/')}) | {agents.get('#'+num, '?')} | Build agent + submission PR |")

    lines += [
        "",
        "Build order: **#10 → #8 → #9 → #7 → #2**.",
        "",
        "## Tier 3 — Completion gaps (plan exists, no PR)",
        "",
    ]
    if completion_gaps:
        for eid in completion_gaps:
            c = completions[eid]
            lines.append(f"- `{eid}` — feasible, artifact `{c['file']}`")
    else:
        lines.append("_None — all feasible completion plans have matching open PRs._")

    lines += [
        "",
        "## Tier 4 — Not feasible / skip",
        "",
        "| Item | Reason |",
        "|------|--------|",
        "| safe-global/safe-smart-account#988, #1021, #1027 | Completion marked not feasible (infra/zksync scope) |",
        "| coinbase/onchainkit#2644 | Duplicate of #2651; our PR closed |",
        "| Scottcjn/*, orchestration-agent/* | Blocked spam repos |",
        "| SecureBananaLabs/* | Deferred security lane |",
        "",
        "## Tier 5 — Applied/submitted, no completion yet",
        "",
        "High-signal items worth completing next (same EVM payout wallet):",
        "",
        "| Issue | SQLite status | Action |",
        "|-------|---------------|--------|",
        "| ethereum-optimism/Retro-Funding#12, #13 | submitted | Review scope; complete if doc-sized |",
        "| shapeshift/web (multiple) | submitted | Needs Dework + FOX payout setup |",
        "| daydreamsai/lucid-agents#179 | open | Apply + build counterparty-risk API |",
        "| claude-builders-bounty #1,#3,#4 | open in scan | Already have PRs — ignore duplicate apply |",
        "",
        "## Chain / wallet coverage",
        "",
        "| Rail | Address | Bounty sources |",
        "|------|---------|----------------|",
        "| Base / EVM | `0x408f39B19266022FeC03076091e59D1f4f163658` | Claude Builders, OnchainKit, base/contracts, Optimism, Celo |",
        "| Solana | `Bq1sMShfZw3oNVoNMjX78zSPcoaCan9r1NVKXctpG3nN` | Daydreams agent-bounties |",
        "",
        "No new wallet needed for Celo/Optimism — same EVM address receives on all EVM chains.",
        "",
        "## Recommended actions (priority order)",
        "",
        "1. **Monitor** Tier 1 PRs; re-run `npm run earning:worker:capture-comments` weekly.",
        "2. **Build** Daydreams #10 Bridge Route Pinger (fastest new $1k submission).",
        "3. **Apply** lucid-agents#179 if competition stays low.",
        "4. **Do not** re-apply Claude Builders or spam repos.",
        "5. Optional: wire `SOLANA_BOUNTY_WALLET` into earning worker apply drafts for Daydreams repos.",
        "",
        f"Machine-readable: `{OUT_JSON.name}`",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
