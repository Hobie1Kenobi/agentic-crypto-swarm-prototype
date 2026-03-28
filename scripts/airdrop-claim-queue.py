#!/usr/bin/env python3
"""
Human-approved airdrop / distributor claim execution queue.

Flow: add (ClaimSpec JSON) → approve → execute
(requires AIRDROP_CLAIM_EXECUTION_ENABLED=1, routing allowlist, and AIRDROP_CLAIMANT_PRIVATE_KEY).

Run from repo root.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)


def main() -> int:
    from airdrop_claim import ClaimQueueStore, ClaimSpec, ClaimStatus
    from airdrop_claim.executor import execute_claim
    from airdrop_claim.routing import default_routing_path, load_routing

    ap = argparse.ArgumentParser(description="Airdrop claim queue (approval-gated execution)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="Queue a ClaimSpec JSON (file path or - for stdin)")
    p.add_argument("file", nargs="?", default="-", help="Path to JSON (default stdin)")
    p.add_argument("--meta", help="Optional JSON file merged into record meta")
    p.set_defaults(_fn="add")

    p = sub.add_parser("list", help="List claims")
    p.add_argument(
        "--status",
        choices=[x.value for x in ClaimStatus],
        default=None,
    )
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(_fn="list")

    p = sub.add_parser("show", help="Show one claim")
    p.add_argument("id")
    p.set_defaults(_fn="show")

    p = sub.add_parser("approve", help="Approve a pending claim")
    p.add_argument("id")
    p.add_argument("--by", default="", help="Approver label (default: USER)")
    p.set_defaults(_fn="approve")

    p = sub.add_parser("reject", help="Reject a pending claim")
    p.add_argument("id")
    p.add_argument("--reason", default="")
    p.set_defaults(_fn="reject")

    p = sub.add_parser("dry-run", help="Gas estimate only (no broadcast)")
    p.add_argument("id")
    p.set_defaults(_fn="dry_run")

    p = sub.add_parser("execute", help="Broadcast approved claim (requires --i-understand)")
    p.add_argument("id")
    p.add_argument(
        "--i-understand",
        action="store_true",
        help="Confirm you reviewed routing allowlist and calldata",
    )
    p.set_defaults(_fn="execute")

    p = sub.add_parser("routing", help="Show merged routing config path hint")
    p.set_defaults(_fn="routing")

    args = ap.parse_args()

    st = ClaimQueueStore()

    if args._fn == "add":
        pth = args.file
        raw = sys.stdin.read() if pth == "-" else Path(pth).read_text(encoding="utf-8")
        spec = ClaimSpec.model_validate_json(raw)
        meta = json.loads(Path(args.meta).read_text(encoding="utf-8")) if getattr(args, "meta", None) else {}
        cid = st.add_pending(spec, meta=meta)
        print(cid)
        return 0

    if args._fn == "list":
        status = ClaimStatus(args.status) if args.status else None
        rows = st.list_by_status(status, limit=args.limit)
        for r in rows:
            print(f"{r.id}\t{r.status.value}\t{r.spec.chain_id}\t{r.spec.to}\t{r.spec.label}")
        return 0

    if args._fn == "show":
        r = st.get(args.id)
        if not r:
            print("not found", file=sys.stderr)
            return 1
        print(r.model_dump_json(indent=2))
        return 0

    if args._fn == "approve":
        who = args.by or os.getenv("USER", "") or os.getenv("USERNAME", "operator")
        st.update_status(args.id, ClaimStatus.approved, approved_by=who)
        print("approved", args.id)
        return 0

    if args._fn == "reject":
        st.update_status(args.id, ClaimStatus.rejected, rejected_reason=args.reason or "rejected")
        print("rejected", args.id)
        return 0

    if args._fn == "dry_run":
        out = execute_claim(args.id, dry_run=True)
        print(json.dumps(out, indent=2))
        return 0

    if args._fn == "execute":
        if not args.i_understand:
            print("Refusing: pass --i-understand after reviewing routing + calldata.", file=sys.stderr)
            return 2
        out = execute_claim(args.id, dry_run=False)
        print(json.dumps(out, indent=2))
        return 0

    if args._fn == "routing":
        print("default:", default_routing_path())
        print(load_routing().model_dump_json(indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
