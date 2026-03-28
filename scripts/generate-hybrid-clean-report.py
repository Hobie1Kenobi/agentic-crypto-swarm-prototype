from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _reports_dir(root: Path) -> Path:
    d = root / "artifacts" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def _fmt_wei(wei: int | None, symbol: str) -> str:
    if wei is None:
        return "n/a"
    return f"{wei} wei ({wei / 1e18:.6f} {symbol})"


def _role_for_addr(private_report: dict[str, Any] | None, addr: str) -> str:
    if not private_report:
        return "UNKNOWN"
    roles = private_report.get("roles") or {}
    for _, v in roles.items():
        if isinstance(v, dict) and (v.get("address") or "").lower() == addr.lower():
            return str(v.get("role") or "UNKNOWN")
    return "UNKNOWN"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rep = _reports_dir(root)

    public = _read_json(_in_report(root, "public_adapter_run_report.json"))
    trace = _read_json(_comm_trace_json(root))
    private = _read_json(_in_report(root, "celo_sepolia_task_market_report.json")) or _read_json(
        _in_report(root, "local_task_market_report.json")
    )

    symbol = (private or {}).get("native_symbol") or "CELO"
    public_boundary = (public or {}).get("olas", {}).get("boundary") or (public or {}).get("boundary") or "unknown"
    private_boundary = "contract_level_execution" if private else "none"

    settlement = (((private or {}).get("task") or {}).get("settlement") or {}) if private else {}
    by_cat = settlement.get("by_category") or {}
    by_addr = settlement.get("by_address") or {}

    lines: list[str] = []
    lines.append("# Hybrid Clean Proof Report")
    lines.append("")
    lines.append("## Boundaries (no silent fakes)")
    lines.append(f"- public external interaction: `{public_boundary}`")
    lines.append(f"- private onchain settlement: `{private_boundary}`")
    lines.append("")

    if public:
        lines.append("## Public intake (adapter)")
        lines.append(f"- ok: `{bool(public.get('ok'))}`")
        lines.append(f"- market_mode: `{public.get('market_mode')}`")
        lines.append(f"- external_request_id: `{(public.get('normalized_task') or {}).get('external_request_id')}`")
        lines.append(f"- notes: `{(public.get('olas') or {}).get('error') or ''}`")
        lines.append("")

    if private:
        roles = private.get("roles") or {}
        lines.append("## Private marketplace (Celo/Anvil) execution")
        lines.append(f"- chain_id: `{private.get('chain_id')}`")
        lines.append(f"- compute_marketplace: `{private.get('compute_marketplace_address')}`")
        lines.append(f"- task_id: `{((private.get('task') or {}).get('task_id'))}`")
        lines.append("")
        lines.append("### Runtime roles (addresses)")
        for k in ["requester", "worker", "validator", "treasury", "finance_distributor"]:
            v = roles.get(k) or {}
            if isinstance(v, dict):
                lines.append(f"- {k}: `{v.get('role')}` `{v.get('address')}`")
        lines.append("")

    lines.append("## Settlement accounting (economic categories)")
    if not by_cat:
        lines.append("- (missing settlement breakdown; re-run after updating code)")
    else:
        for cat in ["protocol_fee", "finance_fee", "worker_payout", "requester_refund"]:
            info = by_cat.get(cat) or {}
            addr = info.get("address") or "n/a"
            exp = _fmt_wei(info.get("expected_wei"), symbol)
            act = _fmt_wei(info.get("actual_pending_wei"), symbol) if info.get("actual_pending_wei") is not None else "combined (see by-address)"
            lines.append(f"- **{cat}**: to `{addr}` expected {exp}; actual_pending {act}")
        lines.append("")

        lines.append("## Combined entitlement by address (when roles overlap)")
        for addr, ent in by_addr.items():
            role = _role_for_addr(private, addr)
            lines.append(f"- `{addr}` ({role}): expected {_fmt_wei(ent.get('total_expected_wei'), symbol)}; pending {_fmt_wei(ent.get('total_actual_pending_wei'), symbol)}")
            cats = ent.get("categories") or []
            for c in cats:
                lines.append(f"  - {c.get('category')}: expected {_fmt_wei(c.get('expected_wei'), symbol)}")
        lines.append("")

    if trace:
        lines.append("## Evidence pointers")
        lines.append("- See `artifacts/communication/communication_trace.md` for step-by-step boundary markers.")
        lines.append(
            "- See `artifacts/reports/public_adapter_run_report.json` and "
            "`artifacts/reports/celo_sepolia_task_market_report.json` for raw data."
        )
        lines.append("")

    out = rep / "hybrid_clean_report.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

