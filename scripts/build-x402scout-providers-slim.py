#!/usr/bin/env python3
"""
Build external_commerce_data/x402scout-providers-slim.json from x402scout-catalog-full.json.

Filters to HTTPS API-like URLs, agent_callable, trust/price bounds, then sorts by trust.
Does not touch running seller/soak processes — run offline or in CI.

Usage:
  python scripts/build-x402scout-providers-slim.py
  python scripts/build-x402scout-providers-slim.py --min-trust 85 --max-providers 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from external_commerce.x402scout_catalog import (  # noqa: E402
    default_slim_path,
    scout_service_to_provider_dict,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--catalog",
        type=Path,
        default=root / "external_commerce_data" / "x402scout-catalog-full.json",
        help="Path to x402scout-catalog-full.json",
    )
    p.add_argument("--min-trust", type=float, default=80.0)
    p.add_argument("--max-price-usd", type=float, default=0.25)
    p.add_argument("--max-providers", type=int, default=300)
    p.add_argument(
        "--out",
        type=Path,
        default=default_slim_path(),
        help="Output slim JSON path",
    )
    args = p.parse_args()

    if not args.catalog.exists():
        print(f"Missing catalog: {args.catalog}", file=sys.stderr)
        print("Run: npm run catalog:x402scout", file=sys.stderr)
        return 1

    data = json.loads(args.catalog.read_text(encoding="utf-8"))
    services = data.get("services") if isinstance(data, dict) else []
    if not isinstance(services, list):
        print("Invalid catalog shape", file=sys.stderr)
        return 1

    candidates: list[dict] = []
    for svc in services:
        if not isinstance(svc, dict):
            continue
        ts = float(svc.get("trust_score") or 0)
        if ts < args.min_trust:
            continue
        price = float(svc.get("price_usd") or 0)
        if price > args.max_price_usd:
            continue
        prov = scout_service_to_provider_dict(svc)
        if prov:
            candidates.append(prov)

    candidates.sort(key=lambda x: -float(x.get("trust_score") or 0))
    out_list = candidates[: args.max_providers]

    payload = {
        "schema_version": 1,
        "source_catalog": str(args.catalog.name),
        "filters": {
            "min_trust": args.min_trust,
            "max_price_usd": args.max_price_usd,
            "max_providers": args.max_providers,
            "https_agent_callable_only": True,
        },
        "count": len(out_list),
        "providers": out_list,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(out_list)} providers to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
