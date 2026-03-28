"""
Flatten x402 discovery resource rows for keyword matching (airdrop-adjacent signals).
"""
from __future__ import annotations

import json
import time
from typing import Any, Iterator

import requests


def item_search_blob(item: dict[str, Any]) -> str:
    """Serialize all likely text-bearing fields for substring search."""
    parts: list[str] = []
    for key in ("resource", "type", "method", "lastUpdated", "x402Version"):
        v = item.get(key)
        if v is not None:
            parts.append(str(v))
    for acc in item.get("accepts") or []:
        if isinstance(acc, dict):
            parts.append(json.dumps(acc, default=str))
    for key in ("metadata", "inputSchema", "outputSchema"):
        v = item.get(key)
        if v is not None:
            parts.append(json.dumps(v, default=str))
    return "\n".join(parts).lower()


def match_keywords(blob: str, keywords: list[str]) -> list[str]:
    """Return keywords that appear as substrings in blob (already lowercased)."""
    b = blob.lower()
    return [k for k in keywords if k.lower() in b]


def fetch_discovery_page(
    url: str,
    offset: int,
    limit: int,
    timeout: float,
) -> tuple[int, dict[str, Any] | None]:
    try:
        r = requests.get(url, params={"limit": limit, "offset": offset}, timeout=timeout)
        if r.status_code != 200:
            return r.status_code, None
        data = r.json()
        if not isinstance(data, dict):
            return 0, None
        return 200, data
    except Exception:
        return 0, None


def iter_discovery_items(
    url: str,
    label: str,
    source_id: str,
    *,
    max_items: int,
    page_size: int,
    sleep_seconds: float,
    timeout: float,
) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """
    Yields (item, page_meta) where page_meta has offset, total, pagination.
    Stops after max_items items or end of catalog.
    """
    offset = 0
    seen = 0
    total = None
    while seen < max_items:
        status, data = fetch_discovery_page(url, offset, page_size, timeout)
        if status != 200 or not data:
            break
        pag = data.get("pagination") or {}
        if total is None and isinstance(pag.get("total"), int):
            total = pag["total"]
        items = data.get("items")
        if not isinstance(items, list) or not items:
            break
        page_meta = {
            "source_id": source_id,
            "label": label,
            "offset": offset,
            "total_reported": total,
            "page_len": len(items),
        }
        for item in items:
            if not isinstance(item, dict):
                continue
            if seen >= max_items:
                return
            yield item, page_meta
            seen += 1
        if len(items) < page_size:
            break
        offset += page_size
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
