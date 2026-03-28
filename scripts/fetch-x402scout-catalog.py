#!/usr/bin/env python3
"""
Download the free full x402scout discovery catalog and split services into chunks of 50.

The Render URL https://x402-discovery-api.onrender.com/discover?limit=N enforces N<=50 but
returns an HTTP 402 x402 payment challenge for the paid search flow — not paginated JSON.

The public full catalog (no payment) is:
  https://x402scout.com/.well-known/x402-discovery

This script saves the full JSON plus chunk_NNN.json files with 50 services each.

Usage:
  python scripts/fetch-x402scout-catalog.py
  python scripts/fetch-x402scout-catalog.py --chunk-size 50
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://x402scout.com/.well-known/x402-discovery"
CHUNK_DEFAULT = 50


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "external_commerce_data" / "x402scout-catalog-chunks"
    full_path = root / "external_commerce_data" / "x402scout-catalog-full.json"

    p = argparse.ArgumentParser(description="Fetch x402scout .well-known catalog and chunk services")
    p.add_argument("--url", default=DEFAULT_URL, help="Catalog URL")
    p.add_argument("--chunk-size", type=int, default=CHUNK_DEFAULT, help="Services per chunk file")
    p.add_argument("--no-chunks", action="store_true", help="Only write full JSON")
    args = p.parse_args()

    ctx = ssl.create_default_context()
    req = urllib.request.Request(args.url, headers={"User-Agent": "Swarm-Economy-fetch-x402scout-catalog/1.0"})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        raw = r.read().decode("utf-8")

    data = json.loads(raw)
    if not isinstance(data, dict) or "services" not in data:
        print("Unexpected catalog shape", file=sys.stderr)
        return 1

    services = data["services"]
    total = len(services)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote full catalog: {full_path} ({total} services, total_services={data.get('total_services')})")

    if args.no_chunks:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {k: v for k, v in data.items() if k != "services"}
    chunk_size = max(1, args.chunk_size)
    idx = 0
    offset = 0
    while offset < total:
        chunk = services[offset : offset + chunk_size]
        payload = {
            **meta,
            "chunk_index": idx,
            "chunk_offset": offset,
            "chunk_size": len(chunk),
            "total_services": total,
            "services": chunk,
        }
        out_file = out_dir / f"chunk_{idx:03d}.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  {out_file.name}: {len(chunk)} services (offset {offset})")
        offset += chunk_size
        idx += 1

    print(f"Done: {idx} chunk files in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
