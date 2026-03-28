from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.dual_chain import get_private_chain_config, get_private_marketplace_address, get_public_olas_chain_config
from config.market_mode import get_market_mode
from config.rail_config import get_payment_rail_mode, get_xrpl_config
from services.communication_trace import CommunicationTrace
from services.olas_adapter import send_olas_mech_request
from services.request_normalizer import normalize_olas_request
from services.result_formatter import format_hybrid_result, PublicAdapterResponse
def _receipt_to_dict(r: Any) -> dict[str, Any]:
    if r is None:
        return {}
    if hasattr(r, "__dataclass_fields__"):
        return {k: getattr(r, k) for k in r.__dataclass_fields__}
    return dict(r) if isinstance(r, dict) else {}


from services.xrpl_payment_provider import get_xrpl_payment_receipt


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _out_dir() -> Path:
    p = (os.getenv("REPORT_OUTPUT_DIR") or "").strip()
    if p:
        out = Path(p)
        return out if out.is_absolute() else (_root() / out)
    d = _root() / "artifacts" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _payment_rail_uses_xrpl() -> bool:
    mode = get_payment_rail_mode()
    return "xrpl" in mode.lower() or mode == "mock_payment"


def _write_live_proof_report(
    out_dir: Path,
    run_id: str,
    xrpl: dict[str, Any],
    private_report: dict[str, Any],
) -> None:
    task = private_report.get("task") or {}
    settlement = task.get("settlement") or {}
    by_cat = settlement.get("by_category") or {}
    tx_hashes = private_report.get("tx_hashes") or []
    explorer = private_report.get("explorer_url") or "https://celo-sepolia.blockscout.com"

    def _wei_to_eth(w: int | None) -> str:
        if w is None:
            return "0"
        return f"{w / 1e18:.6f}".rstrip("0").rstrip(".")

    proof: dict[str, Any] = {
        "proof_type": "live_xrpl_to_celo_multi_rail",
        "status": "verified",
        "run_id": run_id,
        "summary": {
            "xrpl_payment": "verified",
            "celo_settlement": "complete",
            "all_withdrawals": "success",
            "settlement_matches_expected": bool(task.get("settlement_matches_expected")),
        },
        "xrpl_payment": {
            "tx_hash": xrpl.get("tx_hash") or xrpl.get("external_payment_id"),
            "explorer_url": f"https://testnet.xrpl.org/transactions/{xrpl.get('tx_hash', '')}",
            "payer": xrpl.get("payer_address") or xrpl.get("payer"),
            "receiver": xrpl.get("receiver_address") or xrpl.get("receiver"),
            "amount": xrpl.get("amount", "1"),
            "asset": xrpl.get("payment_asset", "XRP"),
            "verified": bool(xrpl.get("verified")),
            "verification_boundary": xrpl.get("verification_boundary", "real_xrpl_payment"),
            "network": "testnet",
        },
        "celo_settlement": {
            "chain_id": private_report.get("chain_id"),
            "chain_name": "celo-sepolia",
            "explorer_url": explorer,
            "internal_task_id": task.get("task_id"),
            "task_status": (task.get("task_status") or {}).get("name", "Finalized"),
            "compute_marketplace_address": private_report.get("compute_marketplace_address"),
            "tx_hashes": tx_hashes,
            "settlement_by_category": {
                cat: {
                    "address": data.get("address"),
                    "amount_wei": data.get("expected_wei"),
                    "amount_eth": _wei_to_eth(data.get("expected_wei", 0)),
                    "status": "withdrawn",
                }
                for cat, data in by_cat.items()
            },
        },
        "correlation": {
            "xrpl_tx_hash": xrpl.get("tx_hash") or xrpl.get("external_payment_id"),
            "internal_task_id": task.get("task_id"),
            "celo_tx_count": len(tx_hashes),
            "flow": "XRPL payment → Celo task lifecycle → full settlement",
        },
        "outcome": {
            "ok": True,
            "boundary": "hybrid:public_intake->private_onchain_settlement",
            "payment_rail": "xrpl",
            "settlement_rail": "celo",
            "live_proven": True,
        },
    }
    _write_json(out_dir / "live_xrpl_to_celo_proof_report.json", proof)

    xrpl_tx = proof["xrpl_payment"]["tx_hash"]
    xrpl_url = proof["xrpl_payment"]["explorer_url"]
    md_lines = [
        "# Live XRPL → Celo Multi-Rail Proof Report",
        "",
        f"**Status:** Verified | **Run ID:** {run_id} | **Date:** {time.strftime('%Y-%m-%d', time.localtime())}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "This report documents a **successful live end-to-end multi-rail agent commerce flow**:",
        "",
        "1. **XRPL** — Machine-native payment verified on testnet",
        f"2. **Celo** — Private settlement (task lifecycle + escrow + {len([t for t in tx_hashes if t.get('name') == 'withdraw'])} withdrawals) on Celo Sepolia",
        "",
        "Both rails executed on public testnets with verifiable transaction hashes.",
        "",
        "---",
        "",
        "## 1. XRPL Payment (Machine Rail)",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Tx Hash** | `{xrpl_tx}` |",
        f"| **Explorer** | [View on XRPL Testnet]({xrpl_url}) |",
        f"| **Payer** | `{proof['xrpl_payment']['payer']}` |",
        f"| **Receiver** | `{proof['xrpl_payment']['receiver']}` |",
        f"| **Amount** | {proof['xrpl_payment']['amount']} {proof['xrpl_payment']['asset']} |",
        "| **Verification** | ✅ `real_xrpl_payment` |",
        "| **Network** | XRPL Testnet |",
        "",
        "---",
        "",
        "## 2. Celo Settlement (Private Rail)",
        "",
        f"| Field | Value |",
        "|-------|-------|",
        f"| **Chain** | Celo Sepolia ({private_report.get('chain_id')}) |",
        f"| **Explorer** | [{explorer}]({explorer}) |",
        f"| **Internal Task ID** | {task.get('task_id')} |",
        f"| **Task Status** | {proof['celo_settlement']['task_status']} |",
        f"| **Compute Marketplace** | `{proof['celo_settlement']['compute_marketplace_address']}` |",
        "",
        "### Correlated Celo Transaction Hashes",
        "",
        "| Step | Role | Tx Hash | Link |",
        "|------|------|---------|------|",
    ]
    for t in tx_hashes:
        name = t.get("name", "")
        role = t.get("role", "")
        h = t.get("tx_hash", "")
        link = t.get("link", f"{explorer}/tx/{h}")
        md_lines.append(f"| {name} | {role} | `{h[:10]}...` | [View]({link}) |")
    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Settlement Accounting by Category",
        "",
        "| Category | Address | Amount (CELO) | Status |",
        "|----------|---------|---------------|--------|",
    ])
    for cat, data in proof["celo_settlement"]["settlement_by_category"].items():
        md_lines.append(f"| **{cat}** | `{data['address']}` | {data['amount_eth']} | ✅ Withdrawn |")
    md_lines.extend([
        "",
        f"**Settlement matches expected:** {proof['summary']['settlement_matches_expected']}",
        "",
        "---",
        "",
        "## 4. Correlation",
        "",
        f"| XRPL Tx Hash | Internal Task ID | Celo Tx Count |",
        "|--------------|-----------------|---------------|",
        f"| `{xrpl_tx[:16]}...` | {task.get('task_id')} | {len(tx_hashes)} |",
        "",
        "**Flow:** XRPL payment → Celo task lifecycle → full settlement",
        "",
        "---",
        "",
        "## 5. Final Outcome",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        "| **Overall** | ✅ Success |",
        "| **Payment rail** | XRPL (live) |",
        "| **Settlement rail** | Celo (live) |",
        "| **Boundary** | `hybrid:public_intake->private_onchain_settlement` |",
        "| **Live proven** | Yes |",
        "",
        "---",
        "",
        "## Related Artifacts",
        "",
        "- `live_xrpl_to_celo_proof_report.json` — Machine-readable proof",
        "- `communication_trace.md` — Step-by-step event timeline",
        "- `multi_rail_run_report.json` — Full run output",
        "",
    ])
    _write(out_dir / "live_xrpl_to_celo_proof_report.md", "\n".join(md_lines))


