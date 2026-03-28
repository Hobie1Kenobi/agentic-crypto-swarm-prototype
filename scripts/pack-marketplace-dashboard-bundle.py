#!/usr/bin/env python3
"""
Build dist/x402-strategy-dashboard-bundle.zip for resale.

Includes:
  marketplace/bundles/x402-strategy-dashboard/** (README, LICENSE, static viewer)
  snapshot of external_commerce_data/x402scout-providers-slim.json -> static/data/catalog-slim.json

Usage:
  python scripts/pack-marketplace-dashboard-bundle.py
  python scripts/pack-marketplace-dashboard-bundle.py --slim path/to/slim.json
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_AGENTS = _REPO / "packages" / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from external_commerce.x402scout_catalog import default_slim_path  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Pack dashboard bundle ZIP")
    p.add_argument(
        "--slim",
        type=Path,
        default=None,
        help="Slim JSON (default: X402_SCOUT_SLIM_JSON or repo default)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output zip path (default: dist/x402-strategy-dashboard-bundle-<ts>.zip)",
    )
    p.add_argument(
        "--no-latest",
        action="store_true",
        help="Do not copy timestamped build to dist/x402-strategy-dashboard-bundle-latest.zip",
    )
    args = p.parse_args()

    bundle_root = _REPO / "marketplace" / "bundles" / "x402-strategy-dashboard"
    if not bundle_root.is_dir():
        print(f"Missing bundle dir: {bundle_root}", file=sys.stderr)
        return 1

    slim_src = args.slim or default_slim_path()
    if not slim_src.exists():
        print(f"Missing slim catalog: {slim_src}", file=sys.stderr)
        print("Run: npm run catalog:scout-slim", file=sys.stderr)
        return 1

    data_dir = bundle_root / "static" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(slim_src, data_dir / "catalog-slim.json")

    dist_dir = _REPO / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_zip = args.out or (dist_dir / f"x402-strategy-dashboard-bundle-{ts}.zip")

    def _walk(root: Path):
        for p in root.rglob("*"):
            if p.is_file():
                yield p

    with zipfile.ZipFile(
        out_zip, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for f in sorted(_walk(bundle_root), key=lambda x: str(x)):
            arc = f.relative_to(bundle_root)
            zf.write(f, arc.as_posix())

    print(f"Wrote {out_zip}")
    print(f"Catalog snapshot: {slim_src.name}")
    if not args.no_latest:
        latest = dist_dir / "x402-strategy-dashboard-bundle-latest.zip"
        shutil.copy2(out_zip, latest)
        print(f"Stable alias: {latest}")
        print("Set MARKETPLACE_BUNDLE_ZIP_PATH=dist/x402-strategy-dashboard-bundle-latest.zip (repo root)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
