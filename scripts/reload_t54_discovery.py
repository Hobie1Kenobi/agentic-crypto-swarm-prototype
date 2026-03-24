#!/usr/bin/env python3
"""
Reload x402 discovery from config (reads .env for T54_SELLER_PUBLIC_BASE_URL / URL overrides).

Run after changing T54 public URL or providers.json. No long-lived process — prints resolved T54 rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv

load_dotenv(root / ".env", override=True)
if (root / ".env.local").exists():
    load_dotenv(root / ".env.local", override=True)

from external_commerce.discovery import Discovery


def main() -> int:
    d = Discovery()
    providers = d.discover_from_config()
    t54 = []
    for p in providers:
        pid = p.provider_id or ""
        meta = p.metadata or {}
        if not (pid.startswith("t54-") or meta.get("t54_path")):
            continue
        t54.append(
            {
                "provider_id": pid,
                "resource_url": p.resource_url or "",
                "network": p.network,
                "sku_path": meta.get("t54_path"),
            }
        )
    print(json.dumps({"t54_providers": t54, "count": len(t54)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
