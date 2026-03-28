#!/usr/bin/env python3
"""
Run one external x402 paid invocation (test flow).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages" / "agents"))

from dotenv import load_dotenv
load_dotenv(root / ".env", override=True)

from external_commerce import (
    Discovery,
    X402Buyer,
    InvocationRecords,
    RelationshipMemory,
    RoutingPolicy,
)


def main() -> int:
    os.environ.setdefault("X402_ENABLED", "1")
    os.environ.setdefault("X402_DRY_RUN", "1")
    discovery = Discovery()
    providers = discovery.discover_from_config()
    if not providers:
        print("No providers discovered")
        return 1
    provider = providers[0]
    records = InvocationRecords()
    relationships = RelationshipMemory()
    buyer = X402Buyer(dry_run=os.getenv("X402_DRY_RUN", "1").strip().lower() in ("1", "true"))
    start = time.time()
    status, data, err = buyer.invoke(provider.resource_url, method="GET", params={"q": "test"})
    elapsed_ms = (time.time() - start) * 1000
    inv = records.create_record(
        provider_id=provider.provider_id,
        resource_id=provider.resource_url,
        adapter_type="direct_x402",
        task_id=None,
        request_summary="q=test",
        price_requested=None,
        price_paid=None,
        network=provider.network,
        facilitator_used=provider.facilitator_url,
        payment_status="completed" if status == 200 else "failed",
        response_status=status,
        latency_ms=elapsed_ms,
        result_summary=json.dumps(data)[:500] if data else "",
        error_type=err,
    )
    records.append(inv)
    if status == 200:
        relationships.record_success(provider.provider_id, elapsed_ms)
    else:
        relationships.record_failure(provider.provider_id, err)
    print(f"Status: {status} | Latency: {elapsed_ms:.0f}ms | Error: {err}")
    print(f"Result: {json.dumps(data, indent=2)[:500]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
