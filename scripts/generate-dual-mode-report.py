#!/usr/bin/env python3
"""
Generate dual_mode_run_report.(json|md) by merging:
- public_adapter_run_report.json
- communication_trace.json
- latest private marketplace report (celo/local) if present
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(p: Path) -> dict[str, Any] | None:
    try:
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _in_report(root: Path, name: str) -> Path:
    ar = root / "artifacts" / "reports" / name
    if ar.exists():
        return ar
    return root / name


def _comm_trace_json(root: Path) -> Path:
    p = root / "artifacts" / "communication" / "communication_trace.json"
    if p.exists():
        return p
    return root / "communication_trace.json"


def _pick_private_report(root: Path) -> tuple[str | None, dict[str, Any] | None]:
    celo = _in_report(root, "celo_sepolia_task_market_report.json")
    local = _in_report(root, "local_task_market_report.json")
    if celo.exists():
        return "celo_sepolia_task_market_report.json", _read_json(celo)
    if local.exists():
        return "local_task_market_report.json", _read_json(local)
    return None, None


def _tx_hashes_from_private(private_report: dict[str, Any] | None) -> list[str]:
    if not private_report:
        return []
    out: list[str] = []
    for e in private_report.get("tx_hashes", []) or []:
        h = e.get("tx_hash")
        if h:
            out.append(str(h))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root")
    ap.add_argument("--output", default="dual_mode_run_report", help="Basename for outputs")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_base = args.output
    rep = root / "artifacts" / "reports"
    rep.mkdir(parents=True, exist_ok=True)

    public = _read_json(_in_report(root, "public_adapter_run_report.json"))
    trace = _read_json(_comm_trace_json(root))
    private_name, private = _pick_private_report(root)

    merged: dict[str, Any] = {
        "ok": bool((public or {}).get("ok")) and (bool((private or {}).get("ok")) if private else True),
        "public_adapter_run_report": public,
        "communication_trace": trace,
        "private_market_report_file": private_name,
        "private_market_report": private,
        "correlation": {
            "external_request_id": ((public or {}).get("public_response") or {}).get("external_request_id")
            or (trace or {}).get("external_request_id"),
            "internal_task_id": ((public or {}).get("public_response") or {}).get("internal_task_id")
            or (trace or {}).get("internal_task_id")
            or (((private or {}).get("task") or {}).get("task_id") if private else None),
        },
        "tx_hashes": {
            "public": (((public or {}).get("public_response") or {}).get("tx_hashes") or []),
            "private": _tx_hashes_from_private(private),
        },
        "boundaries": {
            "public_boundary": ((public or {}).get("public_response") or {}).get("boundary") or (public or {}).get("boundary"),
            "trace_outcome_boundary": (trace or {}).get("outcome", {}).get("boundary") if trace else None,
        },
    }

    json_path = rep / f"{out_base}.json"
    md_path = rep / f"{out_base}.md"
    json_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Dual Mode Run Report")
    lines.append("")
    lines.append(f"- ok: `{merged['ok']}`")
    lines.append(f"- external_request_id: `{merged['correlation']['external_request_id']}`")
    lines.append(f"- internal_task_id: `{merged['correlation']['internal_task_id']}`")
    lines.append(f"- public_boundary: `{merged['boundaries']['public_boundary']}`")
    lines.append(f"- private_report: `{merged['private_market_report_file'] or '—'}`")
    lines.append("")
    lines.append("## Tx hashes")
    lines.append("")
    pub = merged["tx_hashes"]["public"] or []
    priv = merged["tx_hashes"]["private"] or []
    lines.append(f"- public: `{', '.join(pub) if pub else '—'}`")
    lines.append(f"- private: `{', '.join(priv) if priv else '—'}`")
    lines.append("")
    lines.append("## Real vs simulated")
    lines.append("")
    lines.append("- See `communication_trace.md` for step-by-step boundary markers.")
    lines.append("- See `documentation/operations/PUBLIC-ADAPTER.md` for exact meaning of boundaries.")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()

