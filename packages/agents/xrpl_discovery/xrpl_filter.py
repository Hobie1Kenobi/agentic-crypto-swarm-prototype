"""
Heuristic filter: x402 discovery item is XRPL / XRP payment related.
"""
from __future__ import annotations

import json
import re
from typing import Any

from external_commerce.discovery_keyword_scan import item_search_blob

_RE_CLASSIC = re.compile(r"\br[1-9A-HJ-NP-Za-km-z]{25,34}\b")


def is_xrpl_related_item(item: dict[str, Any]) -> bool:
    """True if listing appears to use XRPL or XRP as payment rail."""
    if not isinstance(item, dict):
        return False
    blob = item_search_blob(item)
    res = str(item.get("resource") or "").lower()

    if "xrpl" in blob or "xrp ledger" in blob:
        return True
    if "xrpl" in res or "/xrpl/" in res:
        return True
    if "t54" in blob and ("xrpl" in blob or "xrp" in blob or "x402" in blob):
        return True

    for acc in item.get("accepts") or []:
        if not isinstance(acc, dict):
            continue
        net = str(acc.get("network") or "").lower()
        if "xrpl" in net or net.startswith("xrpl:"):
            return True
        extra = acc.get("extra") or {}
        if isinstance(extra, dict):
            ex = json.dumps(extra, default=str).lower()
            if "xrpl" in ex or "xrp" in ex:
                return True
        asset = str(acc.get("asset") or "").lower()
        desc = str(acc.get("description") or "").lower()
        if asset == "xrp" or " xrp" in f" {asset} ":
            return True
        if "xrp" in desc and ("pay" in desc or "402" in desc or "facilitator" in desc):
            return True

    if _RE_CLASSIC.search(blob):
        if "xrp" in blob or "xrpl" in blob or "ripple" in blob:
            return True

    if re.search(r"\bxrp\b", blob) and ("402" in blob or "facilitator" in blob or "payment" in blob):
        return True

    return False


def optional_keyword_hits(blob: str, keywords: list[str]) -> list[str]:
    if not keywords:
        return []
    b = blob.lower()
    return [k for k in keywords if k.lower() in b]
