"""
Shared soak-test runner for continuous multi-rail loops.

Supports 6h and 24h runs at 15-minute intervals.
- Archives communication traces per cycle
- Produces metrics summary
- Olas intake: explicitly mocked
"""
from __future__ import annotations

import json
import os
import sys
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

root = Path(__file__).resolve().parents[1]
sys_path_inserted = False


def _ensure_path() -> None:
    global sys_path_inserted
    if not sys_path_inserted:
        sys.path.insert(0, str(root / "packages" / "agents"))
        sys_path_inserted = True


TASK_TEMPLATES = [
    "Summarize in one sentence: What is one ethical use of AI?",
    "Classify: Is sustainable compute usage beneficial? Answer yes or no.",
    "Short answer: What is agentic commerce in one phrase?",
]

WORKER_METADATAS = ["swarm-worker-1", "swarm-worker-2"]

INTERVAL_MINUTES = 15
INTERVAL_SECONDS = INTERVAL_MINUTES * 60

OLAS_BOUNDARY = "mocked_external_replay"

CRITICAL_ENV_KEYS = [
    "COMPUTE_MARKETPLACE_ADDRESS",
    "PRIVATE_MARKETPLACE_ADDRESS",
    "PRIVATE_RPC_URL",
    "RPC_URL",
    "CHAIN_ID",
    "PRIVATE_CHAIN_ID",
    "ROOT_STRATEGIST_PRIVATE_KEY",
    "IP_GENERATOR_PRIVATE_KEY",
    "DEPLOYER_PRIVATE_KEY",
    "FINANCE_DISTRIBUTOR_PRIVATE_KEY",
    "TREASURY_PRIVATE_KEY",
    "XRPL_WALLET_SEED",
    "XRPL_RECEIVER_ADDRESS",
    "XRPL_RPC_URL",
]


def snapshot_config() -> dict[str, str]:
    """Load .env once and snapshot critical vars. Use for entire soak run to avoid mid-run config drift."""
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=True)
    return {k: (os.getenv(k) or "").strip() for k in CRITICAL_ENV_KEYS if os.getenv(k)}


