#!/usr/bin/env python3
"""Summarize local T54 / external commerce artifact line counts (optional ops helper)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "packages" / "agents" / "external_commerce_data"


def main() -> int:
    out: dict[str, object] = {"root": str(ROOT)}
    if not DATA.exists():
        print(json.dumps({**out, "note": "no external_commerce_data dir"}, indent=2))
        return 0
    files = sorted(DATA.glob("*.jsonl")) + sorted(DATA.glob("*.json"))
    rows = []
    for p in files:
        if p.suffix == ".jsonl":
            n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
            rows.append({"file": p.name, "lines": n})
        else:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                rows.append({"file": p.name, "keys": list(data.keys()) if isinstance(data, dict) else "array"})
            except Exception as e:
                rows.append({"file": p.name, "error": str(e)})
    out["artifacts"] = rows
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
