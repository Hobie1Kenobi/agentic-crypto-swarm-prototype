#!/usr/bin/env python3
"""
Run x402 discovery and write providers to external_commerce_data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv
load_dotenv(root / ".env", override=True)

from external_commerce import Discovery, ProviderRegistry


def _truthy(key: str) -> bool:
    return (os.getenv(key, "") or "").strip().lower() in {"1", "true", "yes"}


def main() -> int:
    print("Running x402 discovery...")
    scout_on = _truthy("X402_SCOUT_CATALOG_ENABLED")
    remote_on = _truthy("X402_DISCOVERY_ENABLED")
    registry = ProviderRegistry()
    discovery = Discovery(registry=registry)
    providers = discovery.discover_all(
        include_remote=remote_on,
        include_scout_catalog=scout_on,
    )
    registry.save()
    out_path = root / "external_commerce_data" / "discovery-results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "providers": [
            {
                "provider_id": p.provider_id,
                "provider_name": p.provider_name,
                "resource_url": p.resource_url,
                "network": p.network,
                "source_type": p.source_type,
                "discovery_source": p.discovery_source,
            }
            for p in providers
        ],
        "count": len(providers),
        "flags": {
            "X402_SCOUT_CATALOG_ENABLED": scout_on,
            "X402_DISCOVERY_ENABLED": remote_on,
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Discovered {len(providers)} providers (scout_catalog={scout_on}, remote={remote_on}). Written to {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