def apply_locked_config(locked: dict[str, str]) -> None:
    """Re-apply locked config to os.environ so cycles use consistent values."""
    for k, v in locked.items():
        if v:
            os.environ[k] = v


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cycle(
    cycle_num: int,
    out_dir: Path,
    trace_archive_dir: Path,
    locked_config: dict[str, str] | None = None,
    *,
    requester_role: str | None = None,
    worker_role: str | None = None,
    validator_role: str | None = None,
) -> dict:
    _ensure_path()
    if locked_config:
        apply_locked_config(locked_config)
    else:
        from dotenv import load_dotenv
        load_dotenv(root / ".env", override=True)

    os.environ["PAYMENT_RAIL_MODE"] = "hybrid_public_request_xrpl_payment_private_celo_settlement"
    os.environ["XRPL_ENABLED"] = "1"
    os.environ["XRPL_PAYMENT_MODE"] = "live"
    os.environ["MARKET_MODE"] = "hybrid"

    realism_mode = (os.getenv("RUN_MODE", "baseline") or "").strip().lower() == "realism"
    if realism_mode:
        if not os.getenv("XRPL_ALLOW_MOCK_FALLBACK"):
            os.environ["XRPL_ALLOW_MOCK_FALLBACK"] = "0"
        os.environ.setdefault("XRPL_QUOTE_DRIVEN", "1")
    task_spec_dict = None
    if realism_mode:
        try:
            from services.task_templates import select_task
            from config.realism_config import get_realism_seed
            task_spec = select_task(cycle_num, get_realism_seed())
            prompt = task_spec.template
            task_spec_dict = {
                "task_type": task_spec.task_type,
                "complexity": task_spec.complexity,
                "sla_seconds": task_spec.sla_seconds,
                "budget_class": task_spec.budget_class,
                "template": task_spec.template,
                "quoted_price_xrp": task_spec.quoted_price_xrp,
                "quoted_price_usd": task_spec.quoted_price_usd,
                "max_budget_usd": task_spec.max_budget_usd,
                "escrow_eth": task_spec.escrow_eth,
            }
            os.environ["TASK_ESCROW_ETH"] = task_spec.escrow_eth
            os.environ["PRICING_TASK_XRP"] = task_spec.quoted_price_xrp
        except ImportError:
            prompt = TASK_TEMPLATES[cycle_num % len(TASK_TEMPLATES)]
    else:
        prompt = TASK_TEMPLATES[cycle_num % len(TASK_TEMPLATES)]

    worker = WORKER_METADATAS[cycle_num % len(WORKER_METADATAS)]
    os.environ["COMPUTE_WORKER_METADATA"] = worker
    os.environ["COMPUTE_MINER_METADATA"] = worker

    start_time = ts()
    start_ts = time.time()
    record: dict = {
        "cycle": cycle_num,
        "start_time": start_time,
        "task_template": prompt,
        "worker_metadata": worker,
        "worker_payout_address": None,
        "payment_rail": "xrpl",
        "olas_boundary": OLAS_BOUNDARY,
        "status": "unknown",
        "xrpl_tx_hash": None,
        "xrpl_amount": None,
        "xrpl_verification": None,
        "internal_task_id": None,
        "celo_tx_hashes": [],
        "task_final_status": None,
        "settlement": {},
        "elapsed_seconds": None,
        "errors": [],
        "warnings": [],
    }

    try:
        from services.multi_rail_hybrid import run_multi_rail_hybrid_demo
        if requester_role is None or worker_role is None or validator_role is None:
            try:
                from services.actor_registry import select_requester, select_worker, select_validator
                requester_role = requester_role or select_requester(cycle_num)
                worker_role = worker_role or select_worker(cycle_num)
                validator_role = validator_role or select_validator(cycle_num)
            except ImportError:
                pass
        result = run_multi_rail_hybrid_demo(
            prompt,
            force_hybrid=True,
            requester_role=requester_role,
            worker_role=worker_role,
            validator_role=validator_role,
        )
        end_ts = time.time()
        record["end_time"] = ts()
        record["elapsed_seconds"] = round(end_ts - start_ts, 2)

        xrpl = result.get("xrpl_payment") or {}
        private = result.get("private_market_report") or {}
        task = private.get("task") or {}
        settlement = task.get("settlement") or {}
        by_cat = settlement.get("by_category") or {}

        record["xrpl_tx_hash"] = xrpl.get("tx_hash") or xrpl.get("external_payment_id")
        record["xrpl_amount"] = xrpl.get("amount", "1")
        record["xrpl_verification"] = xrpl.get("verification_boundary", "")
        record["internal_task_id"] = task.get("task_id")
        record["celo_tx_hashes"] = [t.get("tx_hash") for t in private.get("tx_hashes") or [] if t.get("tx_hash")]
        record["task_final_status"] = (task.get("task_status") or {}).get("name", "")
        record["settlement"] = {
            cat: {"address": d.get("address"), "expected_wei": d.get("expected_wei")}
            for cat, d in by_cat.items()
        }
        wp = by_cat.get("worker_payout", {})
        record["worker_payout_address"] = wp.get("address")
        record["task_spec"] = task_spec_dict
        record["roles"] = private.get("roles")
        record["contracts"] = private.get("contracts")

        ok = result.get("ok") and private.get("ok")
        payment_boundary = result.get("payment_boundary", "")
        if payment_boundary != "real_xrpl_payment":
            record["warnings"].append(f"XRPL boundary was {payment_boundary}, not real_xrpl_payment")
        if not ok:
            record["errors"].append(
                str(private.get("errors") or result.get("public_response", {}).get("notes") or "unknown")
            )
        task_final = (task.get("task_status") or {}).get("name", "")
        real_xrpl_and_finalized = payment_boundary == "real_xrpl_payment" and task_final == "Finalized"
        record["status"] = "completed" if (ok or real_xrpl_and_finalized) else "failed"

        if realism_mode:
            try:
                from services.cycle_schema import build_realism_cycle
                from services.correlation import external_payment_ref
                meta = xrpl.get("metadata") or {}
                vstatus = xrpl.get("verification_boundary", "")
                is_real = vstatus == "real_xrpl_payment"
                is_mock = vstatus == "mock_xrpl_payment"
                is_failed = vstatus == "payment_failed_pre_submit"
                tx = record["xrpl_tx_hash"]
                if is_mock and tx and not str(tx).startswith("mock_tx_"):
                    tx = f"mock_tx_{tx}" if tx else "mock_tx_unknown"
                elif is_failed:
                    tx = None
                xrpl_out = {
                    "tx_hash": tx if (is_real or is_mock) else None,
                    "sender": xrpl.get("payer_address") if is_real else None,
                    "receiver": xrpl.get("receiver_address"),
                    "destination_tag": meta.get("destination_tag"),
                    "memo_ref": meta.get("memo_ref") or meta.get("memo"),
                    "quote_id": meta.get("quote_id"),
                    "expected_amount_xrp": meta.get("expected_amount") or meta.get("quoted_price_xrp") or xrpl.get("amount"),
                    "amount_drops": meta.get("amount_drops"),
                    "delivered_amount": xrpl.get("amount") if is_real else None,
                    "ledger_index": meta.get("ledger_index") if is_real else None,
                    "validated": False if (is_mock or is_failed) else bool(xrpl.get("verified")),
                    "verification_status": vstatus,
                }
                if is_real:
                    xrpl_out["quoted_price_xrp"] = meta.get("quoted_price_xrp") or meta.get("expected_amount")
                if is_mock or is_failed:
                    xrpl_out["mock_reason"] = (meta or {}).get("mock_reason", "unknown")
                ext_ref = external_payment_ref(
                    record["xrpl_tx_hash"],
                    meta.get("destination_tag"),
                    xrpl.get("amount", ""),
                    meta.get("quote_id", ""),
                )
                actors_map = {}
                try:
                    from config.realism_config import get_actors_from_env
                    actors = get_actors_from_env()
                    req_idx = cycle_num % len(actors.get("requesters") or [1])
                    wrk_idx = cycle_num % len(actors.get("workers") or [1])
                    val_idx = cycle_num % len(actors.get("validators") or [1])
                    req = (actors.get("requesters") or [None])[req_idx] if actors.get("requesters") else None
                    wrk = (actors.get("workers") or [None])[wrk_idx] if actors.get("workers") else None
                    val = (actors.get("validators") or [None])[val_idx] if actors.get("validators") else None
                    xrpl_funding = xrpl.get("payer_address") if vstatus == "real_xrpl_payment" and xrpl.get("payer_address") else ""
                    actors_map = {
                        "requester_id": req.id if req else "requester-1",
                        "requester_xrpl_funding_address": xrpl_funding,
                        "requester_celo_refund_address": req.refund_address if req else "",
                        "worker_id": wrk.id if wrk else "worker-1",
                        "worker_payout_address": wrk.payout_address if wrk else record["worker_payout_address"],
                        "validator_id": val.id if val else "validator-1",
                        "validator_address": val.payout_address if val else (private.get("roles") or {}).get("validator", {}).get("address") if isinstance((private.get("roles") or {}).get("validator"), dict) else "",
                    }
                except (ImportError, IndexError, AttributeError):
                    roles = private.get("roles") or {}
                    req_celo = (roles.get("requester") or {}).get("address", "") if isinstance(roles.get("requester"), dict) else ""
                    xrpl_funding_fallback = xrpl.get("payer_address") if vstatus == "real_xrpl_payment" and xrpl.get("payer_address") else ""
                    actors_map = {
                        "requester_id": "requester-1",
                        "requester_xrpl_funding_address": xrpl_funding_fallback,
                        "requester_celo_refund_address": req_celo,
                        "worker_id": "worker-1",
                        "worker_payout_address": record["worker_payout_address"],
                        "validator_id": "validator-1",
                        "validator_address": (roles.get("validator") or {}).get("address", "") if isinstance(roles.get("validator"), dict) else "",
                    }
                record["realism_cycle"] = build_realism_cycle(
                    cycle_num,
                    record["start_time"],
                    record.get("end_time", ""),
                    record["status"],
                    task_spec_dict,
                    actors_map,
                    {"payment_rail": "xrpl", "public_intake": OLAS_BOUNDARY, "private_settlement": "live_celo"},
                    xrpl_out,
                    {"external_payment_ref": ext_ref, "internal_task_id": task.get("task_id")},
                    private,
                    settlement,
                    record.get("elapsed_seconds", 0),
                    record.get("errors", []),
                    record.get("warnings", []),
                )
            except ImportError:
                pass

        trace_archive_dir.mkdir(parents=True, exist_ok=True)
        comm_dir = root / "artifacts" / "communication"
        for name in ["communication_trace.json", "communication_trace.md"]:
            src = comm_dir / name
            if not src.exists():
                src = out_dir / name
            if src.exists():
                dst = trace_archive_dir / f"cycle_{cycle_num:04d}_{name}"
                shutil.copy2(src, dst)

        return record
    except Exception as e:
        record["end_time"] = ts()
        record["elapsed_seconds"] = round(time.time() - start_ts, 2)
        record["errors"].append(str(e))
        record["status"] = "failed"
        return record


