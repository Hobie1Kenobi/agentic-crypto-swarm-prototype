#!/usr/bin/env python3
"""Generate docs/proof/proof.json from on-chain payments to ASM payTo addresses."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marketplace.proof_snapshot import (  # noqa: E402
    build_snapshot,
    default_paths,
    load_json,
    write_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="", help="Output path (default: docs/proof/proof.json)")
    parser.add_argument("--offline", action="store_true", help="Reuse local snapshots only; no network.")
    args = parser.parse_args()

    paths = default_paths(ROOT)
    output = Path(args.output) if args.output else paths["output"]
    prior = load_json(paths["prior"]) if paths["prior"].exists() else None
    settlements = load_json(paths["settlements"]) if paths["settlements"].exists() else None
    snapshot = build_snapshot(
        repo_root=ROOT,
        live=not args.offline,
        prior=prior,
        settlements=settlements,
        include_health=not args.offline,
        include_preflight=not args.offline,
    )
    write_snapshot(snapshot, output)
    summary = snapshot.get("summary") or {}
    ext = summary.get("external") or {}
    house = summary.get("house") or {}
    print(f"Wrote {output}")
    print(
        "external_payments={0} unique_external_payers={1} house_payments={2} total={3}".format(
            ext.get("payments"),
            ext.get("unique_payers"),
            house.get("payments"),
            summary.get("total_payments"),
        )
    )
    failed = (snapshot.get("coverage") or {}).get("sources_failed") or []
    if failed:
        print("sources_failed:")
        for item in failed:
            if isinstance(item, dict):
                print(f"  {item.get('source')}: {item.get('error')}")
            else:
                print(f"  {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
