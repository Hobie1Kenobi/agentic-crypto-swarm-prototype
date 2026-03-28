#!/usr/bin/env python3
"""
Generate federation summary report.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys_path_inserted = False


def _ensure_path():
    global sys_path_inserted
    if not sys_path_inserted:
        import sys
        sys.path.insert(0, str(root / "packages" / "agents"))
        sys_path_inserted = True


def main() -> int:
    _ensure_path()
    data_dir = root / "external_commerce_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    providers = []
    relationships = {}
    invocations = []
    if (data_dir / "providers.json").exists():
        try:
            d = json.loads((data_dir / "providers.json").read_text(encoding="utf-8"))
            providers = d.get("providers", [])
        except Exception:
            pass
    if (data_dir / "provider_relationships.json").exists():
        try:
            d = json.loads((data_dir / "provider_relationships.json").read_text(encoding="utf-8"))
            relationships = d.get("relationships", {})
        except Exception:
            pass
    if (data_dir / "external-invocations.jsonl").exists():
        for line in (data_dir / "external-invocations.jsonl").read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    invocations.append(json.loads(line))
                except Exception:
                    pass
    summary = {
        "providers_discovered": len(providers),
        "providers_invoked": len({i["provider_id"] for i in invocations}),
        "successful_paid_calls": sum(1 for i in invocations if i.get("payment_status") == "completed"),
        "failed_calls": sum(1 for i in invocations if i.get("payment_status") != "completed"),
        "invocations": invocations[-10:],
        "relationships": relationships,
    }
    out = root / "external_commerce_data" / "federation-summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = root / "external_commerce_data" / "federation-report.md"
    lines = [
        "# x402 Federation Report",
        "",
        f"## Summary",
        "",
        f"- Providers discovered: {summary['providers_discovered']}",
        f"- Providers invoked: {summary['providers_invoked']}",
        f"- Successful paid calls: {summary['successful_paid_calls']}",
        f"- Failed calls: {summary['failed_calls']}",
        "",
        "## Note",
        "",
        "Live vs simulated: Check `payment_status` and `dry_run` in invocations.",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {out} and {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
