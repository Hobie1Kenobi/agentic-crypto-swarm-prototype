#!/usr/bin/env python3
"""
Write external_commerce_data/providers.discovery-snapshot.json — full merged registry
(config + optional x402scout slim catalog) without replacing the small canonical
external_commerce_data/providers.json.

Re-run after catalog or config changes for reproducible discovery diffs.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from external_commerce import Discovery, ProviderRegistry
from external_commerce.schemas import ExternalProvider


def _provider_to_dict(p: ExternalProvider) -> dict:
    return {
        "provider_id": p.provider_id,
        "provider_name": p.provider_name,
        "source_type": p.source_type,
        "discovery_source": p.discovery_source,
        "protocol_type": p.protocol_type,
        "network": p.network,
        "facilitator_url": p.facilitator_url,
        "resource_url": p.resource_url,
        "supported_assets": p.supported_assets,
        "pricing_model": p.pricing_model,
        "categories": p.categories,
        "trust_score": p.trust_score,
        "health_status": p.health_status,
        "last_seen_at": p.last_seen_at,
        "metadata": p.metadata,
    }


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or None
    except Exception:
        return None


def _apply_public_api_host(host: str) -> None:
    h = host.rstrip("/")
    os.environ.setdefault("X402_SELLER_NETWORK", "eip155:8453")
    os.environ["X402_SELLER_PUBLIC_URL"] = f"{h}/x402/v1/query"
    os.environ["T54_SELLER_PUBLIC_BASE_URL"] = f"{h}/t54"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--public-api-host",
        default="https://api.agentic-swarm-marketplace.com",
        help="Stable HTTPS origin for swarm seller + T54 rows in the snapshot (no trailing slash).",
    )
    ap.add_argument(
        "--no-scout-catalog",
        action="store_true",
        help="Omit x402scout slim catalog (config-only snapshot).",
    )
    ap.add_argument(
        "--remote-discovery",
        action="store_true",
        help="Include live remote discovery URLs (non-reproducible; default off).",
    )
    ap.add_argument(
        "--load-dotenv",
        action="store_true",
        help="Load repo root .env after CLI defaults (override=False).",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=root / "external_commerce_data" / "providers.discovery-snapshot.json",
        help="Output path.",
    )
    args = ap.parse_args()

    if args.load_dotenv:
        from dotenv import load_dotenv

        load_dotenv(root / ".env", override=False)

    _apply_public_api_host(args.public_api_host)
    if not args.remote_discovery:
        os.environ.pop("X402_DISCOVERY_ENABLED", None)
        os.environ["X402_DISCOVERY_ENABLED"] = "0"
    if args.no_scout_catalog:
        os.environ["X402_SCOUT_CATALOG_ENABLED"] = "0"
    else:
        os.environ["X402_SCOUT_CATALOG_ENABLED"] = "1"

    empty_registry_path = root / "external_commerce_data" / "__export_empty_registry__.json"
    registry = ProviderRegistry(registry_path=empty_registry_path)
    discovery = Discovery(registry=registry)
    providers = discovery.discover_all(
        include_remote=args.remote_discovery,
        include_scout_catalog=not args.no_scout_catalog,
    )

    out_path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "_export": {
            "generated_at": now,
            "git_commit": _git_head(),
            "public_api_host": args.public_api_host,
            "x402_scout_catalog_enabled": not args.no_scout_catalog,
            "x402_discovery_remote_enabled": args.remote_discovery,
            "note": "Not loaded at runtime; canonical registry remains external_commerce_data/providers.json",
        },
        "providers": [_provider_to_dict(p) for p in providers],
        "count": len(providers),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(providers)} providers to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
