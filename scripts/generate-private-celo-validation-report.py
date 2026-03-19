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
    private = _read_json(root / "celo_sepolia_task_market_report.json") or _read_json(root / "local_task_market_report.json")
    if not private:
        raise SystemExit("Missing private marketplace report JSON (celo_sepolia_task_market_report.json or local_task_market_report.json).")

    symbol = private.get("native_symbol") or "CELO"
    task = private.get("task") or {}
    settlement = task.get("settlement") or {}
    by_cat = settlement.get("by_category") or {}
    by_addr = settlement.get("by_address") or {}

    chain_id = private.get("chain_id")
    marketplace = private.get("compute_marketplace_address")
    roles = private.get("roles") or {}

    md: list[str] = []
    md.append("# Private Celo Marketplace Validation (Celo Sepolia)")
    md.append("")
    md.append("## Boundaries")
    md.append("- public external interaction: `(not used)`")
    md.append("- private onchain settlement: `contract_level_execution (real)`")
    md.append("")
    md.append("## Lifecycle Proof")
    md.append(f"- chain_id: `{chain_id}`")
    md.append(f"- compute marketplace: `{marketplace}`")
    md.append(f"- task_id: `{task.get('task_id')}`")
    status = (task.get("task_status") or {}).get("name") or task.get("task_status") or "—"
    md.append(f"- task status: `{status}`")
    md.append(f"- escrow: `{task.get('escrow_eth')} {symbol}` (`{task.get('escrow_wei')} wei`)")

    for k in ["requester", "worker", "validator", "treasury", "finance_distributor"]:
        v = roles.get(k)
        if isinstance(v, dict) and v.get("address"):
            md.append(f"- {k}: `{v.get('address')}` (`{v.get('role')}`)")

    md.append("")
    md.append("## Settlement Accounting (economic categories)")
    for cat in ["protocol_fee", "finance_fee", "worker_payout", "requester_refund"]:
        info = by_cat.get(cat) or {}
        md.append(
            f"- **{cat}**: expected {_fmt_wei(info.get('expected_wei'), symbol)}; pending {_fmt_wei(info.get('actual_pending_wei'), symbol)}"
        )

    md.append("")
    md.append("## Combined Entitlement by Address (roles overlap)")
    if not by_addr:
        md.append("- (none)")
    else:
        for addr, ent in by_addr.items():
            md.append(f"- `{addr}`: expected {_fmt_wei(ent.get('total_expected_wei'), symbol)}; pending {_fmt_wei(ent.get('total_actual_pending_wei'), symbol)}")
            cats = ent.get("categories") or []
            for c in cats:
                md.append(f"- {c.get('category')}: expected {_fmt_wei(c.get('expected_wei'), symbol)}")

    md.append("")
    md.append("## Withdrawal Evidence")
    # tx_hashes contains withdraw operations with role/signers.
    txs = private.get("tx_hashes") or []
    withdraws = [t for t in txs if t.get("name") == "withdraw"]
    if not withdraws:
        md.append("- (none)")
    else:
        for w in withdraws:
            md.append(f"- withdraw({w.get('who')}): role={w.get('role')}; tx=`{w.get('tx_hash')}`")

    md.append("")
    md.append("## Raw Artifacts")
    md.append(f"- source JSON: `celo_sepolia_task_market_report.json`")
    md.append("")

    out = root / "private_celo_validation_report.md"
    out.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