def compute_summary(cycles: list[dict]) -> dict:
    completed = [c for c in cycles if c.get("status") == "completed"]
    failed = [c for c in cycles if c.get("status") == "failed"]
    xrpl_out = lambda c: c.get("realism_cycle", {}).get("xrpl") or c.get("xrpl") or {}
    vstatus = lambda c: xrpl_out(c).get("verification_status") or c.get("xrpl_verification") or ""
    xrpl_verified = [c for c in completed if vstatus(c) == "real_xrpl_payment"]
    mock_xrpl = [c for c in cycles if vstatus(c) == "mock_xrpl_payment"]
    failed_pre_submit = [c for c in cycles if vstatus(c) == "payment_failed_pre_submit"]
    total_xrp = 0
    for c in completed:
        xo = c.get("realism_cycle", {}).get("xrpl") or c.get("xrpl") or {}
        amt = xo.get("delivered_amount") or xo.get("expected_amount_xrp") or c.get("xrpl_amount")
        total_xrp += float(amt or 0)
    total_celo_txs = 0
    for c in completed:
        lc = (c.get("celo") or {}).get("lifecycle", []) if isinstance(c.get("celo"), dict) else []
        total_celo_txs += len(lc) if lc else len(c.get("celo_tx_hashes") or [])
    elapsed_list = []
    for c in completed:
        sec = (c.get("elapsed") or {}).get("total_seconds") if isinstance(c.get("elapsed"), dict) else c.get("elapsed_seconds")
        if sec is not None:
            elapsed_list.append(sec)
    avg_duration = sum(elapsed_list) / len(elapsed_list) if elapsed_list else 0

    protocol_fee = 0
    finance_fee = 0
    worker_payout = 0
    requester_refund = 0
    worker_payout_by_address: dict[str, int] = {}
    for c in completed:
        s = c.get("settlement") or {}
        for cat, d in (s.items() if isinstance(s, dict) else []):
            if cat == "currency":
                continue
            w = (d.get("expected_wei") or d.get("actual_wei") or 0) if isinstance(d, dict) else 0
            if cat == "protocol_fee":
                protocol_fee += w
            elif cat == "finance_fee":
                finance_fee += w
            elif cat == "worker_payout":
                worker_payout += w
                addr = (d.get("address") or (c.get("actors") or {}).get("worker_payout_address") if isinstance(c.get("actors"), dict) else None) or c.get("worker_payout_address") or "unknown"
                worker_payout_by_address[addr] = worker_payout_by_address.get(addr, 0) + w
            elif cat == "requester_refund":
                requester_refund += w

    failure_causes: dict[str, int] = {}
    for f in failed:
        err = "; ".join(f.get("errors") or ["unknown"])
        failure_causes[err[:80]] = failure_causes.get(err[:80], 0) + 1

    return {
        "total_xrpl_txs": len(xrpl_verified),
        "total_celo_txs": total_celo_txs,
        "total_xrpl_tx_count": len(xrpl_verified),
        "total_celo_tx_count": total_celo_txs,
        "total_cycles_attempted": len(cycles),
        "total_cycles_completed": len(completed),
        "total_cycles_failed": len(failed),
        "success_rate": round(len(completed) / len(cycles) * 100, 1) if cycles else 0,
        "average_cycle_duration_seconds": round(avg_duration, 2),
        "average_settlement_seconds": round(avg_duration, 2),
        "total_protocol_fee_wei": protocol_fee,
        "total_finance_fee_wei": finance_fee,
        "total_worker_payout_wei": worker_payout,
        "total_requester_refund_wei": requester_refund,
        "total_refunds_wei": requester_refund,
        "total_xrp_paid": round(total_xrp, 6),
        "total_xrpl_payments_verified": len(xrpl_verified),
        "real_xrpl_payment_count": len(xrpl_verified),
        "mock_xrpl_payment_count": len(mock_xrpl),
        "payment_failed_pre_submit_count": len(failed_pre_submit),
        "total_celo_tasks_finalized": len(completed),
        "failure_count_by_category": failure_causes,
        "worker_payout_by_address": worker_payout_by_address,
    }


