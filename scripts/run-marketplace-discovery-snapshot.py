#!/usr/bin/env python3
"""
Read-only: fetch public x402 discovery indexes (CDP, PayAI) and write snapshot JSON.
Does not buy or invoke paid endpoints. Safe alongside long-running sellers.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[1]
OUT = root / "external_commerce_data" / "x402-discovery-snapshot.json"
PRIORITY = root / "external_commerce_data" / "marketplace_priority.json"

SOURCES = [
    {
        "id": "coinbase_cdp",
        "label": "Coinbase CDP x402 discovery",
        "url": "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources",
    },
    {
        "id": "payai",
        "label": "PayAI facilitator discovery",
        "url": "https://facilitator.payai.network/discovery/resources",
    },
]


def _fetch(url: str, timeout: float = 30) -> tuple[int, dict]:
    try:
        r = requests.get(url, timeout=timeout)
        ct = (r.headers.get("content-type") or "").lower()
        if r.status_code != 200 or "json" not in ct:
            return r.status_code, {"error": r.text[:500] if r.text else "non-json"}
        data = r.json()
        return r.status_code, data if isinstance(data, dict) else {"raw": str(data)[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for src in SOURCES:
        status, body = _fetch(src["url"])
        pag = body.get("pagination") if isinstance(body, dict) else {}
        items = body.get("items") if isinstance(body, dict) else None
        rows.append({
            "id": src["id"],
            "label": src["label"],
            "url": src["url"],
            "http_status": status,
            "pagination_total": pag.get("total") if isinstance(pag, dict) else None,
            "pagination_limit": pag.get("limit") if isinstance(pag, dict) else None,
            "first_page_items": len(items) if isinstance(items, list) else None,
            "error": body.get("error") if isinstance(body, dict) and "error" in body else None,
        })

    priority = {}
    if PRIORITY.exists():
        try:
            priority = json.loads(PRIORITY.read_text(encoding="utf-8"))
        except Exception:
            priority = {}

    payload = {
        "updated_at": ts,
        "schema_note": "Live GET-only snapshot; re-run: npm run commerce:snapshot",
        "recommended_order_ref": "external_commerce_data/marketplace_priority.json",
        "sources": rows,
        "sell_side_priority_summary": [
            p.get("id") for p in (priority.get("sell_side_priority") or []) if isinstance(p, dict)
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    for r in rows:
        print(
            f"  {r['id']}: status={r['http_status']} total={r.get('pagination_total')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
