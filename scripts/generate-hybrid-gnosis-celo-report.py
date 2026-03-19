from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt_wei(wei: int | None, symbol: str) -> str:
    if wei is None:
        return "n/a"
    return f"{wei} wei ({wei / 1e18:.6f} {symbol})"


def main() -> None:
    root = _root()
    public = _read_json(root / "public_adapter_run_report.json") or {}
    trace = _read_json(root / "communication_trace.json") or {}
    private = _read_json(root / "celo_sepolia_task_market_report.json") or _read_json(root / "local_task_market_report.json") or {}
    preflight = _read_json(root / "olas_preflight_report.json")
    live_attempt = _read_json(root / "olas_live_attempt_report.json")

    symbol = (private.get("native_symbol") or "CELO").upper()
    private_ok = bool(private.get("ok"))
    task = private.get("task") or {}
    settlement = task.get("settlement") or {}
    by_cat = settlement.get("by_category") or {}
    by_addr = settlement.get("by_address") or {}

    olas = public.get("olas") or {}
    external_boundary = str(olas.get("boundary") or public.get("boundary") or "mocked_external_replay")
    external_real = external_boundary == "real_external_integration" and bool(olas.get("tx_hash"))
    external_error = olas.get("error")

    external_mode_desc = "real_external_integration" if external_real else "mocked_external_replay"
    if not external_real and external_error:
        external_mode_desc = "mocked_external_replay (live attempt blocked)"

    internal_boundary = "contract_level_execution (real)" if private_ok else "none"

    remaining_blocker: dict[str, Any] | None = None
    if live_attempt and not bool(live_attempt.get("ok")):
        remaining_blocker = live_attempt.get("blocker") or {"detail": "Olas live attempt failed."}
    elif preflight and not bool(preflight.get("ok")):
        remaining_blocker = {"type": "preflight_failed", "missing": preflight.get("missing")}

    external_request_id = public.get("normalized_task", {}).get("external_request_id") or olas.get("request_id")
    external_tx_hash = olas.get("tx_hash")
    internal_task_id = task.get("task_id") or public.get("public_response", {}).get("internal_task_id")

    internal_tx_hashes = []
    for t in (private.get("tx_hashes") or []):
        if isinstance(t, dict) and t.get("tx_hash"):
            internal_tx_hashes.append({"name": t.get("name"), "role": t.get("role"), "tx_hash": t.get("tx_hash")})

    report: dict[str, Any] = {
        "ok": private_ok,
        "boundaries": {
            "external": external_boundary,
            "external_mode": external_mode_desc,
            "internal": internal_boundary,
        },
        "chains": {
            "private": (public.get("chains") or {}).get("private") or {},
            "public_olas": (public.get("chains") or {}).get("public_olas") or {},
        },
        "correlation": {
            "external_request_id": external_request_id,
            "external_tx_hash": external_tx_hash,
            "internal_task_id": internal_task_id,
            "internal_tx_hashes": internal_tx_hashes,
        },
        "settlement": {
            "by_category": by_cat,
            "by_address": by_addr,
            "settlement_matches_expected": task.get("settlement_matches_expected"),
        },
        "external_evidence": {
            "mech_tool": olas.get("tool"),
            "olas_chain_config": olas.get("chain_config") or public.get("normalized_task", {}).get("external_chain"),
            "error": external_error,
        },
        "remaining_blocker": remaining_blocker,
        "evidence_pointers": {
            "public_adapter_run_report_json": "public_adapter_run_report.json",
            "communication_trace_json": "communication_trace.json",
            "private_task_market_report_json": "celo_sepolia_task_market_report.json",
        },
    }

    out_json = root / "hybrid_gnosis_celo_report.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Markdown.
    md: list[str] = []
    md.append("# Hybrid Gnosis (Olas adapter) -> Celo (private settlement)")
    md.append("")
    md.append("## Boundaries (explicit, no silent fakes)")
    md.append(f"- real external interaction: `{external_real}` (boundary: `{external_boundary}`)")
    md.append(f"- real private onchain settlement: `{private_ok}`")
    md.append("")
    md.append("## Correlation IDs")
    md.append(f"- external_request_id: `{external_request_id}`")
    md.append(f"- external_tx_hash: `{external_tx_hash}`")
    md.append(f"- internal_task_id: `{internal_task_id}`")
    md.append("")
    md.append("## Settlement Accounting (economic categories)")
    if not by_cat:
        md.append("- (missing by_category breakdown)")
    else:
        for cat in ["protocol_fee", "finance_fee", "worker_payout", "requester_refund"]:
            info = by_cat.get(cat) or {}
            md.append(f"- {cat}: expected {_fmt_wei(info.get('expected_wei'), symbol)}; pending {_fmt_wei(info.get('actual_pending_wei'), symbol)}")
    md.append("")
    md.append("## Combined Entitlement by Address (roles overlap)")
    if not by_addr:
        md.append("- (none)")
    else:
        for addr, ent in by_addr.items():
            md.append(f"- `{addr}`: expected {_fmt_wei(ent.get('total_expected_wei'), symbol)}; pending {_fmt_wei(ent.get('total_actual_pending_wei'), symbol)}")
            for c in ent.get("categories") or []:
                md.append(f"- {c.get('category')}: expected {_fmt_wei(c.get('expected_wei'), symbol)}")
    md.append("")
    md.append("## Remaining Blocker (if full public integration not achieved)")
    if remaining_blocker:
        md.append("```json")
        md.append(json.dumps(remaining_blocker, indent=2))
        md.append("```")
    else:
        md.append("- (none)")
    md.append("")
    md.append("## Evidence Pointers")
    md.append("- communication trace: `communication_trace.md`")
    md.append("- public adapter run: `public_adapter_run_report.json`")
    md.append("- private settlement: `celo_sepolia_task_market_report.json`")

    out_md = root / "hybrid_gnosis_celo_report.md"
    md_content = "\n".join(md).rstrip() + "\n"
    out_md.write_text(md_content, encoding="utf-8")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")

    if external_real:
        live_md = root / "hybrid_live_gnosis_to_celo_report.md"
        live_lines = ["# Hybrid live: Gnosis external request -> Celo settlement", ""]
        live_lines.extend(md[2:])
        live_md.write_text("\n".join(live_lines).rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {live_md}")


if __name__ == "__main__":
    main()