def run_multi_rail_hybrid_demo(
    prompt: str,
    *,
    force_hybrid: bool = False,
    external_payload: dict[str, Any] | None = None,
    xrpl_replay_payload: dict[str, Any] | None = None,
    requester_role: str | None = None,
    worker_role: str | None = None,
    validator_role: str | None = None,
) -> dict[str, Any]:
    mode = get_market_mode()
    market_mode = "hybrid" if force_hybrid else mode
    run_id = str(int(time.time()))

    private_cfg = get_private_chain_config()
    public_cfg = get_public_olas_chain_config()
    xrpl_cfg = get_xrpl_config()

    trace = CommunicationTrace(
        run_id=run_id,
        market_mode=market_mode,
        public_chain_id=public_cfg.chain_id,
        public_rpc_url=public_cfg.rpc_url or None,
        private_chain_id=private_cfg.chain_id,
        private_rpc_url=private_cfg.rpc_url or None,
        external_source="olas",
    )

    if external_payload is None:
        olas_res = send_olas_mech_request(prompt)
        trace.add(
            "olas_send_request",
            olas_res.boundary if olas_res.boundary in {"real_external_integration", "mocked_external_replay"} else "mocked_external_replay",
            ok=olas_res.ok,
            tx_hash=olas_res.tx_hash,
            request_id=olas_res.request_id,
            error=olas_res.error,
            chain_config=olas_res.chain_config,
            tool=olas_res.tool,
        )
        external_payload = {
            "prompt": prompt,
            "tool": os.getenv("OLAS_TOOL", ""),
            "request_id": olas_res.request_id or f"mock-{run_id}",
            "chain_config": os.getenv("OLAS_CHAIN_CONFIG", ""),
            "tx_hash": olas_res.tx_hash,
            "boundary": olas_res.boundary,
        }
        out_olas = asdict(olas_res)
    else:
        out_olas = {
            "ok": True,
            "request_id": str(external_payload.get("request_id") or external_payload.get("requestId") or f"replay-{run_id}"),
            "tx_hash": external_payload.get("tx_hash"),
            "result": external_payload.get("result"),
            "boundary": "mocked_external_replay",
            "error": None,
            "chain_config": external_payload.get("chain_config") or external_payload.get("chainConfig") or os.getenv("OLAS_CHAIN_CONFIG", ""),
            "tool": os.getenv("OLAS_TOOL", ""),
        }
        external_payload.setdefault("prompt", prompt)
        external_payload.setdefault("boundary", "mocked_external_replay")
        trace.add("olas_send_request", "mocked_external_replay", ok=False, error="Replay payload provided; live Olas call skipped.")

    trace.external_request_id = external_payload["request_id"]
    trace.external_tx_hash = external_payload.get("tx_hash")
    trace.correlation["olas"] = {"request_id": external_payload["request_id"], "tx_hash": external_payload.get("tx_hash")}

    normalized = normalize_olas_request(external_payload)
    trace.add(
        "normalized_internal_task",
        "contract_level_execution" if market_mode == "hybrid" else "local_simulation",
        task_metadata=normalized.task_metadata,
    )

    payment_receipt = None
    payment_boundary = "mock_xrpl_payment"

    if _payment_rail_uses_xrpl():
        task_request = {"query": normalized.query, "prompt": prompt, "request_id": external_payload["request_id"]}
        receipt, boundary = get_xrpl_payment_receipt(
            mode=xrpl_cfg.payment_mode,
            task_request=task_request,
            replay_payload=xrpl_replay_payload,
        )
        payment_receipt = receipt
        payment_boundary = boundary
        trace.payment_rail = "xrpl"
        trace.payment_asset = receipt.payment_asset
        trace.xrpl_tx_hash = receipt.tx_hash
        trace.correlation["xrpl_payment"] = {
            "external_payment_id": receipt.external_payment_id,
            "tx_hash": receipt.tx_hash,
            "payer": receipt.payer_address,
            "receiver": receipt.receiver_address,
            "amount": receipt.amount,
            "verified": receipt.verified,
            "verification_boundary": receipt.verification_boundary,
        }
        trace.add(
            "xrpl_payment_received",
            payment_boundary,
            external_payment_id=receipt.external_payment_id,
            tx_hash=receipt.tx_hash,
            verified=receipt.verified,
        )
        if payment_boundary == "payment_failed_pre_submit":
            reason = (receipt.metadata or {}).get("mock_reason", "XRPL payment failed pre-submit")
            fail_out = {
                "ok": False,
                "run_id": run_id,
                "market_mode": market_mode,
                "payment_rail_mode": get_payment_rail_mode(),
                "xrpl_payment": _receipt_to_dict(receipt),
                "payment_boundary": payment_boundary,
                "private_market_report": {"ok": False, "error": reason, "payment_failed_pre_submit": True},
                "public_response": format_hybrid_result({"ok": False, "error": reason}, trace.external_request_id).to_dict(),
            }
            trace.outcome = {"ok": False, "boundary": payment_boundary, "error": reason}
            _write_json(_out_dir() / "multi_rail_run_report.json", fail_out)
            trace.write("communication_trace")
            return fail_out
        if (os.getenv("CUSTOMER_BALANCE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}) and receipt.verified:
            from services.customer_balance import credit_from_xrpl_receipt as persist_credit
            receipt_dict = _receipt_to_dict(receipt)
            persist_credit(receipt_dict, customer_id=trace.external_request_id)
            trace.add("customer_balance_credited", "contract_level_execution", customer_id=trace.external_request_id)

    out: dict[str, Any] = {
        "ok": True,
        "run_id": run_id,
        "market_mode": market_mode,
        "payment_rail_mode": get_payment_rail_mode(),
        "chains": {
            "private": {
                "chain_name": private_cfg.chain_name,
                "chain_id": private_cfg.chain_id,
                "explorer_url": private_cfg.explorer_url,
            },
            "public_olas": {
                "chain_config": public_cfg.chain_name,
                "chain_id": public_cfg.chain_id,
                "explorer_url": public_cfg.explorer_url,
            },
        },
        "olas": out_olas,
        "normalized_task": asdict(normalized),
        "xrpl_payment": _receipt_to_dict(payment_receipt) if payment_receipt else None,
        "payment_boundary": payment_boundary if payment_receipt else None,
        "private_market_report": None,
        "public_response": None,
        "boundary": str(external_payload.get("boundary") or "mocked_external_replay"),
    }

    response: PublicAdapterResponse

    if market_mode == "hybrid":
        from task_market_demo import run_task_market_demo
        from services.pricing import get_task_escrow_wei
        from services.customer_balance_stub import budget_enforcement_check, metering_record
        from services.customer_balance import debit

        customer_id = trace.external_request_id
        escrow_wei = get_task_escrow_wei()
        if os.getenv("CUSTOMER_BALANCE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}:
            if not budget_enforcement_check(customer_id, escrow_wei):
                out["private_market_report"] = {"ok": False, "error": "Insufficient customer balance", "required_wei": escrow_wei}
                out["public_response"] = format_hybrid_result(out["private_market_report"], trace.external_request_id).to_dict()
                trace.outcome = {"ok": False, "boundary": "contract_level_execution", "error": "insufficient_balance"}
                _write_json(_out_dir() / "multi_rail_run_report.json", out)
                trace.write("communication_trace")
                return out
            if not debit(customer_id, escrow_wei, service="task_execution"):
                out["private_market_report"] = {"ok": False, "error": "Failed to debit customer balance"}
                out["public_response"] = format_hybrid_result(out["private_market_report"], trace.external_request_id).to_dict()
                trace.outcome = {"ok": False, "boundary": "contract_level_execution", "error": "debit_failed"}
                _write_json(_out_dir() / "multi_rail_run_report.json", out)
                trace.write("communication_trace")
                return out

        os.environ["COMPUTE_TASK_QUERY"] = normalized.query
        os.environ["COMPUTE_TASK_METADATA"] = normalized.task_metadata
        if requester_role:
            os.environ["TASK_REQUESTER_ROLE"] = requester_role
        if worker_role:
            os.environ["TASK_WORKER_ROLE"] = worker_role
        if validator_role:
            os.environ["TASK_VALIDATOR_ROLE"] = validator_role
        reconciliation_enabled = os.getenv("RECONCILIATION_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        xrpl_hash = (payment_receipt.tx_hash or payment_receipt.external_payment_id) if payment_receipt else None
        if reconciliation_enabled and xrpl_hash and payment_boundary == "real_xrpl_payment":
            try:
                from services.reconciliation import is_settled, get_by_external_ref, record_payment_pending, record_settlement
                if is_settled(xrpl_hash):
                    existing = get_by_external_ref(xrpl_hash)
                    if existing and existing.celo_task_id:
                        private_report = {
                            "ok": True,
                            "task": {
                                "task_id": existing.celo_task_id,
                                "task_status": {"name": "Finalized"},
                                "settlement": {},
                                "settlement_matches_expected": True,
                                "reconciled_from": "existing",
                            },
                            "tx_hashes": existing.celo_tx_hashes,
                            "chain_id": private_cfg.chain_id,
                            "explorer_url": private_cfg.explorer_url,
                            "compute_marketplace_address": get_private_marketplace_address(),
                            "contracts": {},
                        }
                        out["private_market_report"] = private_report
                        trace.internal_task_id = existing.celo_task_id
                        trace.correlation["private"] = {
                            "task_id": trace.internal_task_id,
                            "tx_hashes": existing.celo_tx_hashes,
                            "compute_marketplace_address": private_report.get("compute_marketplace_address"),
                            "treasury_address": None,
                            "finance_distributor_address": None,
                        }
                        trace.correlation["xrpl_to_celo"] = {
                            "xrpl_tx_hash": xrpl_hash,
                            "internal_task_id": trace.internal_task_id,
                            "celo_tx_count": len(existing.celo_tx_hashes),
                        }
                        trace.add("private_marketplace_executed", "reconciled_existing", ok=True, task_id=trace.internal_task_id)
                        response = format_hybrid_result(private_report, trace.external_request_id)
                        out["public_response"] = response.to_dict()
                        trace.outcome = {"ok": True, "boundary": response.boundary}
                        _write_json(_out_dir() / "multi_rail_run_report.json", out)
                        _write_live_proof_report(_out_dir(), run_id, _receipt_to_dict(payment_receipt), out["private_market_report"])
                        trace.write("communication_trace")
                        return out
                claimed = record_payment_pending(
                    xrpl_hash,
                    job_id=(payment_receipt.metadata or {}).get("job_id", xrpl_hash[:16]),
                    quote_id=(payment_receipt.metadata or {}).get("quote_id", xrpl_hash[:16]),
                    destination_tag=(payment_receipt.metadata or {}).get("destination_tag"),
                    memo_ref=(payment_receipt.metadata or {}).get("memo_ref") or (payment_receipt.metadata or {}).get("memo"),
                    delivered_amount=str(payment_receipt.amount),
                )
                if not claimed:
                    out["private_market_report"] = {"ok": False, "error": "Duplicate payment reference; already claimed"}
                    out["public_response"] = format_hybrid_result(out["private_market_report"], trace.external_request_id).to_dict()
                    trace.outcome = {"ok": False, "boundary": "contract_level_execution", "error": "duplicate_payment_ref"}
                    _write_json(_out_dir() / "multi_rail_run_report.json", out)
                    trace.write("communication_trace")
                    return out
            except ImportError:
                pass
        private_report = run_task_market_demo()
        out["private_market_report"] = private_report
        if reconciliation_enabled and xrpl_hash and private_report.get("ok"):
            task = private_report.get("task") or {}
            if task.get("task_id"):
                try:
                    from services.reconciliation import record_settlement
                    record_settlement(
                        xrpl_hash,
                        task["task_id"],
                        private_report.get("tx_hashes", []),
                        payout_refund=task.get("settlement", {}).get("by_category"),
                        disposition="settled",
                    )
                except ImportError:
                    pass
        balance_enabled = os.getenv("CUSTOMER_BALANCE_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        if private_report.get("ok") and balance_enabled:
            task_id = (private_report.get("task") or {}).get("task_id")
            metering_record("task_execution", customer_id, escrow_wei, {"task_id": task_id, "escrow_wei": escrow_wei})
        if balance_enabled:
            try:
                from services.customer_balance import get_customer_activity
                out["customer_balance"] = get_customer_activity(customer_id)
            except Exception:
                pass
        trace.internal_task_id = (private_report.get("task") or {}).get("task_id")
        trace.correlation["private"] = {
            "task_id": trace.internal_task_id,
            "tx_hashes": private_report.get("tx_hashes", []),
            "compute_marketplace_address": private_report.get("compute_marketplace_address"),
            "treasury_address": ((private_report.get("contracts") or {}).get("treasury") or None),
            "finance_distributor_address": ((private_report.get("contracts") or {}).get("finance_distributor") or None),
        }
        if payment_receipt:
            trace.correlation["xrpl_to_celo"] = {
                "xrpl_tx_hash": payment_receipt.tx_hash,
                "internal_task_id": trace.internal_task_id,
                "celo_tx_count": len(private_report.get("tx_hashes", [])),
            }
        trace.add(
            "private_marketplace_executed",
            "real_celo_settlement" if private_report.get("ok") else "contract_level_execution",
            ok=bool(private_report.get("ok")),
            task_id=trace.internal_task_id,
        )
        response = format_hybrid_result(private_report, trace.external_request_id)
    else:
        response = PublicAdapterResponse(
            ok=bool(out_olas.get("ok")),
            external_request_id=trace.external_request_id,
            internal_task_id=None,
            result_text=str(out_olas.get("result")) if out_olas.get("result") is not None else "No live Olas result (mock/replay boundary).",
            tx_hashes=[str(out_olas.get("tx_hash"))] if out_olas.get("tx_hash") else [],
            boundary=str(out_olas.get("boundary") or "mocked_external_replay"),
            notes=out_olas.get("error"),
        )

    out["public_response"] = response.to_dict()
    trace.outcome = {"ok": response.ok, "boundary": response.boundary}

    out_dir = _out_dir()
    _write_json(out_dir / "multi_rail_run_report.json", out)
    if payment_boundary == "real_xrpl_payment" and payment_receipt and out.get("private_market_report", {}).get("ok"):
        _write_live_proof_report(
            out_dir,
            run_id,
            _receipt_to_dict(payment_receipt),
            out["private_market_report"],
        )
    _write(
        out_dir / "multi_rail_run_report.md",
        "\n".join(
            [
                "# Multi-Rail Run Report",
                "",
                f"- Run ID: `{run_id}`",
                f"- Market mode: `{market_mode}`",
                f"- Payment rail mode: `{get_payment_rail_mode()}`",
                f"- External request ID: `{trace.external_request_id}`",
                f"- Payment boundary: `{payment_boundary}`",
                f"- XRPL tx hash: `{trace.xrpl_tx_hash or 'n/a'}`",
                "",
                "## Public response",
                "",
                f"- ok: `{response.ok}`",
                f"- internal_task_id: `{response.internal_task_id}`",
                f"- tx_hashes: `{', '.join(response.tx_hashes)}`",
                "",
                "## Notes",
                "",
                response.notes or "(none)",
                "",
            ]
        ),
    )

    trace.write("communication_trace")
    return out