def write_metrics_summary(summary: dict, path: Path, run_label: str) -> None:
    mock_count = summary.get("mock_xrpl_payment_count", 0)
    failed_pre_count = summary.get("payment_failed_pre_submit_count", 0)
    warnings = []
    if mock_count > 0:
        warnings.append(f"WARNING: {mock_count} realism-mode cycle(s) used mock XRPL fallback.")
    if failed_pre_count > 0:
        warnings.append(f"WARNING: {failed_pre_count} cycle(s) failed pre-submit (XRPL payment build/submit failed).")
    lines = [
        "# Continuous Multi-Rail Metrics Summary",
        "",
        f"Run: {run_label} | Generated: {ts()}",
        "",
    ]
    for w in warnings:
        lines.extend([w, ""])
    lines.extend([
        "## Core Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total XRPL txs (real) | {summary.get('real_xrpl_payment_count', summary.get('total_xrpl_txs', 0))} |",
        f"| Mock XRPL fallback count | {mock_count} |",
        f"| Payment failed pre-submit | {failed_pre_count} |",
        f"| Total Celo txs | {summary.get('total_celo_txs', 0)} |",
        f"| Total cycles attempted | {summary.get('total_cycles_attempted', 0)} |",
        f"| Total cycles completed | {summary.get('total_cycles_completed', 0)} |",
        f"| Success rate | {summary.get('success_rate', 0)}% |",
        f"| Average cycle duration | {summary.get('average_cycle_duration_seconds', 0)}s |",
        "",
        "## Settlement Totals (wei)",
        "",
        "| Category | Total |",
        "|----------|-------|",
        f"| Protocol fee | {summary.get('total_protocol_fee_wei', 0)} |",
        f"| Finance fee | {summary.get('total_finance_fee_wei', 0)} |",
        f"| Worker payout | {summary.get('total_worker_payout_wei', 0)} |",
        f"| Requester refund | {summary.get('total_requester_refund_wei', 0)} |",
        "",
        f"| Total XRP paid | {summary.get('total_xrp_paid', 0)} |",
        "",
        "## Worker Payout by Address",
        "",
    ])
    for addr, wei in (summary.get("worker_payout_by_address") or {}).items():
        lines.append(f"- `{addr}`: {wei} wei")
    if not (summary.get("worker_payout_by_address")):
        lines.append("- (single worker identity)")
    lines.extend(["", "## Olas Intake", "", f"Boundary: `{OLAS_BOUNDARY}` (mocked)", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
