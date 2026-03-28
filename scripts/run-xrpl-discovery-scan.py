#!/usr/bin/env python3
"""
XRPL-focused x402 discovery: paginate CDP + PayAI catalogs, filter XRPL/XRP rows, optional keywords.
Read-only GET. Does not spend XRP.

Outputs:
  external_commerce_data/xrpl-discovery-hits.jsonl
  external_commerce_data/xrpl-discovery-scan-summary.json
  docs/xrpl-discovery-scan.json
  docs/xrpl-discovery-scan.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if str(root / "packages" / "agents") not in sys.path:
    sys.path.insert(0, str(root / "packages" / "agents"))

from external_commerce.discovery_keyword_scan import (  # noqa: E402
    item_search_blob,
    iter_discovery_items,
)
from xrpl_discovery.xrpl_filter import is_xrpl_related_item, optional_keyword_hits  # noqa: E402

DEFAULT_CONFIG = root / "packages" / "agents" / "config" / "xrpl_discovery_scan.json"
OUT_JSONL = root / "external_commerce_data" / "xrpl-discovery-hits.jsonl"
OUT_SUMMARY = root / "external_commerce_data" / "xrpl-discovery-scan-summary.json"
DOCS_JSON = root / "docs" / "xrpl-discovery-scan.json"
DOCS_MD = root / "docs" / "xrpl-discovery-scan.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _snippet(blob: str, max_len: int = 220) -> str:
    s = " ".join(blob.split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _md_esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description="XRPL-filtered x402 discovery scan")
    ap.add_argument("--config", type=Path, default=Path(os.getenv("XRPL_DISCOVERY_CONFIG", str(DEFAULT_CONFIG))))
    ap.add_argument("--max-items-per-source", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = _load(args.config)
    defs = cfg.get("defaults") or {}
    max_items = args.max_items_per_source or int(defs.get("max_items_per_source", 600))
    page_size = int(defs.get("page_size", 100))
    sleep_s = float(defs.get("sleep_seconds", 0.2))
    timeout_s = float(defs.get("timeout_seconds", 35))
    opt_kw = list(cfg.get("optional_keywords") or [])
    sources = [s for s in (cfg.get("sources") or []) if isinstance(s, dict) and s.get("url")]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    hits_by_resource: dict[str, dict] = {}
    source_stats: list[dict] = []

    for src in sources:
        sid = str(src.get("id", "unknown"))
        url = str(src["url"])
        label = str(src.get("label", sid))
        scanned = 0
        xrpl_rows = 0
        for item, page_meta in iter_discovery_items(
            url,
            label,
            sid,
            max_items=max_items,
            page_size=page_size,
            sleep_seconds=sleep_s,
            timeout=timeout_s,
        ):
            scanned += 1
            if not is_xrpl_related_item(item):
                continue
            blob = item_search_blob(item)
            kw_hits = optional_keyword_hits(blob, opt_kw)
            if opt_kw and not kw_hits:
                continue
            xrpl_rows += 1
            res = str(item.get("resource") or "").strip() or f"__missing__:{sid}:{scanned}"
            rec = {
                "recorded_at": ts,
                "resource": res,
                "source_id": sid,
                "source_label": label,
                "xrpl_signal": True,
                "optional_keyword_hits": kw_hits,
                "snippet": _snippet(blob),
                "pagination": {"offset": page_meta.get("offset"), "total_reported": page_meta.get("total_reported")},
            }
            if res in hits_by_resource:
                prev = hits_by_resource[res]
                prev["optional_keyword_hits"] = sorted(
                    set(prev.get("optional_keyword_hits") or []) | set(kw_hits)
                )
                prev["sources_seen"] = sorted(set(prev.get("sources_seen", [prev["source_id"]])) | {sid})
            else:
                rec["sources_seen"] = [sid]
                hits_by_resource[res] = rec

        source_stats.append(
            {"id": sid, "label": label, "url": url, "items_scanned": scanned, "xrpl_filtered_rows": xrpl_rows}
        )

    hits_list = sorted(hits_by_resource.values(), key=lambda h: (h["resource"]))
    try:
        cfg_rel = args.config.resolve().relative_to(root)
    except ValueError:
        cfg_rel = args.config.resolve()
    summary = {
        "updated_at": ts,
        "schema_note": "Filtered x402 discovery for XRPL/XRP payment signals. Not an on-ledger airdrop registry.",
        "config_path": cfg_rel.as_posix(),
        "optional_keywords_applied": opt_kw,
        "limits": {"max_items_per_source": max_items, "page_size": page_size},
        "sources": source_stats,
        "aggregate": {
            "unique_resources": len(hits_list),
            "total_xrpl_rows_before_dedupe": sum(s["xrpl_filtered_rows"] for s in source_stats),
        },
        "hits": hits_list[:200],
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False)[:8000])
        return 0

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.write_text("\n".join(json.dumps(h, ensure_ascii=False) for h in hits_list) + ("\n" if hits_list else ""), encoding="utf-8")
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DOCS_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# XRPL x402 discovery scan",
        "",
        f"**Updated:** `{ts}` UTC",
        "",
        "Filtered public x402 listings (CDP + PayAI) for **XRPL / XRP** payment signals. Read-only.",
        "",
        "## Commands",
        "",
        "```bash",
        "npm run discovery:xrpl",
        "```",
        "",
        "## Summary",
        "",
        f"- Unique resources: **{len(hits_list)}**",
        "",
        "### Per source",
        "",
        "| Source | Items scanned | XRPL-filtered rows |",
        "|--------|---------------|---------------------|",
    ]
    for s in source_stats:
        md.append(f"| {_md_esc(s['label'])} | {s['items_scanned']} | {s['xrpl_filtered_rows']} |")
    md.extend(["", "## Sample resources", ""])
    for h in hits_list[:40]:
        md.append(f"- `{_md_esc(h['resource'])}`")
    md.extend(
        [
            "",
            "## Xaman",
            "",
            "This scan does **not** need your Xaman secret. Paying an x402 endpoint on XRPL from automation uses `XRPL_WALLET_SEED` (hot wallet) in `.env` — **not** Xaman’s signing flow. Use Xaman for manual review of URLs.",
            "",
        ]
    )
    DOCS_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {len(hits_list)} XRPL-related resources. See {DOCS_MD.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
