from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STEP_MAP = {
    "createTask": "createTask",
    "acceptTask": "acceptTask",
    "submitResult": "submitResult",
    "submitTaskScore": "validateResult",
    "finalizeTask": "finalizeTask",
    "registerAsMiner": "registerWorker",
    "setValidatorAllowlist": "allowlistValidator",
}


def _tx_to_lifecycle_step(entry: dict[str, Any], roles: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    name = entry.get("name", "")
    step = STEP_MAP.get(name, name)
    if name == "withdraw":
        role = (entry.get("role") or entry.get("signer_role") or "").upper()
        who = (entry.get("who") or "").lower()
        worker_addr = (roles.get("worker") or {}).get("address", "") if isinstance(roles.get("worker"), dict) else ""
        req_addr = (roles.get("requester") or {}).get("address", "") if isinstance(roles.get("requester"), dict) else ""
        if who == worker_addr.lower():
            step = "withdrawWorkerPayout"
        elif who == (contracts.get("treasury") or "").lower():
            step = "settleProtocolFee"
        elif who == (contracts.get("finance_distributor") or "").lower():
            step = "settleFinanceFee"
        elif who == req_addr.lower():
            step = "refundRequester"
        elif "WORKER" in role or "IP_GENERATOR" in role:
            step = "withdrawWorkerPayout"
        elif "TREASURY" in role:
            step = "settleProtocolFee"
        elif "FINANCE" in role:
            step = "settleFinanceFee"
        elif "ROOT_STRATEGIST" in role or "REQUESTER" in role:
            step = "refundRequester"
        else:
            step = "withdraw"
    return {
        "step": step,
        "tx_hash": entry.get("tx_hash"),
        "block_number": entry.get("block_number"),
        "success": True,
    }


def build_realism_cycle(
    cycle_num: int,
    start_time: str,
    end_time: str,
    status: str,
    task_spec: dict[str, Any] | None,
    actors: dict[str, Any],
    boundary: dict[str, str],
    xrpl: dict[str, Any],
    correlation: dict[str, Any],
    private_report: dict[str, Any],
    settlement: dict[str, Any],
    elapsed_seconds: float,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    roles = (private_report.get("roles") or {})
    contracts = (private_report.get("contracts") or {})
    tx_hashes = private_report.get("tx_hashes") or []
    lifecycle = [_tx_to_lifecycle_step(t, roles, contracts) for t in tx_hashes if t.get("tx_hash")]

    settlement_out: dict[str, Any] = {"currency": "CELO"}
    by_cat = settlement.get("by_category") or settlement
    if isinstance(by_cat, dict):
        for cat, data in by_cat.items():
            addr = data.get("address") if isinstance(data, dict) else None
            wei = data.get("expected_wei") or data.get("actual_wei") or data.get("actual_pending_wei") if isinstance(data, dict) else 0
            if addr:
                settlement_out[cat] = {"address": addr, "actual_wei": wei}

    task_out: dict[str, Any] = {}
    if task_spec:
        task_out = {
            "task_type": task_spec.get("task_type", ""),
            "complexity": task_spec.get("complexity", ""),
            "template": task_spec.get("template", ""),
            "sla_seconds": task_spec.get("sla_seconds"),
            "quoted_price_xrp": task_spec.get("quoted_price_xrp", ""),
            "quoted_price_usd": task_spec.get("quoted_price_usd", ""),
            "max_budget": task_spec.get("max_budget_usd", ""),
        }
    task_info = private_report.get("task") or {}
    task_out["task_id"] = task_info.get("task_id")

    return {
        "cycle": cycle_num,
        "start_time": start_time,
        "end_time": end_time,
        "status": status,
        "task": task_out,
        "actors": actors,
        "boundary": boundary,
        "xrpl": xrpl,
        "correlation": correlation,
        "celo": {
            "network": "celo_sepolia",
            "task_contract": private_report.get("compute_marketplace_address"),
            "lifecycle": lifecycle,
            "final_status": (task_info.get("task_status") or {}).get("name", ""),
            "confirmations_used": 1,
        },
        "settlement": settlement_out,
        "quality": {
            "result_score": task_info.get("average_score"),
            "validator_decision": "accepted" if status == "completed" else "unknown",
        },
        "elapsed": {
            "total_seconds": round(elapsed_seconds, 2),
        },
        "errors": errors,
        "warnings": warnings,
    }
