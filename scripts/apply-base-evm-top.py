#!/usr/bin/env python3
"""Apply to a curated list of Base/EVM bounties from the latest scan."""
from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env", override=False)
if (_ROOT / ".env.local").exists():
    load_dotenv(_ROOT / ".env.local", override=True)

from earning_worker import config
from earning_worker.bounty_apply import apply_bounty
from earning_worker.handlers.bounty import discover_bounties
from earning_worker.store import bounty_already_applied, init_db, mark_opportunity, record_action, upsert_opportunity

TARGETS = [
    "coinbase/onchainkit#2644",
    "ethereum-optimism/Retro-Funding#12",
    "SecureBananaLabs/bug-bounty#30",
]


def main() -> int:
    init_db()
    if not config.payout_address():
        print("ERROR: no payout wallet configured", file=sys.stderr)
        return 1

    by_id = {o.external_id: o for o in discover_bounties()}
    sleep_sec = config.bounty_apply_sleep_sec()
    ok = 0
    for ext in TARGETS:
        opp = by_id.get(ext)
        if not opp:
            print(f"SKIP not found in discovery: {ext}")
            continue
        if bounty_already_applied(opp.source_id, opp.external_id):
            print(f"SKIP already applied: {ext}")
            continue
        oid = upsert_opportunity(
            channel=opp.channel,
            source_id=opp.source_id,
            external_id=opp.external_id,
            title=opp.title,
            url=opp.url,
            reward_hint=opp.reward_hint,
            metadata=opp.metadata,
            status="open",
        )
        result = apply_bounty(opp, opportunity_id=oid, dry_run=False)
        print(f"{result.status:10} {ext} — {result.detail[:120]}")
        if result.status == "submitted":
            mark_opportunity(oid, "submitted")
            ok += 1
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        record_action(
            opportunity_id=oid,
            channel="bounty",
            action=result.action,
            status=result.status,
            detail=result.detail,
        )
    print(f"Applied {ok}/{len(TARGETS)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
