from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config.dual_chain import get_private_chain_config, get_public_olas_chain_config
from config.market_mode import get_market_mode
from services.communication_trace import CommunicationTrace
from services.olas_adapter import send_olas_mech_request
from services.request_normalizer import normalize_olas_request
from services.result_formatter import format_hybrid_result, PublicAdapterResponse


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


def run_public_adapter_demo(prompt: str, *, force_hybrid: bool = False, external_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    MODE B / MODE D building block:
    - Attempts a live Olas mech request if enabled/configured (supported chains: gnosis/base/polygon/optimism).
    - Always normalizes into our internal task model.
    - In hybrid mode: executes internal private onchain task settlement via `task_market_demo`.
    - Writes `public_adapter_run_report.(json|md)` and `communication_trace.(json|md)`.
    """
    mode = get_market_mode()
    market_mode = "hybrid" if force_hybrid else mode
    run_id = str(int(time.time()))

    private_cfg = get_private_chain_config()
    public_cfg = get_public_olas_chain_config()
    trace = CommunicationTrace(
        run_id=run_id,
        market_mode=market_mode,
        public_chain_id=public_cfg.chain_id,
        public_rpc_url=public_cfg.rpc_url or None,
        private_chain_id=private_cfg.chain_id,
        private_rpc_url=private_cfg.rpc_url or None,
        external_source="olas",
    )

    # If a replay payload was provided, do NOT attempt a live Olas call.
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

    trace.add(
        "public_intake_received",
        str(out_olas.get("boundary") or "mocked_external_replay"),
        prompt=prompt,
    )

    trace.external_request_id = external_payload["request_id"]
    trace.external_tx_hash = external_payload.get("tx_hash")
    trace.correlation["olas"] = {"request_id": external_payload["request_id"], "tx_hash": external_payload.get("tx_hash")}

    normalized = normalize_olas_request(external_payload)
    trace.add(
        "normalized_internal_task",
        "contract_level_execution" if market_mode == "hybrid" else "local_simulation",
        task_metadata=normalized.task_metadata,
    )

    out: dict[str, Any] = {
        "ok": True,
        "run_id": run_id,
        "market_mode": market_mode,
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
        "private_market_report": None,
        "public_response": None,
        "boundary": str(external_payload.get("boundary") or "mocked_external_replay"),
    }

    response: PublicAdapterResponse

    if market_mode == "hybrid":
        # Execute internal settlement on Celo/Anvil using our existing demo runner.
        from task_market_demo import run_task_market_demo

        os.environ["COMPUTE_TASK_QUERY"] = normalized.query
        os.environ["COMPUTE_TASK_METADATA"] = normalized.task_metadata
        private_report = run_task_market_demo()
        out["private_market_report"] = private_report
        trace.internal_task_id = (private_report.get("task") or {}).get("task_id")
        trace.correlation["private"] = {
            "task_id": trace.internal_task_id,
            "tx_hashes": private_report.get("tx_hashes", []),
            "compute_marketplace_address": private_report.get("compute_marketplace_address"),
            "treasury_address": ((private_report.get("contracts") or {}).get("treasury") or None),
            "finance_distributor_address": ((private_report.get("contracts") or {}).get("finance_distributor") or None),
        }
        trace.add(
            "private_marketplace_executed",
            "contract_level_execution",
            ok=bool(private_report.get("ok")),
            task_id=trace.internal_task_id,
        )
        response = format_hybrid_result(private_report, trace.external_request_id)
    else:
        # Pure public adapter mode without internal settlement (yet).
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
    _write_json(out_dir / "public_adapter_run_report.json", out)
    _write(
        out_dir / "public_adapter_run_report.md",
        "\n".join(
            [
                "# Public Adapter Run Report",
                "",
                f"- Run ID: `{run_id}`",
                f"- Market mode: `{market_mode}`",
                f"- External request ID: `{trace.external_request_id}`",
                f"- Boundary: `{response.boundary}`",
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

