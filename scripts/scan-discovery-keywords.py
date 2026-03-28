#!/usr/bin/env python3
"""
Paginate CDP + PayAI x402 discovery catalogs, match airdrop-adjacent keywords, write JSONL + summary.
Read-only GET; does not buy or invoke paid endpoints. Safe alongside long-running sellers.

Outputs:
  external_commerce_data/discovery-keyword-hits.jsonl
  external_commerce_data/discovery-keyword-scan-summary.json
  docs/discovery-keyword-scan.json  (mirror for GitHub Pages)
  docs/discovery-keyword-scan.md    (human-readable; regenerate with npm run discovery:keywords)
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
    match_keywords,
)

DEFAULT_CONFIG = root / "packages" / "agents" / "config" / "discovery_keyword_scan.json"
OUT_JSONL = root / "external_commerce_data" / "discovery-keyword-hits.jsonl"
OUT_SUMMARY_DATA = root / "external_commerce_data" / "discovery-keyword-scan-summary.json"
DOCS_JSON = root / "docs" / "discovery-keyword-scan.json"
DOCS_MD = root / "docs" / "discovery-keyword-scan.md"


def _load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    try:
        return float(v)
    except ValueError:
        return default


def _snippet(blob: str, max_len: int = 220) -> str:
    s = " ".join(blob.split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _md_escape_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Keyword-scan x402 discovery catalogs (CDP + PayAI).")
    ap.add_argument(
        "--config",
        type=Path,
        default=Path(os.environ.get("DISCOVERY_KEYWORD_CONFIG", str(DEFAULT_CONFIG))),
        help="Path to discovery_keyword_scan.json",
    )
    ap.add_argument(
        "--max-items-per-source",
        type=int,
        default=None,
        help="Cap items scanned per source (default: config or DISCOVERY_SCAN_MAX_ITEMS_PER_SOURCE)",
    )
    ap.add_argument("--page-size", type=int, default=None)
    ap.add_argument("--sleep-seconds", type=float, default=None)
    ap.add_argument("--timeout-seconds", type=float, default=None)
    ap.add_argument(
        "--append-jsonl",
        action="store_true",
        help="Append to discovery-keyword-hits.jsonl instead of overwriting.",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; print counts to stdout.",
    )
    args = ap.parse_args()

    cfg = _load_config(args.config)
    defaults = cfg.get("defaults") or {}
    max_items = args.max_items_per_source
    if max_items is None:
        max_items = _env_int("DISCOVERY_SCAN_MAX_ITEMS_PER_SOURCE", int(defaults.get("max_items_per_source", 600)))
    page_size = args.page_size
    if page_size is None:
        page_size = _env_int("DISCOVERY_SCAN_PAGE_SIZE", int(defaults.get("page_size", 100)))
    sleep_s = args.sleep_seconds
    if sleep_s is None:
        sleep_s = _env_float("DISCOVERY_SCAN_SLEEP_SECONDS", float(defaults.get("sleep_seconds", 0.2)))
    timeout_s = args.timeout_seconds
    if timeout_s is None:
        timeout_s = _env_float("DISCOVERY_SCAN_TIMEOUT_SECONDS", float(defaults.get("timeout_seconds", 35)))

    keywords = list(cfg.get("default_keywords") or [])
    sources = [s for s in (cfg.get("sources") or []) if isinstance(s, dict) and s.get("url")]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    hits_by_resource: dict[str, dict] = {}
    source_stats: list[dict] = []

    for src in sources:
        sid = str(src.get("id", "unknown"))
        url = str(src["url"])
        label = str(src.get("label", sid))
        scanned = 0
        hits_count = 0
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
            blob = item_search_blob(item)
            matched = match_keywords(blob, keywords)
            if not matched:
                continue
            hits_count += 1
            res = str(item.get("resource") or "").strip()
            if not res:
                res = f"__missing_resource__:{sid}:{scanned}"
            rec = {
                "recorded_at": ts,
                "resource": res,
                "source_id": sid,
                "source_label": label,
                "matched_keywords": sorted(set(matched)),
                "snippet": _snippet(blob),
                "pagination": {
                    "offset": page_meta.get("offset"),
                    "total_reported": page_meta.get("total_reported"),
                },
            }
            if res in hits_by_resource:
                prev = hits_by_resource[res]
                merged = sorted(set(prev["matched_keywords"]) | set(rec["matched_keywords"]))
                prev["matched_keywords"] = merged
                prev["sources_seen"] = sorted(set(prev.get("sources_seen", [prev["source_id"]])) | {sid})
            else:
                rec["sources_seen"] = [sid]
                hits_by_resource[res] = rec

        source_stats.append(
            {
                "id": sid,
                "label": label,
                "url": url,
                "items_scanned": scanned,
                "hit_rows": hits_count,
                "total_reported_first_page": None,
            }
        )

    hits_list = list(hits_by_resource.values())
    hits_list.sort(key=lambda h: (-len(h["matched_keywords"]), h["resource"]))

    try:
        cfg_rel = args.config.resolve().relative_to(root)
    except ValueError:
        cfg_rel = args.config.resolve()
    summary = {
        "updated_at": ts,
        "schema_note": "Weak signal: substring match on discovery listing JSON, not proof of an airdrop. Combine with scripts/run-airdrop-scout.py for LLM scoring.",
        "config_path": cfg_rel.as_posix(),
        "keywords_used": keywords,
        "limits": {
            "max_items_per_source": max_items,
            "page_size": page_size,
            "sleep_seconds": sleep_s,
            "timeout_seconds": timeout_s,
        },
        "sources": source_stats,
        "aggregate": {
            "unique_resources_with_hits": len(hits_list),
            "total_hit_events_before_dedupe": sum(s["hit_rows"] for s in source_stats),
        },
        "top_hits": [
            {
                "resource": h["resource"],
                "matched_keywords": h["matched_keywords"],
                "sources_seen": h.get("sources_seen", [h["source_id"]]),
                "snippet": h.get("snippet", ""),
            }
            for h in hits_list[:120]
        ],
    }

    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append_jsonl else "w"
    with OUT_JSONL.open(mode, encoding="utf-8") as f:
        for h in hits_list:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    OUT_SUMMARY_DATA.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# x402 discovery — keyword scan (airdrop-adjacent)",
        "",
        f"**Updated:** `{ts}` (UTC)  ",
        "**Disclaimer:** These are **weak signals** from public x402 discovery listings (Coinbase CDP + PayAI). A keyword match is **not** confirmation of a legitimate airdrop or claim.",
        "",
        "## How to regenerate",
        "",
        "```bash",
        "npm run discovery:keywords",
        "# or",
        "python scripts/scan-discovery-keywords.py",
        "```",
        "",
        "Optional env: `DISCOVERY_KEYWORD_CONFIG`, `DISCOVERY_SCAN_MAX_ITEMS_PER_SOURCE`, `DISCOVERY_SCAN_PAGE_SIZE`, `DISCOVERY_SCAN_SLEEP_SECONDS`, `DISCOVERY_SCAN_TIMEOUT_SECONDS`.",
        "",
        "## Summary",
        "",
        f"- **Unique resources with a hit:** {summary['aggregate']['unique_resources_with_hits']}",
        f"- **Keywords:** {len(keywords)} (`{', '.join(keywords[:8])}` …)",
        "",
        "### Per source",
        "",
        "| Source | Items scanned | Hit rows (pre-dedupe) |",
        "|--------|---------------|------------------------|",
    ]
    for s in source_stats:
        md_lines.append(
            f"| {_md_escape_cell(s['label'])} | {s['items_scanned']} | {s['hit_rows']} |"
        )
    md_lines.extend(
        [
            "",
            "## Top hits (deduped by `resource`)",
            "",
            "| Resource | Keywords | Sources |",
            "|----------|----------|---------|",
        ]
    )
    for h in hits_list[:80]:
        kw = ", ".join(h["matched_keywords"][:12])
        if len(h["matched_keywords"]) > 12:
            kw += " …"
        srcs = ", ".join(h.get("sources_seen", []))
        md_lines.append(
            f"| {_md_escape_cell(h['resource'])} | {_md_escape_cell(kw)} | {_md_escape_cell(srcs)} |"
        )
    md_lines.extend(
        [
            "",
            "## Machine-readable",
            "",
            "- Repo: `external_commerce_data/discovery-keyword-scan-summary.json`",
            "- Pages mirror: [`discovery-keyword-scan.json`](discovery-keyword-scan.json)",
            "",
            "## Pair with Airdrop Scout",
            "",
            "Use interesting `resource` URLs as `--context` for `scripts/run-airdrop-scout.py` for LLM Farm Score + rationale. See `documentation/discovery/AIRDROP_INTELLIGENCE_AGENT.md`.",
            "",
        ]
    )
    DOCS_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote {len(hits_list)} deduped hits, {OUT_JSONL.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
